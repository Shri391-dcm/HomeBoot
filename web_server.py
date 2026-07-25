#!/usr/bin/env python3
"""
Simple HTTP server for ApplianceAI web interface
Serves HTML/CSS/JS from ./frontend/
Run: python3 web_server.py (from project root)
Then open: http://localhost:8080
"""

import http.server
import socketserver
import os
import sys
from pathlib import Path

PORT = 8080

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # Serve from frontend folder
        frontend_path = Path(__file__).parent / 'frontend'
        super().__init__(*args, directory=str(frontend_path), **kwargs)
    
    def end_headers(self):
        """Add CORS headers to allow calls to localhost:8000"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

def run_server():
    try:
        with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
            print(f"🚀 Web server running on http://localhost:{PORT}")
            print(f"   Serving from: ./frontend/")
            print(f"   Press Ctrl+C to stop")
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n✅ Server stopped")
        sys.exit(0)
    except OSError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    run_server()
