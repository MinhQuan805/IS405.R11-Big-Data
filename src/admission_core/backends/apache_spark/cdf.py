"""Exact empirical CDF from distributed score observations."""
from functools import reduce
from admission_core.ports import BaseCDFPort
from admission_core.specs.contracts import BLOCK_NAME_MAP
from admission_core.cdf_contract import YEAR_MAP, CDF_COLUMNS
from admission_core.backends.apache_spark.session import SparkRuntime


class SparkCDFBackend(BaseCDFPort):
    def __init__(self, runtime=None):
        self.runtime = runtime or SparkRuntime()

    def compute_cdf(self, raw_dist_sources, output_uri, options=None):
        from pyspark.sql import functions as F, Window
        spark = self.runtime.session
        frames = []
        mapping = F.create_map(*[F.lit(value) for pair in YEAR_MAP.items() for value in pair])
        blocks = F.create_map(*[F.lit(value) for pair in BLOCK_NAME_MAP.items() for value in pair])
        for name, uri in raw_dist_sources.items():
            if not name.startswith("score_distribution") or not uri:
                continue
            frame = spark.read.parquet(uri)
            excluded = (options or {}).get("excluded_year_labels", {}).get(name, [])
            if excluded:
                if "Nam" not in frame.columns:
                    raise ValueError("Loại đợt thi cần cột Nam ở nguồn phổ điểm")
                frame = frame.filter(~F.col("Nam").cast("string").isin(excluded))
            if {"score_year", "block_name", "score_value"}.issubset(frame.columns):
                frame = frame.select("score_year", "block_name", "score_value")
                frame = frame.withColumn("block_name", F.coalesce(blocks[F.col("block_name")], F.col("block_name")))
            else:
                if "score_year" not in frame.columns:
                    if "Nam" in frame.columns:
                        frame = frame.withColumn("score_year", F.coalesce(
                            mapping[F.col("Nam").cast("string")].cast("string"), F.col("Nam").cast("string")))
                    elif name == "score_distribution_ct2018":
                        frame = frame.withColumn("score_year", F.lit(2025))
                    else:
                        raise ValueError("Phổ điểm thiếu năm")
                names = [block for block in BLOCK_NAME_MAP.values() if block in frame.columns]
                if not names:
                    raise ValueError("Phổ điểm không có tổ hợp được hỗ trợ")
                frame = frame.select("score_year", F.explode(F.array(*[
                    F.struct(F.lit(block).alias("block_name"),
                             F.expr(f"try_cast(`{block}` as double)").alias("score_value")) for block in names
                ])).alias("observation")).select("score_year", "observation.*")
            year = F.expr("try_cast(score_year as double)")
            frame = frame.withColumn("score_value", F.expr("try_cast(score_value as double)"))
            frame = frame.filter(year.between(2016, 2100) & (year == F.floor(year)))
            frame = frame.withColumn("score_year", F.expr("try_cast(score_year as double)").cast("int"))
            frame = frame.filter(F.col("score_value").between(0, 30) &
                                 ~F.isnan("score_value") & F.col("block_name").isin(list(BLOCK_NAME_MAP.values())))
            frames.append(frame)
        if not frames:
            raise FileNotFoundError("Không có nguồn phổ điểm")
        observations = reduce(lambda left, right: left.unionByName(right), frames)
        counts = observations.groupBy("score_year", "block_name", "score_value").agg(
            F.count("*").alias("candidate_count"))
        group = Window.partitionBy("score_year", "block_name")
        cumulative = group.orderBy("score_value").rowsBetween(Window.unboundedPreceding, Window.currentRow)
        output = counts.withColumn("total_candidates", F.sum("candidate_count").over(group))
        output = output.withColumn("cdf_leq", F.sum("candidate_count").over(cumulative) / F.col("total_candidates"))
        output = output.withColumn("rank_pct_gt", 1.0 - F.col("cdf_leq")).select(CDF_COLUMNS)
        if output.isEmpty():
            raise ValueError("Không có quan sát điểm hợp lệ")
        output.write.mode("errorifexists").parquet(output_uri)
        return output_uri
