"""IoC Factory and Dynamic Plugin Dispatcher.
Resolves and instantiates execution adapters based on configuration.
Supports built-in backends, user class plugins, and zero-syntax external scripts.
"""

import importlib
import subprocess
from typing import Dict, Any
from admission_core.ports import BaseCDFPort, BaseFeaturePipelinePort, BaseTrainerPort, BaseIngestionPort

# Wrapper cho trường hợp User dùng Script Độc lập (Zero-Syntax)
class ExternalScriptCDFAdapter(BaseCDFPort):
    def __init__(self, command_template: str):
        self.command_template = command_template

    def compute_cdf(self, raw_dist_sources: Dict[str, str], output_uri: str, options: dict = None) -> str:
        input_uri = raw_dist_sources.get("score_distribution_ct2006", "")
        cmd = self.command_template.format(input_uri=input_uri, output_uri=output_uri)
        print(f"[Factory: EXTERNAL_SCRIPT] Kích hoạt script của user: {cmd}")
        subprocess.run(cmd, shell=True, check=True)
        return output_uri

def resolve_adapter(stage_cfg: Dict[str, Any], default_class):
    """Phân giải adapter từ cấu hình (hỗ trợ built-in, class_adapter, external_script)"""
    if not stage_cfg:
        return default_class()

    adapter_type = stage_cfg.get("type", "builtin")
    
    if adapter_type == "external_script":
        cmd = stage_cfg.get("command", "")
        return ExternalScriptCDFAdapter(cmd)
        
    elif adapter_type == "class_adapter":
        target = stage_cfg.get("target")
        if not target:
            raise ValueError("Khai báo 'class_adapter' bắt buộc phải có thuộc tính 'target'.")
        module_name, class_name = target.rsplit(".", 1)
        mod = importlib.import_module(module_name)
        cls = getattr(mod, class_name)
        # Bọc adapter của user nếu chưa kế thừa BaseCDFPort
        instance = cls()
        if hasattr(instance, "execute"):
            class DuckTypedWrapper(BaseCDFPort):
                def __init__(self, obj): self.obj = obj
                def compute_cdf(self, raw_dist_sources, output_uri, options=None):
                    inp = raw_dist_sources.get("score_distribution_ct2006", "")
                    return self.obj.execute(input_uri=inp, output_uri=output_uri)
            return DuckTypedWrapper(instance)
        return instance

    return default_class()

def get_ingestion_backend(config: Dict[str, Any]) -> BaseIngestionPort:
    from admission_core.backends.local_pandas.ingestion import LocalIngestionBackend
    return LocalIngestionBackend()

def get_cdf_backend(config: Dict[str, Any]) -> BaseCDFPort:
    from admission_core.backends.local_pandas.cdf import LocalPandasCDFBackend
    stage_cfg = config.get("backend_execution", {}).get("cdf_stage", {})
    return resolve_adapter(stage_cfg, LocalPandasCDFBackend)

def get_feature_backend(config: Dict[str, Any]) -> BaseFeaturePipelinePort:
    from admission_core.backends.local_pandas.feature_pipeline import LocalPandasFeatureBackend
    return LocalPandasFeatureBackend()

def get_trainer_backend(config: Dict[str, Any]) -> BaseTrainerPort:
    from admission_core.backends.local_pandas.trainer import LocalLightGBMTrainerBackend
    return LocalLightGBMTrainerBackend()

