import os
from PySide6.QtCore import QThread, Signal
import subprocess  
import sys
import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import datetime
from .checkIfJamming import analyze_file_for_jamming 

class _DataReceiverHandler(BaseHTTPRequestHandler):
    thread_instance = None

    def do_POST(self):
        if self.path == '/data':
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_length)
                data = json.loads(body.decode('utf-8'))
                
                if self.thread_instance:
                    self.thread_instance.process_incoming_data(data)
                    
                try:
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    response_body = b'{"status":"ok"}'
                    self.send_header('Content-Length', str(len(response_body)))
                    self.end_headers()
                    self.wfile.write(response_body)
                except (BrokenPipeError, ConnectionResetError):
                    pass
                    
            except json.JSONDecodeError:
                print("Błąd parsowania JSON")
                try:
                    self.send_response(400)
                    self.end_headers()
                except (BrokenPipeError, ConnectionResetError):
                    pass
            except Exception as e:
                print(f"[HTTP HANDLER] Błąd: {e}")
                try:
                    self.send_response(500)
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
        # Wycisza logi serwera HTTP
        pass

class GPSAnalysisThread(QThread):

    analysis_complete = Signal(list)  
    progress_update = Signal(int)     
    new_analysis_text = Signal(str) 
    new_position_data = Signal(float, float, float)
    jamming_analysis_complete = Signal(object, object) 

    def __init__(self, file_paths, power_threshold=120.0):
        super().__init__()
        self.file_paths = file_paths
        self.power_threshold = power_threshold
        self.current_buffcnt = 0
        self.current_lat = 0.0
        self.current_lon = 0.0
        self.current_hgt = 0.0
        self.current_nsat = 0
        self.current_gdop = 0.0
        self.current_clk_bias = 0.0
        self.jamming_detected = False
        self.jamming_start_sample = None
        self.jamming_end_sample = None
        self.http_server = None
        self.http_thread = None
        self.jamming_thread = None
        
        self.jamming_analysis_complete.connect(self.on_jamming_detected) 
        
        try:
            app_dir = os.path.dirname(os.path.abspath(__file__)) 
        except NameError:
            app_dir = os.getcwd() 
        self.project_root_dir = os.path.dirname(app_dir)
        
        self.gnssdec_path = os.path.join(
            self.project_root_dir, "backendhttp", "bin", "gnssdec"
        )
        
    def process_incoming_data(self, data):
        try:
            position = data.get('position', {})
            if position:
                self.current_buffcnt = position.get('buffcnt', 0)
                self.current_lat = float(position.get('lat', 0.0))
                self.current_lon = float(position.get('lon', 0.0))
                self.current_hgt = float(position.get('hgt', 0.0))
                self.current_nsat = position.get('nsat', 0)
                self.current_gdop = float(position.get('gdop', 0.0))
                self.current_clk_bias = float(position.get('clk_bias', 0.0))
            
            elapsed = data.get('elapsed_time', 'N/A')

            text_output = f"[{elapsed}, {self.current_lat:.6f}, {self.current_lon:.6f}, {self.current_buffcnt}]"
            self.new_analysis_text.emit(text_output)
            
            if self.current_lat != 0.0 or self.current_lon != 0.0:
                 self.new_position_data.emit(self.current_lat, self.current_lon, self.current_hgt)
        except Exception as e:
            print(f"[WORKER] Błąd podczas przetwarzania danych JSON: {e}")
            
    def get_current_position_data(self):
        return {
            'buffcnt': self.current_buffcnt,
            'lat': self.current_lat,
            'lon': self.current_lon,
            'hgt': self.current_hgt,
            'nsat': self.current_nsat,
            'gdop': self.current_gdop,
            'clk_bias': self.current_clk_bias
        }
    
    def get_current_sample_number(self):
        return self.current_buffcnt

    def on_jamming_detected(self, start_sample, end_sample):
        self.jamming_start_sample = start_sample
        self.jamming_end_sample = end_sample
        if start_sample is not None:
            self.jamming_detected = True
            print(f"\n[JAMMING THREAD] Wykryto jamming: próbki {start_sample} - {end_sample}")
        else:
            self.jamming_detected = False
            print(f"\n[JAMMING THREAD] Nie wykryto jammingu")

    def analyze_jamming_in_background(self, file_path):
        def jamming_worker():
            try:
                print(f"[JAMMING THREAD] Rozpoczynanie analizy jammingu w pliku: {file_path}")
                jamming_start, jamming_end = analyze_file_for_jamming(file_path, self.power_threshold)
                print(f"[JAMMING THREAD] Analiza zakończona: start={jamming_start}, end={jamming_end}")
                self.jamming_analysis_complete.emit(jamming_start, jamming_end)
            except Exception as e:
                print(f"[JAMMING THREAD] Błąd podczas analizy jammingu: {e}")
                self.jamming_analysis_complete.emit(None, None)
        
        self.jamming_thread = threading.Thread(target=jamming_worker)
        self.jamming_thread.daemon = True
        self.jamming_thread.start()

    def run(self):
        _DataReceiverHandler.thread_instance = self

        try:
            server_address = ('127.0.0.1', 1234)
            self.http_server = HTTPServer(server_address, _DataReceiverHandler)
            self.http_thread = threading.Thread(target=self.http_server.serve_forever)
            self.http_thread.daemon = True 
            self.http_thread.start()
            print("[WORKER] Serwer HTTP uruchomiony na porcie 1234.") 
            
        except Exception as e:
            print(f"[WORKER] BŁĄD: Nie można uruchomić serwera HTTP na porcie 1234: {e}")
            self.analysis_complete.emit([])
            return
        
        file1 = self.file_paths[0] if self.file_paths else None
        
        if not file1 or not os.path.exists(file1):
            print(f"BŁĄD: Plik {file1} nie istnieje. Przerwanie.")
            self.shutdown_server()
            self.analysis_complete.emit([])
            return
            
        if not os.path.exists(self.gnssdec_path):
            print(f"BŁĄD: Nie znaleziono programu {self.gnssdec_path}. Przerwanie.")
            self.shutdown_server()
            self.analysis_complete.emit([])
            return
        
        self.analyze_jamming_in_background(file1)
        try:
            print(f"[WORKER] Uruchamianie analizy {self.gnssdec_path}...")
            print(f"[WORKER] --- WĄTEK CZEKA NA ZAKOŃCZENIE ./gnssdec ---")
            gnssdec_command = [self.gnssdec_path, file1]
            result = subprocess.run(gnssdec_command, check=True, capture_output=True, text=True)
            print(f"[WORKER] Analiza {self.gnssdec_path} zakończona.")
            
        except subprocess.CalledProcessError as e:
            print(f"BŁĄD: Proces {self.gnssdec_path} zakończył się błędem!")
        except Exception as e:
            print(f"Nieoczekiwany błąd podczas uruchamiania gnssdec: {e}")
            
        finally:
            self.shutdown_server()
            print("[WORKER] Wątek zakończył pracę. Odblokowanie UI.")
            
            if self.jamming_detected:
                jamming_info = [{
                    'type': 'jamming',
                    'start_sample': self.jamming_start_sample,
                    'end_sample': self.jamming_end_sample
                }]
                self.analysis_complete.emit(jamming_info)
            else:
                no_jamming_info = [{'type': 'no_jamming'}]
                self.analysis_complete.emit(no_jamming_info)

    def shutdown_server(self):
        if self.http_server:
            print("[WORKER] Zamykanie serwera HTTP...")
            self.http_server.shutdown() 
            self.http_thread.join() 
            self.http_server = None
            self.http_thread = None
            print("[WORKER] Serwer HTTP zamknięty.")
        
        if self.jamming_thread and self.jamming_thread.is_alive():
            print("[WORKER] Czekam na zakończenie analizy jammingu...")
            self.jamming_thread.join(timeout=5)
            if self.jamming_thread.is_alive():
                print("[WORKER] Analiza jammingu nadal trwa w tle...")
            else:
                print("[WORKER] Analiza jammingu zakończona.")

    def use_get_data(self):
        if self.current_buffcnt > 0:
            print(f"Aktualny buffcnt: {self.current_buffcnt}")
            print(f"Pozycja: {self.current_lat}, {self.current_lon}")
        
        data = self.get_current_position_data()
        if data['buffcnt'] > 0:
            print(f"Kompletne dane: {data}")


# PORADNIK DO INNEGO UŻYCIA !!!
# Przykład użycia analizy jammingu jako multithread:
# 
# def on_jamming_result(start_sample, end_sample):
#     if start_sample is not None:
#         print(f"Wykryto jamming: próbki {start_sample} - {end_sample}")
#     else:
#         print("Nie wykryto jammingu")
#
# # Stwórz wątek z progiem mocy 120.0
# thread = GPSAnalysisThread(["/path/to/file.bin"], power_threshold=120.0)
# thread.jamming_analysis_complete.connect(on_jamming_result)
# thread.start()