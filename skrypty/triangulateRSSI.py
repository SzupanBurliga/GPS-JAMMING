import numpy as np
import math

# ==============================================================================
#   KONFIGURACJA I STAŁE
# ==============================================================================

# PARAMETRY KALIBRACYJNE (domyślne)
DEFAULT_CALIBRATED_TX_POWER = 40.0
DEFAULT_CALIBRATED_PATH_LOSS_EXPONENT = 3.0
DEFAULT_SIGNAL_FREQUENCY_MHZ = 1575.42
DEFAULT_SIGNAL_THRESHOLD = 0.1

# PARAMETRY PRZESZUKIWANIA SIATKI (GRID SEARCH)
GRID_DENSITY = 300          # Rozdzielczość siatki (im więcej, tym precyzyjniej, ale wolniej)
SEARCH_RANGE_MULTIPLIER = 1.5

# Stałe do konwersji metrów na stopnie/minuty geograficzne
METERS_PER_DEGREE_LAT = 111320.0
METERS_PER_DEGREE_LON = 111320.0 

# ==============================================================================
#   FUNKCJE POMOCNICZE (IQ, Konwersja, Dystans)
# ==============================================================================

def read_iq_data(filename):
  ##Wczytywanie i przetwarzanie IQ w uint8 z pliku  
    try:
        raw_data = np.fromfile(filename, dtype=np.uint8)
        float_data = (raw_data.astype(np.float32) - 127.5) / 127.5
        complex_data = float_data[0::2] + 1j * float_data[1::2]
        return complex_data
    except FileNotFoundError:
        print(f"BŁĄD: Plik '{filename}' nie został znaleziony.")
        return None

def find_change_point(amplitude_data, threshold):
  ##Znajdowanie pierwszego indeksu przekraczającego próg 
    change_indices = np.where(amplitude_data > threshold)[0]
    return change_indices[0] if len(change_indices) > 0 else None

def meters_to_geographic_degrees(meters_x, meters_y, reference_lat=50.0):
  ##Konwersja przesunięcia w metrach na stopnie geograficzne 
    delta_lat_degrees = meters_y / METERS_PER_DEGREE_LAT

    meters_per_degree_lon = METERS_PER_DEGREE_LON * math.cos(math.radians(reference_lat))
    delta_lon_degrees = meters_x / meters_per_degree_lon
    
    delta_lat_minutes = delta_lat_degrees * 60
    delta_lon_minutes = delta_lon_degrees * 60
    
    return delta_lat_degrees, delta_lon_degrees, delta_lat_minutes, delta_lon_minutes

def calculate_distance_from_file(iq_filename, 
                               tx_power=DEFAULT_CALIBRATED_TX_POWER,
                               path_loss_exp=DEFAULT_CALIBRATED_PATH_LOSS_EXPONENT,
                               frequency_mhz=DEFAULT_SIGNAL_FREQUENCY_MHZ,
                               threshold=DEFAULT_SIGNAL_THRESHOLD,
                               verbose=True):
  ##Obliczanie odległości na podstawie pliku z danymi IQ 
    if verbose:
        print(f"  Analizowanie pliku '{iq_filename}'  ")
    iq_samples = read_iq_data(iq_filename)
    if iq_samples is None or len(iq_samples) == 0: return None
    amplitude = np.abs(iq_samples)
    turn_on_index = find_change_point(amplitude, threshold)
    if turn_on_index is not None:
        avg_amplitude = np.mean(amplitude[turn_on_index:])
        if avg_amplitude == 0: return None
        received_power_db = 10 * np.log10(avg_amplitude**2)
        if verbose:
            print(f"Sygnał wykryty. Średnia amplituda: {avg_amplitude:.4f}")
            print(f"Hipotetyczna moc odebrana: {received_power_db:.2f} dB")
        path_loss_at_1m = 20 * np.log10(frequency_mhz) - 27.55
        distance = 10 ** ((tx_power - received_power_db - path_loss_at_1m) / (10 * path_loss_exp))
        if verbose:
            print(f">>> Oszacowana odległość: {distance:.2f} m\n")
        return distance
    else:
        if verbose:
            print(f"Nie wykryto sygnału z progiem {threshold}.\n")
        return None

