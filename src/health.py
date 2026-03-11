# -*- coding: utf-8 -*-
"""
Health check server — Hugging Face Spaces yêu cầu expose 1 port.
Chạy song song với bot, trả 200 OK cho HF health check.
"""

import threading
from http.server import HTTPServer, BaseHTTPRequestHandler


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, *args):
        pass  # Không log health check requests


def start_health_server(port: int = 7860) -> None:
    """Chạy HTTP server trên background thread (non-blocking)."""
    server = HTTPServer(("0.0.0.0", port), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
