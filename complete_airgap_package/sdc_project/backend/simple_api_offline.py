#!/usr/bin/env python3
"""
Simple API - 완전 오프라인 버전
외부 패키지 의존성 없이 Python 표준 라이브러리만 사용
"""
import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

class OfflineAPIHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)

        if parsed_path.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = {
                "status": "healthy",
                "mode": "pure_offline",
                "message": "Backend API running in pure offline mode",
                "services": ["document_upload", "basic_chat", "health_check"]
            }
            self.wfile.write(json.dumps(response).encode())

        elif parsed_path.path == '/api/v1/health':
            self.do_GET()  # 동일한 응답

        else:
            self.send_response(404)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = {"error": "Not found", "mode": "pure_offline"}
            self.wfile.write(json.dumps(response).encode())

    def do_POST(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        response = {
            "status": "processed",
            "mode": "pure_offline",
            "message": "Request processed in offline mode"
        }
        self.wfile.write(json.dumps(response).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8000))
    server = HTTPServer(('0.0.0.0', port), OfflineAPIHandler)
    print(f"🔧 Backend API starting on port {port} (Pure Offline Mode)")
    print(f"🔒 Air-gap environment - No external dependencies")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Backend API stopped")
        server.shutdown()