# ==============================================================================
#   ALGORYTM GRID SEARCH (Zastępuje metody geometryczne)
# ==============================================================================

def perform_grid_search(positions, radii):
  ##Znajduje punkt najlepiej pasujący do zestawu odległości od anten metodą Grid Search. Minimalizuje błąd bezwzględny sumy różnic odległości.
    # Konwersja na numpy array dla pewności
    positions = np.array(positions)
    radii = np.array(radii)
    
    print(f"Uruchamianie przeszukiwania siatki {GRID_DENSITY}x{GRID_DENSITY}...")
    
    max_radius = np.max(radii)
    # Środek obszaru poszukiwań to średnia pozycja anten
    center = np.mean(positions, axis=0)
    
    search_range = max_radius * SEARCH_RANGE_MULTIPLIER
    
    # Tworzenie siatki punktów
    x_coords = np.linspace(center[0] - search_range, center[0] + search_range, GRID_DENSITY)
    y_coords = np.linspace(center[1] - search_range, center[1] + search_range, GRID_DENSITY)
    grid_x, grid_y = np.meshgrid(x_coords, y_coords)
    
    # Obliczanie macierzy błędu dla każdego punktu siatki
    total_error = np.zeros_like(grid_x)
    
    for pos, r in zip(positions, radii):
        # Odległość każdego punktu siatki od danej anteny
        dist_to_pos = np.sqrt((grid_x - pos[0])**2 + (grid_y - pos[1])**2)
        # Dodajemy błąd (różnica między odległością z siatki a zmierzoną RSSI)
        total_error += np.abs(dist_to_pos - r)
    
    # Znalezienie indeksu punktu z najmniejszym błędem
    min_error_idx = np.unravel_index(np.argmin(total_error), total_error.shape)
    best_location = np.array([grid_x[min_error_idx], grid_y[min_error_idx]])
    
    return best_location

# ==============================================================================
#   GŁÓWNA FUNKCJA LOGIKI BIZNESOWEJ
# ==============================================================================

