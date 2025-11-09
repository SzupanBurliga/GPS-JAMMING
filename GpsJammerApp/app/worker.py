import os
import subprocess
import sys
import json
import threading
import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from PySide6.QtCore import QThread, Signal
import numpy as np
import math


#  Parametry konfiguracyjne dla logiki jammingu 
#   Opcjonalne Antena 2 (jeśli nie jest używana, pozostawić None)
FILE_ANT2 = None
ANT2_POS = None

#   Parametry kalibracyjne
CALIBRATED_TX_POWER = 40.0
CALIBRATED_PATH_LOSS_EXPONENT = 3.0

#   Parametry sygnału
SIGNAL_FREQUENCY_MHZ = 1575.42
SIGNAL_THRESHOLD = 0.1

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
                    
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"status":"ok"}')
            except (json.JSONDecodeError, BrokenPipeError, ConnectionResetError) as e:
                # Błędy, które można zignorować w kontekście działania
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
    # Zmieniony sygnał: emituje słownik z wynikiem analizy jammingu
    jamming_analysis_complete = Signal(dict) 

    def __init__(self, file_paths):
        super().__init__()
        self.file_paths = file_paths
        self.current_buffcnt = 0
        self.current_lat = 0.0
        self.current_lon = 0.0
        self.current_hgt = 0.0
        self.current_nsat = 0
        self.current_gdop = 0.0
        self.current_clk_bias = 0.0
        
        self.jamming_detected = False
        self.jamming_result = None  # Przechowuje wynik z analizy jammingu
        
        self.http_server = None
        self.http_thread = None
        self.jamming_thread = None
        
        # Pozycje anten dla analizy jammingu
        self.antenna_positions = [
            np.array([0.0, 0.0]),      # Pozycja ANT0
            np.array([0.5, 0.0]),   # Pozycja ANT1
            # ANT2_POS                   # Opcjonalna trzecia antena
        ]
        # self.calculate_antenna_positions() #Odkoomentować gdy pozycje lon i lat obu anten są znane 
        
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
            'buffcnt': self.current_buffcnt, 'lat': self.current_lat, 'lon': self.current_lon,
            'hgt': self.current_hgt, 'nsat': self.current_nsat, 'gdop': self.current_gdop,
            'clk_bias': self.current_clk_bias
        }
    
    def get_current_sample_number(self):
        return self.current_buffcnt

    def on_jamming_detected(self, result):
        self.jamming_result = result
        if result and result.get('status') == 'success':
            self.jamming_detected = True
            print(f"\n[JAMMING THREAD] Lokalizacja jammera zakończona sukcesem: {result}")
        else:
            self.jamming_detected = False
            error_msg = result.get('message', 'Nieznany błąd')
            print(f"\n[JAMMING THREAD] Nie wykryto jammera lub wystąpił błąd: {error_msg}")

    def analyze_jamming_in_background(self):
        def jamming_worker():
            try:
                print(f"[JAMMING THREAD] Rozpoczynanie lokalizacji jammera dla plików: {self.file_paths}")
                result = run_jamming_localization(self.file_paths, self.antenna_positions)
                print(f"[JAMMING THREAD] Analiza zakończona.")
                self.jamming_analysis_complete.emit(result)
            except Exception as e:
                print(f"[JAMMING THREAD] Krytyczny błąd podczas analizy jammingu: {e}")
                error_result = {'status': 'error', 'message': str(e)}
                self.jamming_analysis_complete.emit(error_result)
        
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
        
        # Sprawdzenie, czy pliki istnieją
        if not self.file_paths:
            print("BŁĄD: Nie podano plików do analizy. Przerwanie.")
            self.shutdown_server()
            self.analysis_complete.emit([])
            return
            
        for path in self.file_paths:
            if not os.path.exists(path):
                print(f"BŁĄD: Plik {path} nie istnieje. Przerwanie.")
                self.shutdown_server()
                self.analysis_complete.emit([])
                return
            
        if not os.path.exists(self.gnssdec_path):
            print(f"BŁĄD: Nie znaleziono programu {self.gnssdec_path}. Przerwanie.")
            self.shutdown_server()
            self.analysis_complete.emit([])
            return
        
        # Uruchomienie analizy jammingu w tle
        self.analyze_jamming_in_background()

        try:
            print(f"[WORKER] Uruchamianie analizy {self.gnssdec_path} dla pliku {self.file_paths[0]}...")
            print(f"[WORKER] WĄTEK CZEKA NA ZAKOŃCZENIE ./gnssdec ---")
            gnssdec_command = [self.gnssdec_path, self.file_paths[0]]
            subprocess.run(gnssdec_command, check=True, capture_output=True, text=True)
            print(f"[WORKER] Analiza {self.gnssdec_path} zakończona.")
        except subprocess.CalledProcessError:
            print(f"BŁĄD: Proces {self.gnssdec_path} zakończył się błędem!")
        except Exception as e:
            print(f"Nieoczekiwany błąd podczas uruchamiania gnssdec: {e}")
            
        finally:
            self.shutdown_server()
            print("[WORKER] Wątek zakończył pracę. Odblokowanie UI.")
            
            final_info = []
            if self.jamming_detected:
                jamming_info = {
                    'type': 'jamming_location',
                    'result': self.jamming_result
                }
                final_info.append(jamming_info)
            else:
                no_jamming_info = {
                    'type': 'no_jamming', 
                    'result': self.jamming_result
                }
                final_info.append(no_jamming_info)
                
            self.analysis_complete.emit(final_info)

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
            self.jamming_thread.join()


