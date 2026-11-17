import json
from threading import Thread
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import pytest
from admission_core.http_api import create_server
from admission_core.inference import AdmissionPredictor, PredictionError


def request_payload(score=23.0, school="S0"):
    return {"score_year": 2026, "school_id": school, "score_code": "M0", "score_blocks": "A00", "total_score": score}


def test_real_predictions(trained_root):
    predictor = AdmissionPredictor(trained_root)
    first = predictor.predict(request_payload())
    second = predictor.predict(request_payload(school="S5"))
    better = predictor.predict(request_payload(score=28))
    assert first["admission_percentile_forecast"]["expected_percentile_mean"] != second["admission_percentile_forecast"]["expected_percentile_mean"]
    assert first["student_percentile"]["calculated_rank_pct"] > better["student_percentile"]["calculated_rank_pct"]
    assert first["admission_probability"]["probability_value"] <= better["admission_probability"]["probability_value"]


@pytest.mark.parametrize("score", [-1, 31, float("nan"), float("inf"), True, "23"])
def test_bad_inputs(trained_root, score):
    with pytest.raises(PredictionError):
        AdmissionPredictor(trained_root).predict(request_payload(score=score))


def test_http_endpoints(trained_root):
    server = create_server(port=0, models_dir=trained_root)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}/api/v2"
    try:
        with urlopen(base + "/health") as response:
            assert json.load(response)["model_loaded"]
        with urlopen(base + "/models/current-metadata") as response:
            assert json.load(response)["feature_schema_version"] == "3.0"
        request = Request(base + "/predict/admission-probability", json.dumps(request_payload()).encode(),
                          {"Content-Type": "application/json"})
        with urlopen(request) as response:
            assert json.load(response)["status"] == "success"
        with pytest.raises(HTTPError) as error:
            urlopen(Request(base + "/predict/admission-probability", b"invalid"))
        assert error.value.code == 400
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_health_not_ready(tmp_path):
    server = create_server(port=0, models_dir=tmp_path)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with pytest.raises(HTTPError) as error:
            urlopen(f"http://127.0.0.1:{server.server_port}/api/v2/health")
        assert error.value.code == 503
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