def triangulate_jammer_location(file_paths, 
                              antenna_positions_meters=None,
                              reference_lat=50.00898,
                              reference_lon=19.98287,
                              tx_power=DEFAULT_CALIBRATED_TX_POWER,
                              path_loss_exp=DEFAULT_CALIBRATED_PATH_LOSS_EXPONENT,
                              frequency_mhz=DEFAULT_SIGNAL_FREQUENCY_MHZ,
                              threshold=DEFAULT_SIGNAL_THRESHOLD,
                              verbose=False):
  ## Główna funkcja określająca lokalizację jammera. Teraz używa metody Grid Search zamiast prostych przecięć geometrycznych.
    if len(file_paths) < 2:
        return {
            'success': False,
            'distances': None,
            'location_meters': None,
            'location_geographic': None,
            'message': 'Wymagane są co najmniej 2 pliki z danymi anten.',
            'num_antennas': len(file_paths)
        }
    
    # Domyślne pozycje anten (w metrach)
    if antenna_positions_meters is None:
        antenna_positions_meters = [
            np.array([0.0, 0.0]),      # Antena 0 - punkt odniesienia
            np.array([0.5, 0.0]),      # Antena 1
            np.array([0.0, 0.5])       # Antena 2 (opcjonalna)
        ]
        # Przytnij listę domyślnych pozycji do liczby plików
        antenna_positions_meters = antenna_positions_meters[:len(file_paths)]
    
    # 1. Oblicz odległości dla każdej anteny
    distances = []
    valid_positions = []
    valid_radii = []

    for i, file_path in enumerate(file_paths):
        dist = calculate_distance_from_file(
            file_path, tx_power, path_loss_exp, frequency_mhz, threshold, verbose
        )
        distances.append(dist)
        
        if dist is not None:
            valid_radii.append(dist)
            # Pobierz pozycję odpowiadającą tej antenie (zabezpieczenie przed index error)
            if i < len(antenna_positions_meters):
                valid_positions.append(np.array(antenna_positions_meters[i]))
            else:
                if verbose: print(f"Ostrzeżenie: Brak zdefiniowanej pozycji dla anteny {i}, pomijanie.")
                valid_radii.pop() # Cofnij dodanie promienia

    # Sprawdzenie czy mamy wystarczająco danych po obliczeniach
    if len(valid_radii) < 2:
        return {
            'success': False,
            'distances': distances,
            'location_meters': None,
            'location_geographic': None,
            'message': f'Nie udało się obliczyć poprawnej odległości dla wystarczającej liczby anten (min 2). Sukcesy: {len(valid_radii)}',
            'num_antennas': len(file_paths)
        }

    # 2. Uruchomienie algorytmu Grid Search
    if verbose:
        print(f"Obliczanie lokalizacji metodą Grid Search dla {len(valid_positions)} anten.")
        for i, (pos, r) in enumerate(zip(valid_positions, valid_radii)):
            print(f"  Antena [{pos[0]:.1f}, {pos[1]:.1f}] -> r={r:.2f}m")

    best_location = perform_grid_search(valid_positions, valid_radii)
    
    # 3. Konwersja wyników na format wyjściowy
    if best_location is not None:
        delta_lat_deg, delta_lon_deg, delta_lat_min, delta_lon_min = meters_to_geographic_degrees(
            best_location[0], best_location[1], reference_lat
        )
        
        absolute_lat = reference_lat + delta_lat_deg
        absolute_lon = reference_lon + delta_lon_deg
        
        message = f"Lokalizacja wyznaczona algorytmem Grid Search (błąd minimalny). x={best_location[0]:.2f}m, y={best_location[1]:.2f}m"

        return {
            'success': True,
            'distances': distances,
            'location_meters': best_location.tolist(),
            'location_geographic': {
                'lat': absolute_lat,
                'lon': absolute_lon,
                'lat_offset_degrees': delta_lat_deg,
                'lon_offset_degrees': delta_lon_deg,
                'lat_offset_minutes': delta_lat_min,
                'lon_offset_minutes': delta_lon_min
            },
            'message': message,
            'num_antennas': len(valid_radii)
        }
    else:
        return {
            'success': False,
            'distances': distances,
            'location_meters': None,
            'location_geographic': None,
            'message': 'Algorytm Grid Search nie zwrócił wyniku.',
            'num_antennas': len(valid_radii)
        }

# ==============================================================================
#   URUCHOMIENIE TESTOWE
# ==============================================================================

if __name__ == "__main__":
    # Przykładowe ścieżki
    example_files = [
        '/home/szymon/Downloads/GPS_JAMMING/GPS-JAMMING/GpsJammerApp/test1.bin',
        '/home/szymon/Downloads/GPS_JAMMING/GPS-JAMMING/GpsJammerApp/test2.bin',
        '/home/szymon/Downloads/GPS_JAMMING/GPS-JAMMING/GpsJammerApp/test3.bin'
    ]
    
    # Aby test zadziałał, pliki muszą istnieć. Tu tylko symulacja wywołania:
    print("--- TEST GRID SEARCH ---")
    print("Uwaga: Upewnij się, że ścieżki do plików w sekcji __main__ są poprawne, jeśli chcesz uruchomić to bezpośrednio.")
    
    # W normalnym użyciu importujesz funkcję triangulate_jammer_location do innego skryptu.
    # Poniżej kod, który możesz odkomentować, jeśli masz pliki .bin w folderze
    
  ##
    result = triangulate_jammer_location(
        example_files,
        reference_lat=50.00898,
        reference_lon=19.98287,
        verbose=True
    )
    
    if result['success']:
        loc_geo = result['location_geographic']
        print(f"\n>>> ZNALEZIONO LOKALIZACJĘ (Grid Search) <<<")
        print(f"    Współrzędne: {loc_geo['lat']:.8f}°N, {loc_geo['lon']:.8f}°E")
        print(f"    Metry (x,y): {result['location_meters'][0]:.2f}, {result['location_meters'][1]:.2f}")
        print(f"    Wiadomość: {result['message']}")
    else:
        print(f"\n>>> BŁĄD <<<")
        print(result['message'])
  ##
