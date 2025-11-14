import os
from PySide6.QtCore import QThread, Signal
import subprocess  
import sys
import json
import threading
import time
import numpy as np
from http.server import HTTPServer, BaseHTTPRequestHandler
import datetime
from .checkIfJamming import analyze_file_for_jamming 
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'skrypty'))
from triangulateRSSI import triangulate_jammer_location

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
        pass

class GPSAnalysisThread(QThread):

    analysis_complete = Signal(list)  
    progress_update = Signal(int, str)
    new_analysis_text = Signal(str) 
    new_position_data = Signal(float, float, float)
    jamming_analysis_complete = Signal(object, object)
    triangulation_complete = Signal(dict)

    def __init__(self, file_paths, power_threshold=120.0, antenna_positions=None, satellite_system='GPS'):
        super().__init__()
        self.file_paths = file_paths
        self.power_threshold = power_threshold
        self.antenna_positions = antenna_positions if antenna_positions else {
            'antenna1': [0.0, 0.0],
            'antenna2': [0.5, 0.0],
            'antenna3': [0.0, 0.5]
        }
        
        # Mapowanie flagi systemu !
        self.satellite_system = satellite_system
        if satellite_system == 'GPS':
            self.gnss_system_flag = '-g'
        elif satellite_system == 'GLONASS':
            self.gnss_system_flag = '-n'
        elif satellite_system == 'Galileo':
            self.gnss_system_flag = '-l'
        else:
            self.gnss_system_flag = '-g'  # domyślnie GPS
        
        print(f"[WORKER INIT] Utworzono GPSAnalysisThread z pozycjami anten:")
        print(f"[WORKER INIT]   Antena 1: {self.antenna_positions['antenna1']}")
        print(f"[WORKER INIT]   Antena 2: {self.antenna_positions['antenna2']}")
        print(f"[WORKER INIT]   Antena 3: {self.antenna_positions['antenna3']}")
        print(f"[WORKER INIT]   System satelitarny: {self.satellite_system} (flaga: {self.gnss_system_flag})")
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
        self.triangulation_thread = None
        self.total_samples = 0
        self.estimated_total_samples = 0
        self.triangulation_result = None
        self.jamming_analysis_finished = False 
        self.triangulation_started = False  
        self.last_position_before_jamming = {
            'lat': 0.0,
            'lon': 0.0,
            'hgt': 0.0,
            'buffcnt': 0,
            'valid': False
        } 
        self.jamming_analysis_complete.connect(self.on_jamming_detected)
        self.triangulation_complete.connect(self.on_triangulation_complete)
        
        try:
            app_dir = os.path.dirname(os.path.abspath(__file__)) 
        except NameError:
            app_dir = os.getcwd() 
        self.project_root_dir = os.path.dirname(app_dir)
        
        self.gnssdec_path = os.path.join(
            self.project_root_dir, "backend", "bin", "gnssdec"
        )
        if self.file_paths:
            self.calculate_file_samples()
        
    def calculate_file_samples(self):
        try:
            if not self.file_paths or not os.path.exists(self.file_paths[0]):
                return
            
            file_path = self.file_paths[0]
            file_size = os.path.getsize(file_path)
            bytes_per_sample = 2 
            self.total_samples = file_size // bytes_per_sample

            if file_size % 4 == 0: 
                samples_int16 = file_size // 4
                if samples_int16 > 100000:
                    self.total_samples = samples_int16
                    bytes_per_sample = 4
                    
            self.estimated_total_samples = self.total_samples
            
            print(f"[PROGRESS] Plik: {os.path.basename(file_path)}")
            print(f"[PROGRESS] Rozmiar: {file_size} bajtów")
            print(f"[PROGRESS] Bajty na próbkę: {bytes_per_sample}")
            print(f"[PROGRESS] Całkowita liczba próbek: {self.total_samples}")
            print(f"[PROGRESS] Szacowany czas analizy: {self.total_samples / 2048000:.1f}s przy 2.048 MHz")
            
        except Exception as e:
            print(f"[PROGRESS] Błąd przy obliczaniu próbek: {e}")
            self.total_samples = 0

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
                self.update_progress_bar()
                
                if self.current_lat != 0.0 and self.current_lon != 0.0:
                    if self.jamming_analysis_finished and self.jamming_start_sample is not None and not self.triangulation_started:
                        if self.current_buffcnt < self.jamming_start_sample:
                            if (not self.last_position_before_jamming['valid'] or 
                                self.current_buffcnt > self.last_position_before_jamming['buffcnt']):
                                self.last_position_before_jamming = {
                                    'lat': self.current_lat,
                                    'lon': self.current_lon,
                                    'hgt': self.current_hgt,
                                    'buffcnt': self.current_buffcnt,
                                    'valid': True
                                }
                                #print(f"[WORKER] ✅ AKTUALIZACJA ostatniej pozycji przed jammingiem: próbka {self.current_buffcnt} < jamming {self.jamming_start_sample}")
                                #print(f"[WORKER]    📍 Nowa pozycja: {self.current_lat:.8f}, {self.current_lon:.8f}")
                    elif not self.triangulation_started:  # ZMIENIONE: Tylko jeśli triangulacja jeszcze nie została uruchomiona
                        # Analiza jammingu jeszcze trwa - zapisuj pozycję jako kandydata
                        # (zostanie nadpisana jeśli jamming zostanie wykryty wcześniej)
                        candidate_position = {
                            'lat': self.current_lat,
                            'lon': self.current_lon,
                            'hgt': self.current_hgt,
                            'buffcnt': self.current_buffcnt,
                            'valid': True
                        }
                        
                        if self.jamming_start_sample is not None:
                            if self.current_buffcnt < self.jamming_start_sample:
                                if (not self.last_position_before_jamming['valid'] or 
                                    self.current_buffcnt > self.last_position_before_jamming['buffcnt']):
                                    self.last_position_before_jamming = candidate_position
                                    print(f"[WORKER] 🔄 AKTUALIZACJA kandydata na ostatnią pozycję: próbka {self.current_buffcnt} < jamming {self.jamming_start_sample}")
                                    print(f"[WORKER]    📍 Kandydat: {self.current_lat:.8f}, {self.current_lon:.8f}")
                        else:
                            self.last_position_before_jamming = candidate_position
            
            elapsed = data.get('elapsed_time', 'N/A')

            text_output = f"[{elapsed}, {self.current_lat:.6f}, {self.current_lon:.6f}, {self.current_buffcnt}]"
            self.new_analysis_text.emit(text_output)
            
            should_update_gui = self.should_update_gui_position()
            if self.current_lat != 0.0 or self.current_lon != 0.0:
                if should_update_gui:
                    self.new_position_data.emit(self.current_lat, self.current_lon, self.current_hgt)
        except Exception as e:
            print(f"[WORKER] Błąd podczas przetwarzania danych JSON: {e}")
            
    def update_progress_bar(self):
        if self.total_samples > 0 and self.current_buffcnt > 0:
            current_total = max(self.total_samples, self.estimated_total_samples)
            progress_percent = min(100, int((self.current_buffcnt / current_total) * 100))

            if progress_percent % 10 == 0 and progress_percent != getattr(self, '_last_logged_percent', -1):
                print(f"[PROGRESS] Postęp: {progress_percent}% ({self.current_buffcnt}/{int(current_total)} próbek)")
                self._last_logged_percent = progress_percent

            in_jamming_range = self.is_in_jamming_range()
            
            if in_jamming_range:
                if self.triangulation_thread and self.triangulation_thread.is_alive():
                    self.progress_update.emit(progress_percent, "triangulating")
                else:
                    self.progress_update.emit(progress_percent, "jamming")
            else:
                self.progress_update.emit(progress_percent, "normal")
            
            if self.current_buffcnt > self.estimated_total_samples:
                old_estimate = self.estimated_total_samples
                self.estimated_total_samples = self.current_buffcnt * 1.2 
                #print(f"[PROGRESS] Aktualizacja szacowanej liczby próbek: {int(old_estimate)} → {int(self.estimated_total_samples)}")
                
        elif self.current_buffcnt > 0:
            print(f"[PROGRESS] Fallback mode: próbka {self.current_buffcnt} (brak informacji o całkowitej liczbie)")
            
            estimated_file_samples = max(1000000, self.current_buffcnt * 2) # strzelamy
            progress_percent = min(95, int((self.current_buffcnt / estimated_file_samples) * 100))
            self.progress_update.emit(progress_percent, "normal")
        else:
            self.progress_update.emit(0, "normal")
            
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

    def get_triangulation_result(self):
        return self.triangulation_result
    
    def is_in_jamming_range(self):
        if not self.jamming_analysis_finished or self.jamming_start_sample is None:
            return False
        if self.jamming_end_sample is None:
            return self.current_buffcnt >= self.jamming_start_sample
        return (self.jamming_start_sample <= self.current_buffcnt < self.jamming_end_sample)
    
    def should_update_gui_position(self):
        if not self.jamming_analysis_finished:
            return True
        if self.jamming_start_sample is None:
            return True
        if self.is_in_jamming_range():
            return False
        return True

    def on_jamming_detected(self, start_sample, end_sample):
        self.jamming_start_sample = start_sample
        self.jamming_end_sample = end_sample
        if start_sample is not None:
            self.jamming_detected = True
            print(f"\n[JAMMING THREAD] Wykryto jamming: nr probek:  {start_sample} - {end_sample}")
            self.jamming_analysis_finished = True
            
            if self.last_position_before_jamming['valid']:
                if self.last_position_before_jamming['buffcnt'] < start_sample:
                    print(f"[JAMMING THREAD] ✅ ZATWIERDZONA pozycja przed jammingiem: "
                          f"{self.last_position_before_jamming['lat']:.6f}, "
                          f"{self.last_position_before_jamming['lon']:.6f} "
                          f"(próbka {self.last_position_before_jamming['buffcnt']} < jamming {start_sample})")
                else:
                    print(f"[JAMMING THREAD] ❌ ODRZUCONA pozycja - nie jest przed jammingiem!")
                    print(f"[JAMMING THREAD]    Pozycja: próbka {self.last_position_before_jamming['buffcnt']} >= jamming {start_sample}")
                    self.last_position_before_jamming = {
                        'lat': 0.0, 'lon': 0.0, 'hgt': 0.0, 'buffcnt': 0, 'valid': False
                    }
                    print(f"[JAMMING THREAD]    Pozycja wyczyszczona - będzie aktualizowana przez nadchodzące dane gnssdec")
            else:
                print(f"[JAMMING THREAD] Brak zapisanej pozycji - będzie aktualizowana przez gnssdec")
            if len(self.file_paths) >= 2:
                print(f"[JAMMING THREAD] Triangulacja będzie uruchomiona PO zakończeniu gnssdec z ostatnią pozycją")
            else:
                print(f"[JAMMING THREAD] Pominięto triangulację - za mało plików ({len(self.file_paths)})")
                
        else:
            self.jamming_detected = False
            print(f"\n[JAMMING THREAD] Nie wykryto jammingu")
            self.jamming_analysis_finished = True

    def get_test_files_for_triangulation(self):
        test_files = []
        base_dir = os.path.dirname(self.file_paths[0]) if self.file_paths else "../data"
        num_files = len(self.file_paths)
        
        for i in range(min(num_files, 3)): 
            test_filename = f"test{i+1}.bin"
            test_path = os.path.join(base_dir, test_filename)
            
            if os.path.exists(test_path):
                test_files.append(test_path)
                #print(f"[TEST FILES] Znaleziono plik triangulacji: {test_filename}")
            else:
                #print(f"[TEST FILES] OSTRZEŻENIE: Nie znaleziono {test_filename} w {base_dir}")
                if i < len(self.file_paths):
                    test_files.append(self.file_paths[i])
                    #print(f"[TEST FILES] Używam oryginalnego pliku: {os.path.basename(self.file_paths[i])}")
        
        if not test_files:
            #print("[TEST FILES] Brak plików testowych - używam oryginalnych plików")
            return self.file_paths
        
        return test_files

    def on_triangulation_complete(self, result):
        self.triangulation_result = result
        if result['success']:
            geo = result['location_geographic']
            ref_pos = result.get('reference_position')
            
            print(f"\n[TRIANGULATION] ✅ TRIANGULACJA ZAKOŃCZONA SUKCESEM:")
            print(f"[TRIANGULATION]    🎯 Jammer: {geo['lat']:.8f}°N, {geo['lon']:.8f}°E")
            print(f"[TRIANGULATION]    📏 Odległości: {result['distances']}")
            print(f"[TRIANGULATION]    📐 Metoda: {result['num_antennas']}-antenna triangulation")
            
            if ref_pos:
                print(f"[TRIANGULATION]    📍 Pozycja referencyjna: {ref_pos['lat']:.8f}, {ref_pos['lon']:.8f}")
                print(f"[TRIANGULATION]    🔢 Próbka referencyjna: {ref_pos['buffcnt']}")
        else:
            print(f"\n[TRIANGULATION] ❌ BŁĄD TRIANGULACJI: {result['message']}")

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

    def analyze_triangulation_when_ready(self):
        def triangulation_worker():
            try:
                if len(self.file_paths) < 2:
                    self.triangulation_complete.emit({
                        'success': False,
                        'message': f'Triangulacja wymaga minimum 2 plików, masz {len(self.file_paths)}',
                        'distances': None,
                        'location_geographic': None,
                        'num_antennas': len(self.file_paths)
                    })
                    return

                print(f"[TRIANGULATION THREAD] Czekam na wykrycie jammingu i na to, by gnssdec przetworzył próbki do miejsca jammingu...")
                import time
                wait_time = 0.0

                # Najpierw poczekaj aż wykryty zostanie jamming (start_sample ustawiony).
                while not (self.jamming_detected and self.jamming_start_sample is not None):
                    time.sleep(0.5)
                    wait_time += 0.5
                    if int(wait_time) % 10 == 0:
                        print(f"[TRIANGULATION THREAD] Czekam na wykrycie jammingu... ({wait_time:.0f}s)")

                # Gdy znamy numer próbki startu jammigu, poczekaj aż gnssdec
                # przetworzy próbki co najmniej do tej próbki (current_buffcnt >= start_sample).
                # Dzięki temu last_position_before_jamming będzie MAAKSYMALNĄ dostępną próbka < start_sample.
                start_sample = self.jamming_start_sample
                print(f"[TRIANGULATION THREAD] Jamming wykryty: start_sample={start_sample}. Czekam na aktualizacje pozycji z gnssdec...")

                while self.current_buffcnt < start_sample:
                    time.sleep(0.5)
                    wait_time += 0.5
                    # co 10s loguj status
                    if int(wait_time) % 10 == 0:
                        print(f"[TRIANGULATION THREAD] Czekam aż gnssdec osiągnie próbkę {start_sample}... (current_buffcnt={self.current_buffcnt}, waited={wait_time:.0f}s)")
                    # Safety: jeśli czekamy bardzo długo (np. >120s), przerwij i użyj najlepszej dostępnej pozycji
                    if wait_time > 120:
                        print(f"[TRIANGULATION THREAD] Oczekiwanie przekroczyło 120s — używam najlepszej dostępnej pozycji przed jammigem.")
                        break

                if self.last_position_before_jamming['valid']:
                    print(f"[TRIANGULATION THREAD] Jamming wykryty i posiadam pozycję przed jammingiem: próbka {self.last_position_before_jamming['buffcnt']} < jamming start: {start_sample}")
                else:
                    print(f"[TRIANGULATION THREAD] Brak zapisanej pozycji przed jammingiem — użyję fallbacku po current_lat/current_lon lub pozycji domyślnej")
                
                print(f"[TRIANGULATION THREAD] Gotowe do triangulacji po {wait_time}s oczekiwania")

                # Zablokuj dalsze aktualizacje pozycji - triangulacja używa aktualnej pozycji
                # Ustaw flagę triangulation_started żeby proces_incoming_data przestał
                # nadpisywać kandydata na ostatnią pozycję przed jammigem.
                self.triangulation_started = True
                final_position = self.last_position_before_jamming.copy()
                print(f"[TRIANGULATION THREAD] ZABLOKOWANIE pozycji referencyjnej: {final_position['lat']:.8f}, {final_position['lon']:.8f} (próbka {final_position['buffcnt']})")

                print(f"[TRIANGULATION THREAD] Rozpoczynanie triangulacji z {len(self.file_paths)} plikami...")
                
                test_files = self.get_test_files_for_triangulation()
                print(f"[TRIANGULATION THREAD] Używam plików triangulacji: {[os.path.basename(f) for f in test_files]}")
                
                if final_position['valid']:
                    ref_lat = final_position['lat']
                    ref_lon = final_position['lon']
                    # do debugowania
                    #print(f"[TRIANGULATION THREAD] FINALNA POZYCJA REFERENCYJNA:")
                    #print(f"[TRIANGULATION THREAD] Współrzędne: {ref_lat:.8f}, {ref_lon:.8f}")
                    #print(f"[TRIANGULATION THREAD] Próbka: {final_position['buffcnt']} (ostatnia przed jamming {self.jamming_start_sample})")
                    #print(f"[TRIANGULATION THREAD] Różnica: {self.jamming_start_sample - final_position['buffcnt']} próbek przed jammingiem")
                else:
                    ref_lat = self.current_lat if self.current_lat != 0.0 else 50.06143
                    ref_lon = self.current_lon if self.current_lon != 0.0 else 19.93658
                    print(f"[TRIANGULATION THREAD] Punkt referencyjny (fallback): {ref_lat:.6f}, {ref_lon:.6f}")
                    print(f"[TRIANGULATION THREAD] UWAGA: Brak zapisanej pozycji przed jammingiem!")
                
                # Przygotuj pozycje anten w formacie dla triangulate_jammer_location
                # WAŻNE: Konwertuj listy na numpy arrays - algorytm wymaga arrays!
                antenna_positions_meters = [
                    np.array(self.antenna_positions['antenna1']),  # [0.0, 0.0] - zawsze punkt odniesienia
                    np.array(self.antenna_positions['antenna2']),  # np. [0.5, 0.0]
                    np.array(self.antenna_positions['antenna3'])   # np. [0.0, 0.5]
                ]
                
                print(f"[TRIANGULATION THREAD] Pozycje anten przekazane do algorytmu:")
                print(f"[TRIANGULATION THREAD]   Antena 1: x={antenna_positions_meters[0][0]:.3f}m, y={antenna_positions_meters[0][1]:.3f}m")
                print(f"[TRIANGULATION THREAD]   Antena 2: x={antenna_positions_meters[1][0]:.3f}m, y={antenna_positions_meters[1][1]:.3f}m")
                if len(test_files) >= 3:
                    print(f"[TRIANGULATION THREAD]   Antena 3: x={antenna_positions_meters[2][0]:.3f}m, y={antenna_positions_meters[2][1]:.3f}m")
                
                result = triangulate_jammer_location(
                    file_paths=test_files,
                    antenna_positions_meters=antenna_positions_meters,
                    reference_lat=ref_lat,
                    reference_lon=ref_lon,
                    tx_power=40.0,
                    path_loss_exp=3.0,
                    frequency_mhz=1575.42,     
                    threshold=self.power_threshold / 1000.0, 
                    verbose=False 
                )
                
                print(f"[TRIANGULATION THREAD] Triangulacja zakończona: sukces={result['success']}")
                
                if result['success'] and final_position['valid']:
                    result['reference_position'] = {
                        'lat': final_position['lat'],
                        'lon': final_position['lon'],
                        'buffcnt': final_position['buffcnt']
                    }
                
                self.triangulation_complete.emit(result)
                
            except Exception as e:
                print(f"[TRIANGULATION THREAD] Błąd podczas triangulacji: {e}")
                self.triangulation_complete.emit({
                    'success': False,
                    'message': f'Błąd triangulacji: {str(e)}',
                    'distances': None,
                    'location_geographic': None,
                    'num_antennas': len(self.file_paths) if hasattr(self, 'file_paths') else 0
                })
        
        self.triangulation_thread = threading.Thread(target=triangulation_worker)
        self.triangulation_thread.daemon = True
        self.triangulation_thread.start()

    def analyze_triangulation_after_gnssdec(self):
        def triangulation_worker():
            try:
                if len(self.file_paths) < 2:
                    self.triangulation_complete.emit({
                        'success': False,
                        'message': f'Triangulacja wymaga minimum 2 plików, masz {len(self.file_paths)}',
                        'distances': None,
                        'location_geographic': None,
                        'num_antennas': len(self.file_paths)
                    })
                    return

                print(f"[TRIANGULATION THREAD] Rozpoczynanie triangulacji po zakończeniu gnssdec z {len(self.file_paths)} plikami...")
                
                test_files = self.get_test_files_for_triangulation()
                print(f"[TRIANGULATION THREAD] Używam plików triangulacji: {[os.path.basename(f) for f in test_files]}")
                final_position = None
                
                if self.jamming_detected and self.last_position_before_jamming['valid']:
                    final_position = self.last_position_before_jamming.copy()
                    ref_lat = final_position['lat']
                    ref_lon = final_position['lon']
                    #print(f"[TRIANGULATION THREAD]   FINALNA POZYCJA REFERENCYJNA (przed jammingiem):")
                    #print(f"[TRIANGULATION THREAD]    Współrzędne: {ref_lat:.8f}, {ref_lon:.8f}")
                    #print(f"[TRIANGULATION THREAD]    Próbka: {final_position['buffcnt']} (ostatnia przed jamming {self.jamming_start_sample})")
                    #print(f"[TRIANGULATION THREAD]    Różnica: {self.jamming_start_sample - final_position['buffcnt']} próbek przed jammingiem")
                elif self.current_lat != 0.0 and self.current_lon != 0.0:
                    final_position = {
                        'lat': self.current_lat,
                        'lon': self.current_lon,
                        'hgt': self.current_hgt,
                        'buffcnt': self.current_buffcnt,
                        'valid': True
                    }
                    ref_lat = final_position['lat']
                    ref_lon = final_position['lon']
                    #print(f"[TRIANGULATION THREAD] FINALNA POZYCJA REFERENCYJNA:")
                    print(f"[TRIANGULATION THREAD] Współrzędne: {ref_lat:.8f}, {ref_lon:.8f}")
                    #print(f"[TRIANGULATION THREAD] Próbka: {final_position['buffcnt']}")
                else:
                    ref_lat = 50.06143
                    ref_lon = 19.93658
                    print(f"[TRIANGULATION THREAD] Punkt referencyjny (fallback): {ref_lat:.6f}, {ref_lon:.6f}")
                    print(f"[TRIANGULATION THREAD] UWAGA: Brak zapisanej pozycji!")

                # Przygotuj pozycje anten w formacie dla triangulate_jammer_location
                # WAŻNE: Konwertuj listy na numpy arrays - algorytm wymaga arrays!
                antenna_positions_meters = [
                    np.array(self.antenna_positions['antenna1']),  # [0.0, 0.0] - zawsze punkt odniesienia
                    np.array(self.antenna_positions['antenna2']),  # np. [0.5, 0.0]
                    np.array(self.antenna_positions['antenna3'])   # np. [0.0, 0.5]
                ]
                
                print(f"[TRIANGULATION THREAD] Pozycje anten przekazane do algorytmu:")
                print(f"[TRIANGULATION THREAD]   Antena 1: x={antenna_positions_meters[0][0]:.3f}m, y={antenna_positions_meters[0][1]:.3f}m")
                print(f"[TRIANGULATION THREAD]   Antena 2: x={antenna_positions_meters[1][0]:.3f}m, y={antenna_positions_meters[1][1]:.3f}m")
                if len(test_files) >= 3:
                    print(f"[TRIANGULATION THREAD]   Antena 3: x={antenna_positions_meters[2][0]:.3f}m, y={antenna_positions_meters[2][1]:.3f}m")
                
                result = triangulate_jammer_location(
                    file_paths=test_files,
                    antenna_positions_meters=antenna_positions_meters,
                    reference_lat=ref_lat,
                    reference_lon=ref_lon,
                    tx_power=40.0,
                    path_loss_exp=3.0,
                    frequency_mhz=1575.42,
                    threshold=self.power_threshold / 1000.0,
                    verbose=False
                )
                
                print(f"[TRIANGULATION THREAD] Triangulacja zakończona: sukces={result['success']}")

                if result['success'] and final_position and final_position['valid']:
                    result['reference_position'] = {
                        'lat': final_position['lat'],
                        'lon': final_position['lon'],
                        'buffcnt': final_position['buffcnt']
                    }
                
                self.triangulation_complete.emit(result)
                
            except Exception as e:
                print(f"[TRIANGULATION THREAD] Błąd podczas triangulacji: {e}")
                self.triangulation_complete.emit({
                    'success': False,
                    'message': f'Błąd triangulacji: {str(e)}',
                    'distances': None,
                    'location_geographic': None,
                    'num_antennas': len(self.file_paths) if hasattr(self, 'file_paths') else 0
                })
        
        self.triangulation_thread = threading.Thread(target=triangulation_worker)
        self.triangulation_thread.daemon = True
        self.triangulation_thread.start()

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
        if len(self.file_paths) >= 2:
            self.analyze_triangulation_when_ready()
        
        try:
            print(f"[WORKER] Uruchamianie analizy {self.gnssdec_path}...")
            print(f"[WORKER] System satelitarny: {self.satellite_system} (flaga: {self.gnss_system_flag})")
            gnssdec_command = [self.gnssdec_path, self.gnss_system_flag, file1]
            result = subprocess.run(gnssdec_command, check=True, capture_output=True, text=True)
            print(f"[WORKER] Analiza {self.gnssdec_path} zakończona.")
            
        except subprocess.CalledProcessError as e:
            print(f"BŁĄD: Proces {self.gnssdec_path} zakończył się błędem!")
        except Exception as e:
            print(f"Nieoczekiwany błąd podczas uruchamiania gnssdec: {e}")
            
        finally:
            self.progress_update.emit(100, "completed")
            
            self.shutdown_server()
            print("[WORKER] Analiza gnssdec zakończona.")
            triangulation_completed = False
            
            if self.triangulation_thread and self.triangulation_thread.is_alive():
                print("[WORKER] Czekanie na zakończenie triangulacji (uruchomionej równolegle)...")
                self.triangulation_thread.join(timeout=20) 
                if self.triangulation_thread.is_alive():
                    print("[WORKER] OSTRZEŻENIE: Triangulacja nadal trwa w tle!")
                else:
                    print("[WORKER] Triangulacja równoległa zakończona.")
                    triangulation_completed = True
            elif len(self.file_paths) >= 2 and not self.triangulation_started:
                print("[WORKER] Uruchamiam triangulację")
                self.analyze_triangulation_after_gnssdec()
                if self.triangulation_thread:
                    print("[WORKER] Czekam na zakończenie triangulacji...")
                    self.triangulation_thread.join(timeout=25)  
                    if self.triangulation_thread.is_alive():
                        print("[WORKER] OSTRZEŻENIE: Triangulacja nadal trwa!")
                    else:
                        print("[WORKER] Triangulacja zakończona.")
                        triangulation_completed = True

            print("[WORKER] Wątek zakończył pracę. Odblokowanie UI.")

            if self.jamming_detected:
                result_info = [{
                    'type': 'jamming',
                    'start_sample': self.jamming_start_sample,
                    'end_sample': self.jamming_end_sample,
                    'triangulation': self.triangulation_result
                }]
                self.analysis_complete.emit(result_info)
            else:
                result_info = [{
                    'type': 'no_jamming',
                    'triangulation': self.triangulation_result
                }]
                self.analysis_complete.emit(result_info)

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
        
        if self.triangulation_thread and self.triangulation_thread.is_alive():
            print("[WORKER] Czekam na zakończenie triangulacji...")
            self.triangulation_thread.join(timeout=10)  # triangulacja moze trwac dluzej
            if self.triangulation_thread.is_alive():
                print("[WORKER] Triangulacja nadal trwa w tle...")
            else:
                print("[WORKER] Triangulacja zakończona.")

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