#!/usr/bin/env python3
"""
Air-gap compatible HTTP server for SDC backend
Uses only Python standard library - no external dependencies
"""

import json
import http.server
import socketserver
import urllib.parse
from pathlib import Path
import os
import sys

PORT = 8000

class AIRGAPHandler(http.server.BaseHTTPRequestHandler):

    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'ok', 'mode': 'airgap'}).encode())

        elif self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {
                'message': 'SDC Backend - Air-gap Mode',
                'status': 'running',
                'mode': 'offline',
                'version': '1.0.0'
            }
            self.wfile.write(json.dumps(response).encode())

        elif self.path.startswith('/api'):
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {
                'message': 'API endpoint available in Air-gap mode',
                'endpoint': self.path,
                'mode': 'offline'
            }
            self.wfile.write(json.dumps(response).encode())

        else:
            self.send_response(404)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Not found'}).encode())

    def do_POST(self):
        # Handle POST requests for basic API compatibility
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        response = {
            'message': 'POST request handled in Air-gap mode',
            'endpoint': self.path,
            'mode': 'offline'
        }
        self.wfile.write(json.dumps(response).encode())

    def log_message(self, format, *args):
        print(f"[AIRGAP SERVER] {format % args}")

if __name__ == "__main__":
    print(f"🚀 Starting SDC Air-gap Server on port {PORT}")
    print(f"📡 Server mode: OFFLINE/AIR-GAP")
    print(f"🔧 Python version: {sys.version}")

    with socketserver.TCPServer(("", PORT), AIRGAPHandler) as httpd:
        print(f"✅ Server ready at http://0.0.0.0:{PORT}")
        print("🔄 Air-gap mode - using only Python standard library")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 Server shutting down...")
            httpd.shutdown()