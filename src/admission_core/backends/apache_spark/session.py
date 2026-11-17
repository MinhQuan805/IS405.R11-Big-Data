"""Create a lazy Spark runtime with explicit session ownership."""
import os
import sys


class SparkRuntime:
    def __init__(self, config=None):
        self.config = config or {}
        self._session = None
        self._owned = False

    @property
    def session(self):
        if self._session is None:
            from pyspark.sql import SparkSession
            os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
            self._owned = SparkSession.getActiveSession() is None
            builder = SparkSession.builder.appName(self.config.get("app_name", "admission-big-data"))
            master = self.config.get("master", "local[2]")
            if master:
                builder = builder.master(master)
            settings = {"spark.sql.shuffle.partitions": "4", "spark.ui.enabled": "false",
                        "spark.sql.session.timeZone": "Asia/Bangkok"}
            local_fs_jar = self.config.get("windows_local_fs_jar") or os.environ.get("ADMISSION_WINDOWS_FS_JAR")
            if os.name == "nt" and local_fs_jar:
                if not master.startswith("local"):
                    raise ValueError("windows_local_fs_jar chỉ dành cho Spark local")
                settings.update({"spark.driver.extraClassPath": local_fs_jar,
                    "spark.executor.extraClassPath": local_fs_jar,
                    "spark.hadoop.fs.file.impl": "com.globalmentor.apache.hadoop.fs.BareLocalFileSystem"})
            settings.update(self.config.get("conf", {}))
            for key, value in settings.items():
                builder = builder.config(key, str(value))
            self._session = builder.getOrCreate()
            self._session.sparkContext.setLogLevel("ERROR")
            if self._session.version != "4.3.0":
                self.close()
                raise RuntimeError("Backend yêu cầu Spark 4.3.0")
        return self._session

    def close(self):
        if self._session is not None and self._owned:
            self._session.stop()
        self._session = None
