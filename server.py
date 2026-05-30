import os
import sys
import json
import socket
import threading
import time
import urllib.parse
import webbrowser
from http.server import SimpleHTTPRequestHandler, HTTPServer
from pathlib import Path

# Config and scanning hooks
from app import run_scan

# Server global variables
LAST_HEARTBEAT = time.time()
SHUTDOWN_TIMEOUT = 25.0  # Shutdown if no heartbeat for 25 seconds
STATIC_DIR = Path(__file__).parent / "static"
IS_SCANNING = False

class DashboardHTTPRequestHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress logging spam in console to keep terminal clean
        pass

    def translate_path(self, path):
        # Redirect root to index.html inside the static folder
        if path == "/" or path == "":
            return str(STATIC_DIR / "index.html")
        return str(STATIC_DIR / path.lstrip("/"))

    def do_POST(self):
        global LAST_HEARTBEAT, IS_SCANNING
        parsed_url = urllib.parse.urlparse(self.path)
        
        # Handle API: Heartbeat
        if parsed_url.path == "/api/heartbeat":
            LAST_HEARTBEAT = time.time()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "time": LAST_HEARTBEAT, "scanning": IS_SCANNING}).encode("utf-8"))
            return
            
        # Handle API: Trigger Scan
        elif parsed_url.path == "/api/scan":
            if IS_SCANNING:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": "Scan already in progress"}).encode("utf-8"))
                return
                
            IS_SCANNING = True
            
            def perform_scan_thread():
                global IS_SCANNING
                try:
                    run_scan(console_output=False)
                finally:
                    IS_SCANNING = False
            
            # Run scan in background thread
            threading.Thread(target=perform_scan_thread, daemon=True).start()
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "message": "Scan started"}).encode("utf-8"))
            return
            
        self.send_error(404, "Not Found")

    def do_GET(self):
        global LAST_HEARTBEAT, IS_SCANNING
        parsed_url = urllib.parse.urlparse(self.path)
        
        # Handle favicon requests gracefully to avoid 404 noise
        if parsed_url.path == "/favicon.ico":
            self.send_response(200)
            self.send_header("Content-Type", "image/x-icon")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
            
        # Handle API: Get Stats
        if parsed_url.path == "/api/stats":
            # Refresh heartbeat on stats fetch
            LAST_HEARTBEAT = time.time()
            report_file = Path("pdf_ocr_data.json")
            data = {
                "files": [], 
                "directories": [], 
                "stats": {
                    "total_pdfs": 0, 
                    "already_searchable": 0, 
                    "ocr_succeeded": 0, 
                    "ocr_failed": 0
                }, 
                "scanning": IS_SCANNING
            }
            
            if report_file.exists():
                try:
                    with open(report_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except Exception:
                    pass
            data["scanning"] = IS_SCANNING
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode("utf-8"))
            return
            
        # Handle file serving for PDF previewing: /files/<path>
        elif parsed_url.path.startswith("/files/"):
            # Clean and sanitize the path
            rel_file_path = urllib.parse.unquote(parsed_url.path[7:])  # Strip "/files/"
            file_path = Path(rel_file_path).resolve()
            
            # Security checks: Ensure it exists, is a file, and has PDF extension
            if file_path.exists() and file_path.is_file() and file_path.suffix.lower() == ".pdf":
                try:
                    self.send_response(200)
                    self.send_header("Content-Type", "application/pdf")
                    self.send_header("Content-Length", str(file_path.stat().st_size))
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    with open(file_path, "rb") as f:
                        while True:
                            chunk = f.read(65536)
                            if not chunk:
                                break
                            self.wfile.write(chunk)
                    return
                except Exception as e:
                    self.send_error(500, f"Error reading file: {e}")
                    return
            else:
                self.send_error(404, "File not found or access denied")
                return

        # Default fallback to serve static files
        super().do_GET()

def get_free_port():
    """Finds an available local port dynamically."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port

def start_dashboard():
    global LAST_HEARTBEAT
    port = get_free_port()
    server_address = ("127.0.0.1", port)
    
    # Create static directory if it does not exist
    STATIC_DIR.mkdir(exist_ok=True)
    
    httpd = HTTPServer(server_address, DashboardHTTPRequestHandler)
    print(f"\nStarting PDFocr Dashboard on: http://127.0.0.1:{port}")
    print("Bound strictly to loopback interface 127.0.0.1 (local accessibility only).")
    print("Closing the browser tab or hitting Ctrl+C will terminate this server.")
    
    # Setup initial heartbeat time
    LAST_HEARTBEAT = time.time()
    
    # Heartbeat monitoring loop
    def monitor_heartbeat():
        while True:
            time.sleep(2)
            elapsed = time.time() - LAST_HEARTBEAT
            if elapsed > SHUTDOWN_TIMEOUT:
                print(f"\nNo active browser session detected for {SHUTDOWN_TIMEOUT}s. Auto-shutting down server...")
                os._exit(0)
                
    # Run monitor in daemon thread
    threading.Thread(target=monitor_heartbeat, daemon=True).start()
    
    # Auto-launch default browser
    url = f"http://127.0.0.1:{port}"
    webbrowser.open(url)
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        sys.exit(0)