#Wczytuje i przetwarza dane IQ (uint8) z pliku binarnego.
def read_iq_data(filename):
    try:
        raw_data = np.fromfile(filename, dtype=np.uint8)
        float_data = (raw_data.astype(np.float32) - 127.5) / 127.5
        complex_data = float_data[0::2] + 1j * float_data[1::2]
        return complex_data
    except FileNotFoundError:
        print(f"BŁĄD: Plik '{filename}' nie został znaleziony.")
        return None
    
#Znajduje pierwszy indeks, w którym amplituda przekracza próg.
def find_change_point(amplitude_data, threshold):
    change_indices = np.where(amplitude_data > threshold)[0]
    return change_indices[0] if len(change_indices) > 0 else None

#Oblicza odległość od nadajnika na podstawie mocy sygnału w pliku IQ.
def calculate_distance_from_file(iq_filename):
    print(f"  Analizowanie pliku '{iq_filename}'")
    iq_samples = read_iq_data(iq_filename)
    if iq_samples is None or len(iq_samples) == 0: return None
    
    amplitude = np.abs(iq_samples)
    turn_on_index = find_change_point(amplitude, SIGNAL_THRESHOLD)
    
    if turn_on_index is not None:
        avg_amplitude = np.mean(amplitude[turn_on_index:])
        if avg_amplitude == 0: return None
        
        received_power_db = 10 * np.log10(avg_amplitude**2)
        print(f"Sygnał wykryty. Średnia amplituda: {avg_amplitude:.4f}")
        print(f"Hipotetyczna moc odebrana: {received_power_db:.2f} dB")
        
        path_loss_at_1m = 20 * np.log10(SIGNAL_FREQUENCY_MHZ) - 27.55
        distance = 10 ** ((CALIBRATED_TX_POWER - received_power_db - path_loss_at_1m) / (10 * CALIBRATED_PATH_LOSS_EXPONENT))
        print(f">>> Oszacowana odległość: {distance:.2f} m\n")
        return distance
    else:
        print(f"Nie wykryto sygnału z progiem {SIGNAL_THRESHOLD}.\n")
        return None

#Oblicza punkty przecięcia dwóch okręgów.
def find_circle_intersections(p0, r0, p1, r1):
    d = np.linalg.norm(p1 - p0)
    if d > r0 + r1 or d < abs(r0 - r1) or d == 0:
        return None  # Warunki braku przecięcia
    
    a = (r0**2 - r1**2 + d**2) / (2 * d)
    if r0**2 < a**2:
        return None  # Błąd zaokrąglenia
        
    h = math.sqrt(r0**2 - a**2)
    p2 = p0 + a * (p1 - p0) / d
    x1 = p2[0] + h * (p1[1] - p0[1]) / d
    y1 = p2[1] - h * (p1[0] - p0[0]) / d
    x2 = p2[0] - h * (p1[1] - p0[1]) / d
    y2 = p2[1] + h * (p1[0] - p0[0]) / d
    return [np.array([x1, y1]), np.array([x2, y2])]

#Estymuje najbardziej prawdopodobną lokalizację, gdy okręgi się nie przecinają.
def find_best_estimate_no_intersection(p0, r0, p1, r1):
    d = np.linalg.norm(p1 - p0)
    if d == 0: return None
    unit_vector = (p1 - p0) / d
    point_on_0 = p0 + r0 * unit_vector
    point_on_1 = p1 - r1 * unit_vector
    best_estimate = (point_on_0 + point_on_1) / 2
    return best_estimate

