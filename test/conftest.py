import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest
import yaml
from admission_core.demo import generate_demo
from admission_core.pipeline import AdmissionPipeline


@pytest.fixture(scope="session")
def demo_root(tmp_path_factory):
    return generate_demo(tmp_path_factory.mktemp("admission"), score_rows=22000)


@pytest.fixture(scope="session")
def trained_root(demo_root):
    config = yaml.safe_load((demo_root / "local_pandas.yaml").read_text(encoding="utf-8"))
    AdmissionPipeline(config).execute()
    return demo_root / "local_pandas" / "models"
