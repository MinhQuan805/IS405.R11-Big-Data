"""Backend dispatch and explicit CDF plugin overrides."""
import importlib
import inspect
import subprocess
import sys
from admission_core.ports import BaseCDFPort


def validate_backend(config):
    name = config.get("execution_backend", "local_pandas")
    if name not in {"local_pandas", "apache_spark"}:
        raise ValueError(f"Backend chưa được hỗ trợ: {name}")
    return name


class ExternalScriptCDFAdapter(BaseCDFPort):
    def __init__(self, command_template):
        self.command_template = command_template

    def compute_cdf(self, raw_dist_sources, output_uri, options=None):
        values = dict(raw_dist_sources, input_uri=raw_dist_sources.get("score_distribution_ct2006", ""),
                      output_uri=output_uri, python=sys.executable)
        # A list preserves paths containing spaces and avoids shell interpolation.
        if isinstance(self.command_template, list):
            command = [str(argument).format(**values) for argument in self.command_template]
            subprocess.run(command, check=True)
        else:
            # Compatibility for existing, trusted shell command configurations.
            subprocess.run(self.command_template.format(**values), shell=True, check=True)
        from admission_core.cdf_contract import validate_cdf
        import pandas as pd
        validate_cdf(pd.read_parquet(output_uri))
        return output_uri


class ClassCDFAdapter(BaseCDFPort):
    def __init__(self, instance):
        self.instance = instance

    def compute_cdf(self, raw_dist_sources, output_uri, options=None):
        if hasattr(self.instance, "compute_cdf"):
            result = self.instance.compute_cdf(raw_dist_sources, output_uri, options)
        else:
            arguments = {"input_uri": raw_dist_sources.get("score_distribution_ct2006", ""),
                         "output_uri": output_uri, "raw_dist_sources": raw_dist_sources, "options": options}
            parameters = inspect.signature(self.instance.execute).parameters
            if not any(parameter.kind == inspect.Parameter.VAR_KEYWORD for parameter in parameters.values()):
                arguments = {key: value for key, value in arguments.items() if key in parameters}
            result = self.instance.execute(**arguments)
        from admission_core.cdf_contract import validate_cdf
        import pandas as pd
        validate_cdf(pd.read_parquet(result))
        return result


def resolve_adapter(stage_cfg, default_class):
    kind = (stage_cfg or {}).get("type", "builtin")
    if kind == "builtin":
        return default_class()
    if kind == "external_script":
        command = stage_cfg.get("command")
        if not command:
            raise ValueError("Plugin script thiếu command")
        return ExternalScriptCDFAdapter(command)
    if kind == "class_adapter":
        module, name = stage_cfg["target"].rsplit(".", 1)
        return ClassCDFAdapter(getattr(importlib.import_module(module), name)())
    raise ValueError(f"Loại plugin không hợp lệ: {kind}")


def get_ingestion_backend(config):
    validate_backend(config)
    from admission_core.backends.local_pandas.ingestion import LocalIngestionBackend
    return LocalIngestionBackend()


def get_cdf_backend(config, runtime=None):
    name = validate_backend(config)
    from admission_core.backends.local_pandas.cdf import LocalPandasCDFBackend
    default = LocalPandasCDFBackend
    if name == "apache_spark":
        from admission_core.backends.apache_spark.cdf import SparkCDFBackend
        default = lambda: SparkCDFBackend(runtime)
    return resolve_adapter(config.get("backend_execution", {}).get("cdf_stage"), default)


def get_feature_backend(config, runtime=None):
    if validate_backend(config) == "apache_spark":
        from admission_core.backends.apache_spark.feature_pipeline import SparkFeatureBackend
        return SparkFeatureBackend(runtime)
    from admission_core.backends.local_pandas.feature_pipeline import LocalPandasFeatureBackend
    return LocalPandasFeatureBackend()


def get_trainer_backend(config):
    validate_backend(config)
    from admission_core.backends.local_pandas.trainer import LocalLightGBMTrainerBackend
    return LocalLightGBMTrainerBackend()