#Oblicza lokalizację na podstawie odległości od trzech punktów.
def trilaterate(p0, r0, p1, r1, p2, r2):
    x0, y0 = p0; x1, y1 = p1; x2, y2 = p2
    A = 2 * (x1 - x0)
    B = 2 * (y1 - y0)
    C = r0**2 - r1**2 - x0**2 + x1**2 - y0**2 + y1**2
    D = 2 * (x2 - x1)
    E = 2 * (y2 - y1)
    F = r1**2 - r2**2 - x1**2 + x2**2 - y1**2 + y2**2
    determinant = A * E - B * D
    if abs(determinant) < 1e-9:
        print("BŁĄD: Anteny są współliniowe. Nie można jednoznacznie określić lokalizacji.")
        return None
    x = (C * E - F * B) / determinant
    y = (A * F - D * C) / determinant
    return np.array([x, y])

#Główna funkcja do procesu lokalizacji jammera, zwraca słownik z wynikiem
def run_jamming_localization(file_paths, antenna_positions):
    if not file_paths or len(file_paths) < 2:
        return {'status': 'error', 'message': 'Wymagane są co najmniej dwa pliki dla 2 anten.'}
    if not antenna_positions or len(antenna_positions) < 2:
        return {'status': 'error', 'message': 'Wymagane są co najmniej dwie pozycje anten.'}

    dist0 = calculate_distance_from_file(file_paths[0])
    dist1 = calculate_distance_from_file(file_paths[1])
    
    ant0_pos = antenna_positions[0]
    ant1_pos = antenna_positions[1]

    USE_THREE_ANTENNAS = len(file_paths) > 2 and len(antenna_positions) > 2

    if USE_THREE_ANTENNAS:
        print("Wykryto konfigurację dla 3 anten.\n")
        dist2 = calculate_distance_from_file(file_paths[2])
        ant2_pos = antenna_positions[2]
        
        if dist0 is None or dist1 is None or dist2 is None:
            return {'status': 'error', 'message': 'Nie udało się obliczyć jednej lub więcej odległości.'}
        
        location = trilaterate(ant0_pos, dist0, ant1_pos, dist1, ant2_pos, dist2)
        
        if location is not None:
            return {'status': 'success', 'type': 'trilateration', 'locations': [location.tolist()]}
        else:
            return {'status': 'error', 'message': 'Nie udało się obliczyć lokalizacji metodą trilateracji.'}
    else:
        print("Uruchamianie obliczeń dla 2 anten.\n")
        if dist0 is None or dist1 is None:
            return {'status': 'error', 'message': 'Nie udało się obliczyć jednej z odległości.'}
        
        intersections = find_circle_intersections(ant0_pos, dist0, ant1_pos, dist1)
        
        if intersections:
            loc1, loc2 = intersections
            return {'status': 'success', 'type': 'intersection', 'locations': [loc1.tolist(), loc2.tolist()]}
        else:
            print("Okręgi się nie przecinają. Uruchamianie estymacji...\n")
            best_guess = find_best_estimate_no_intersection(ant0_pos, dist0, ant1_pos, dist1)
            if best_guess is not None:
                return {'status': 'success', 'type': 'estimation', 'locations': [best_guess.tolist()]}
            else:
                return {'status': 'error', 'message': 'Nie udało się znaleźć oszacowania dla 2 anten.'}

#Metoda do obliczania i aktualizowania pozycji anten z lat i lon
def calculate_antenna_positions(self):
    # Przykładowe współrzędne geograficzne anten (długość i szerokość geograficzna)
    ant0_long, ant0_lat = 21.0122, 52.2297  # Przykład: Warszawa
    ant1_long, ant1_lat = 21.0150, 52.2300  # Przykład: Warszawa, inna lokalizacja

    # Konwersja na płaskie współrzędne (metody uproszczonej projekcji)
    R = 6371000  # Promień Ziemi w metrach
    
    # Obliczenia dla ANT0 - nasz punkt odniesienia [0,0]
    ref_lon_rad = np.radians(ant0_long)
    ref_lat_rad = np.radians(ant0_lat)

    # Obliczenia dla ANT1 względem ANT0
    ant1_lon_rad = np.radians(ant1_long)
    ant1_lat_rad = np.radians(ant1_lat)

    # Różnica w radianach
    dLon = ant1_lon_rad - ref_lon_rad
    dLat = ant1_lat_rad - ref_lat_rad

    # Uproszczona konwersja na metry
    ant1x = R * dLon * np.cos(ref_lat_rad)
    ant1y = R * dLat

    # ANT0 jest teraz w punkcie [0,0] układu kartezjańskiego
    self.antenna_positions = [
        np.array([0.0, 0.0]),      # Pozycja ANT0 jako środek układu
        np.array([ant1x, ant1y]),   # Pozycja ANT1 w metrach względem ANT0
    ]
