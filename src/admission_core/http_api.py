"""HTTP endpoints backed by a validated model release."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from admission_core.inference import AdmissionPredictor, PredictionError


def create_server(host="127.0.0.1", port=8000, models_dir="models"):
    predictor, loading_error = None, None
    try:
        predictor = AdmissionPredictor(models_dir)
    except Exception as error:
        loading_error = str(error)

    class Handler(BaseHTTPRequestHandler):
        def send_json(self, status, data):
            payload = json.dumps(data, ensure_ascii=False, allow_nan=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            if self.path == "/api/v2/health":
                self.send_json(200 if predictor else 503, {"status": "ready" if predictor else "not_ready",
                    "model_loaded": predictor is not None, "error": loading_error})
            elif self.path == "/api/v2/models/current-metadata":
                self.send_json(200 if predictor else 503, predictor.metadata if predictor else {"error": loading_error})
            else:
                self.send_json(404, {"error": "Endpoint không tồn tại"})

        def do_POST(self):
            if self.path != "/api/v2/predict/admission-probability":
                self.send_json(404, {"error": "Endpoint không tồn tại"})
                return
            if predictor is None:
                self.send_json(503, {"error": loading_error})
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 65536:
                    raise PredictionError("Kích thước request không hợp lệ", 400)
                request = json.loads(self.rfile.read(size).decode("utf-8"))
                self.send_json(200, predictor.predict(request))
            except PredictionError as error:
                self.send_json(error.status, {"status": "error", "message": str(error)})
            except (ValueError, UnicodeError) as error:
                self.send_json(400, {"status": "error", "message": str(error)})
            except Exception:
                self.send_json(500, {"status": "error", "message": "Lỗi suy luận nội bộ"})

    return ThreadingHTTPServer((host, port), Handler)


def start_server(host="127.0.0.1", port=8000, models_dir="models"):
    server = create_server(host, port, models_dir)
    print(f"API listening at http://{host}:{server.server_port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
