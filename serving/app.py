"""Decoupled Model Serving Service.
Provides high-performance RESTful inference API independent of heavy big data platforms.
Uses Python built-in HTTP server with JSON REST API endpoints.
"""

import sys
import json
import time
import math
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import joblib
import numpy as np

from admission_core.specs.math_formulas import calculate_admission_probability, classify_decision_tier

# Nạp model và metadata khi khởi động
MODEL_DIR = Path("models")
best_model = None
metadata = {}

try:
    if (MODEL_DIR / "best_lightgbm_regressor.joblib").exists():
        best_model = joblib.load(MODEL_DIR / "best_lightgbm_regressor.joblib")
    if (MODEL_DIR / "model_metadata.json").exists():
        with open(MODEL_DIR / "model_metadata.json", "r", encoding="utf-8") as f:
            metadata = json.load(f)
except Exception as e:
    print(f"⚠️ Cảnh báo khởi động Serving: Chưa tải được mô hình ({e})")

class AdmissionInferenceHandler(BaseHTTPRequestHandler):
    def _send_json(self, status_code: int, data: dict):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"))

    def do_GET(self):
        if self.path == "/api/v2/health":
            self._send_json(200, {
                "status": "UP",
                "model_loaded": best_model is not None,
                "timestamp": time.time()
            })
        elif self.path == "/api/v2/models/current-metadata":
            self._send_json(200, metadata)
        else:
            self._send_json(404, {"error": "Endpoint không tồn tại"})

    def do_POST(self):
        if self.path == "/api/v2/predict/admission-probability":
            t_start = time.time()
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            
            try:
                req = json.loads(body)
                # Giả lập suy luận Module 4
                raw_score = float(req.get("total_score", 25.0))
                # Điểm 25/30 giả định tương ứng phân vị top 5%
                student_rank_pct = max(0.001, min(0.999, 1.0 - (raw_score / 30.0) ** 1.5))
                
                pred_mean = 0.05
                pred_var = 0.0004
                
                # Nếu có model nạp sẵn, ta có thể dự đoán vector đặc trưng
                # Ở đây ta tính xác suất theo Module 4 giải tích:
                prob = calculate_admission_probability(student_rank_pct, pred_mean, pred_var)
                tier = classify_decision_tier(prob)
                latency = (time.time() - t_start) * 1000

                res = {
                    "status": "success",
                    "student_percentile": {
                        "block": req.get("score_blocks", "A00"),
                        "calculated_rank_pct": round(student_rank_pct, 4),
                        "rank_interpretation": f"Thí sinh nằm trong Top {student_rank_pct*100:.2f}% toàn quốc"
                    },
                    "admission_percentile_forecast": {
                        "expected_percentile_mean": pred_mean,
                        "expected_percentile_variance": pred_var,
                        "confidence_scenarios_80pct": {
                            "intense_competition_q10": max(0.001, pred_mean - 0.02),
                            "base_expected_q50": pred_mean,
                            "cooling_down_q90": min(0.999, pred_mean + 0.03)
                        }
                    },
                    "admission_probability": {
                        "probability_value": round(prob, 4),
                        "probability_percentage": f"{prob*100:.2f}%",
                        "decision_tier": tier,
                        "recommendation_guidance": "Xác suất được tính toán theo mô hình phân vị cân bằng động Module 4."
                    },
                    "inference_latency_ms": round(latency, 2)
                }
                self._send_json(200, res)

            except Exception as e:
                self._send_json(400, {"status": "error", "message": str(e)})
        else:
            self._send_json(404, {"error": "Endpoint không tồn tại"})

def start_server(host: str = "127.0.0.1", port: int = 8000):
    server = HTTPServer((host, port), AdmissionInferenceHandler)
    print(f"🚀 Model Serving API đang lắng nghe tại: http://{host}:{port}")
    print(f"👉 Health Check: http://{host}:{port}/api/v2/health")
    print(f"👉 Metadata: http://{host}:{port}/api/v2/models/current-metadata")
    print(f"👉 Inference: POST http://{host}:{port}/api/v2/predict/admission-probability")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nĐang tắt Server...")
        server.server_close()

if __name__ == "__main__":
    start_server()

