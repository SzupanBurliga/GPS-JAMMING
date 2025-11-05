#!/usr/bin/env python3
"""
Prosty serwer HTTP do odbierania danych JSON z gnssdec
Uruchom: python3 test_http_server.py
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import datetime

class JSONHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/data':
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)

            try:
                data = json.loads(body.decode('utf-8'))
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                print(f"\n[{timestamp}] Otrzymano dane JSON:")
                print(json.dumps(data, indent=2, ensure_ascii=False))

                try:
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Content-Length', '15')
                    self.end_headers()
                    self.wfile.write(b'{"status":"ok"}')
                except (BrokenPipeError, ConnectionResetError):
                    # Klient zamknął połączenie - to OK
                    pass
            except Exception as e:
                print(f"Błąd parsowania JSON: {e}")
                try:
                    self.send_response(400)
                    self.end_headers()
                except (BrokenPipeError, ConnectionResetError):
                    pass
        else:
            try:
                self.send_response(404)
                self.end_headers()
            except (BrokenPipeError, ConnectionResetError):
                pass

    def log_message(self, format, *args):
        # Wyciszenie standardowych logów HTTP
        pass

if __name__ == '__main__':
    server_address = ('127.0.0.1', 1234)
    httpd = HTTPServer(server_address, JSONHandler)
    print(f"Serwer HTTP nasłuchuje na http://127.0.0.1:1234")
    print("Czekam na dane z gnssdec...\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nZamykanie serwera...")
        httpd.server_close()
