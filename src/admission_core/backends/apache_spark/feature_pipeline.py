"""Distributed step lookup, annual joins and hierarchical feature engineering."""
from admission_core.ports import BaseFeaturePipelinePort
from admission_core.specs.contracts import BLOCK_NAME_MAP, OFFICIAL_FEATURES
from admission_core.features import KEYS, PROGRAM, INTERACTIONS, major_join_keys
from admission_core.backends.apache_spark.session import SparkRuntime


class SparkFeatureBackend(BaseFeaturePipelinePort):
    def __init__(self, runtime=None):
        self.runtime = runtime or SparkRuntime()

    def build_features(self, input_data_uris, output_feature_uri, options=None):
        from pyspark.sql import functions as F, Window
        options = options or {}
        spark = self.runtime.session
        cutoff = spark.read.parquet(input_data_uris["cutoff_scores"])
        cutoff = cutoff.filter(F.col("score_admission_name") == "Điểm thi THPT")
        cutoff = cutoff.withColumn("score_year", F.col("score_year").cast("int"))
        cutoff = cutoff.filter(F.col("score_year") >= int(options.get("min_label_year", 2016)))
        cutoff = cutoff.withColumn("score_mark", F.expr("try_cast(score_mark as double)"))
        cutoff = cutoff.filter(F.col("score_mark").between(0, 30) & ~F.isnan("score_mark"))
        if not cutoff.filter(F.col("school_id").isNull() | F.col("school_name").isNull() |
                             F.col("score_code").isNull() | F.col("score_year").isNull()).isEmpty():
            raise ValueError("Điểm chuẩn thiếu thông tin định danh")
        cutoff = cutoff.withColumn("school_id", F.trim(F.col("school_id").cast("string")))
        cutoff = cutoff.withColumn("score_code", F.trim(F.col("score_code").cast("string")))
        if not cutoff.filter((F.col("school_id") == "") | (F.col("score_code") == "")).isEmpty():
            raise ValueError("Mã trường hoặc chương trình rỗng")
        cutoff = cutoff.withColumn("blocks", F.array_sort(F.array_distinct(F.filter(
            F.transform(F.split(F.coalesce(F.col("score_blocks"), F.lit("")), ";"), lambda block: F.trim(block)),
            lambda block: block.isin(list(BLOCK_NAME_MAP))))))
        if cutoff.isEmpty() or not cutoff.filter(F.size("blocks") == 0).isEmpty():
            raise ValueError("Điểm chuẩn rỗng hoặc không có tổ hợp được hỗ trợ")
        majors = spark.read.parquet(input_data_uris["majors"])
        majors = majors.withColumn("score_code", F.explode(F.split("score_codes", ";")))
        majors = majors.withColumn("score_code", F.trim("score_code"))
        major_keys = major_join_keys(majors.columns)
        majors = majors.select(*major_keys, "major_name", "major_group_name").filter("score_code != ''").distinct()
        if not majors.groupBy(major_keys).count().filter("count > 1").isEmpty():
            raise ValueError("Mã chương trình có nhiều ánh xạ ngành")
        cutoff = cutoff.join(majors, major_keys, "left")
        if not cutoff.filter(F.col("major_name").isNull() | F.col("major_group_name").isNull()).isEmpty():
            raise ValueError("Điểm chuẩn có mã ngành chưa được ánh xạ")
        cutoff = cutoff.withColumn("query_id", F.monotonically_increasing_id()).localCheckpoint(eager=True)
        mapping = F.create_map(*[F.lit(value) for pair in BLOCK_NAME_MAP.items() for value in pair])
        queries = cutoff.select("query_id", "score_year", "score_mark", F.explode("blocks").alias("block"))
        queries = queries.select("query_id", "score_year", mapping[F.col("block")].alias("block_name"),
                                 F.col("score_mark").alias("score_value"))
        cdf = spark.read.parquet(input_data_uris["cdf_data"])
        missing = queries.select("score_year", "block_name").distinct().join(
            cdf.select("score_year", "block_name").distinct(), ["score_year", "block_name"], "left_anti")
        if not missing.isEmpty():
            raise ValueError("Thiếu CDF cho năm hoặc tổ hợp trong điểm chuẩn")
        # Merge CDF knots and score queries. Knots precede queries at equal scores.
        events = cdf.select("score_year", "block_name", "score_value", "cdf_leq").withColumn("query_id", F.lit(None).cast("long"))
        events = events.withColumn("kind", F.lit(0))
        requests = queries.withColumn("cdf_leq", F.lit(None).cast("double")).withColumn("kind", F.lit(1))
        events = events.unionByName(requests)
        window = Window.partitionBy("score_year", "block_name").orderBy("score_value", "kind").rowsBetween(
            Window.unboundedPreceding, Window.currentRow)
        ranked = events.withColumn("cdf_at_score", F.last("cdf_leq", ignorenulls=True).over(window))
        ranks = ranked.filter("kind = 1").groupBy("query_id").agg(
            F.avg(1 - F.coalesce(F.col("cdf_at_score"), F.lit(0.0))).alias("R_star"))
        labeled = cutoff.join(ranks, "query_id")
        programs = labeled.groupBy(PROGRAM).agg(F.avg("R_star").alias("R_star"),
            F.array_sort(F.array_distinct(F.flatten(F.collect_list("blocks")))).alias("blocks"))
        programs = programs.withColumn("allowed_blocks", F.concat_ws(";", "blocks")).withColumn(
            "num_blocks", F.size("blocks")).drop("blocks").withColumn("offering_carried_forward", F.lit(0))
        programs = programs.localCheckpoint(eager=True)
        if not programs.groupBy(KEYS).count().filter("count > 1").isEmpty():
            raise ValueError("Thông tin chương trình không nhất quán trong cùng năm")
        latest = programs.agg(F.max("score_year")).first()[0]
        year = int(options.get("forecast_year", latest + 1))
        if year <= latest:
            raise ValueError("forecast_year phải lớn hơn năm điểm chuẩn cuối")
        future = programs.filter(F.col("score_year") == latest).withColumn("score_year", F.lit(year))
        future = future.withColumn("R_star", F.lit(None).cast("double")).withColumn("offering_carried_forward", F.lit(1))
        output = programs.unionByName(future)
        lag = programs.select(*KEYS, F.col("R_star").alias("prog_pct_lag1")).withColumn("score_year", F.col("score_year") + 1)
        output = output.join(lag, KEYS, "left")
        for key, aggregates in [
            ("school_id", [F.avg("R_star").alias("school_pct_mean_lag1"), F.min("R_star").alias("school_pct_min_lag1")]),
            ("major_name", [F.avg("R_star").alias("major_pct_mean_lag1")]),
            ("major_group_name", [F.avg("R_star").alias("group_pct_mean_lag1")]),
        ]:
            values = programs.groupBy(key, "score_year").agg(*aggregates).withColumn("score_year", F.col("score_year") + 1)
            output = output.join(values, [key, "score_year"], "left")
        if input_data_uris.get("trend_annual") and input_data_uris.get("trend_keywords"):
            annual = spark.read.parquet(input_data_uris["trend_annual"])
            if not annual.groupBy("query_id", "year").count().filter("count > 1").isEmpty():
                raise ValueError("Trends theo năm trùng query_id và year")
            for name in ("interest_mean", "interest_season_peak"):
                annual = annual.withColumn(name, F.when(~F.isnan(name), F.col(name)))
            keywords = spark.read.parquet(input_data_uris["trend_keywords"]).select("query_id", "keyword", "keyword_type").distinct()
            trends = annual.join(keywords, "query_id")
            for kind, key, source, target in [
                ("school", "school_name", "interest_season_peak", "trend_school_peak"),
                ("major_group", "major_group_name", "interest_mean", "trend_group_mean"),
            ]:
                values = trends.filter(F.col("keyword_type") == kind).groupBy("keyword", "year").agg(F.avg(source).alias(target))
                values = values.select(F.col("keyword").alias(key), (F.col("year").cast("int") + 1).alias("score_year"), target)
                output = output.join(values, [key, "score_year"], "left")
        else:
            output = output.withColumn("trend_school_peak", F.lit(0.0)).withColumn("trend_group_mean", F.lit(0.0))
        output = output.fillna(0.5, subset=["school_pct_mean_lag1", "school_pct_min_lag1", "major_pct_mean_lag1", "group_pct_mean_lag1"])
        output = output.withColumn("is_new_program", F.col("prog_pct_lag1").isNull().cast("int"))
        output = output.withColumn("prog_pct_lag1", F.coalesce(F.col("prog_pct_lag1"),
            0.5 * F.col("school_pct_mean_lag1") + 0.5 * F.col("major_pct_mean_lag1")))
        output = output.withColumn("delta_prog_vs_school_mean", F.col("prog_pct_lag1") - F.col("school_pct_mean_lag1"))
        output = output.withColumn("delta_prog_vs_major_mean", F.col("prog_pct_lag1") - F.col("major_pct_mean_lag1"))
        output = output.fillna(0.0, subset=["trend_school_peak", "trend_group_mean"])
        for name, (left, right) in INTERACTIONS.items():
            output = output.withColumn(name, F.col(left) * F.col(right))
        output = output.filter(F.col("score_year") >= int(options.get("min_training_year", 2018)))
        output = output.localCheckpoint(eager=True)
        invalid = None
        for name in OFFICIAL_FEATURES:
            bad = F.col(name).isNull() | F.isnan(name) | (F.abs(F.col(name)) == float("inf"))
            invalid = bad if invalid is None else invalid | bad
        if output.isEmpty() or not output.filter(invalid).isEmpty():
            raise ValueError("Gold rỗng hoặc chứa đặc trưng không hợp lệ")
        output.write.mode("errorifexists").parquet(output_feature_uri)
        return output_feature_uri
