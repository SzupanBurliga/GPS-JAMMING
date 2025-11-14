import numpy as np
import math

# PARAMETRY KALIBRACYJNE (domyślne)
DEFAULT_CALIBRATED_TX_POWER = 40.0
DEFAULT_CALIBRATED_PATH_LOSS_EXPONENT = 3.0
DEFAULT_SIGNAL_FREQUENCY_MHZ = 1575.42
DEFAULT_SIGNAL_THRESHOLD = 0.1

# Stałe do konwersji metrów na stopnie/minuty geograficzne
METERS_PER_DEGREE_LAT = 111320.0  # przybliżona wartość dla szerokości geograficznej
METERS_PER_DEGREE_LON = 111320.0  # będzie korygowana w zależności od szerokości

#Wczytywanie i przetwarzanie IQ w uint8 z pliku
def read_iq_data(filename):
    try:
        raw_data = np.fromfile(filename, dtype=np.uint8)
        float_data = (raw_data.astype(np.float32) - 127.5) / 127.5
        complex_data = float_data[0::2] + 1j * float_data[1::2]
        return complex_data
    except FileNotFoundError:
        print(f"BŁĄD: Plik '{filename}' nie został znaleziony.")
        return None

#Znajdowanie pierwszego indeksu przekraczajacego próg
def find_change_point(amplitude_data, threshold):
    change_indices = np.where(amplitude_data > threshold)[0]
    return change_indices[0] if len(change_indices) > 0 else None

# Konwersja metrów na stopnie geograficzne
def meters_to_geographic_degrees(meters_x, meters_y, reference_lat=50.0):
    """
    Konwertuje przesunięcie w metrach na stopnie/minuty geograficzne.
    
    Args:
        meters_x: przesunięcie w metrach (wschód/zachód)
        meters_y: przesunięcie w metrach (północ/południe)
        reference_lat: szerokość geograficzna referencyjna do korekcji longitude
    
    Returns:
        tuple: (delta_lat_degrees, delta_lon_degrees, delta_lat_minutes, delta_lon_minutes)
    """
    # Szerokość geograficzna (latitude) - stała wartość na całym świecie
    delta_lat_degrees = meters_y / METERS_PER_DEGREE_LAT
    
    # Długość geograficzna (longitude) - zależy od szerokości geograficznej
    meters_per_degree_lon = METERS_PER_DEGREE_LON * math.cos(math.radians(reference_lat))
    delta_lon_degrees = meters_x / meters_per_degree_lon
    
    # Konwersja na minuty (1 stopień = 60 minut)
    delta_lat_minutes = delta_lat_degrees * 60
    delta_lon_minutes = delta_lon_degrees * 60
    
    return delta_lat_degrees, delta_lon_degrees, delta_lat_minutes, delta_lon_minutes

#Obliczanie odległości metodą RSSI
def calculate_distance_from_file(iq_filename, 
                               tx_power=DEFAULT_CALIBRATED_TX_POWER,
                               path_loss_exp=DEFAULT_CALIBRATED_PATH_LOSS_EXPONENT,
                               frequency_mhz=DEFAULT_SIGNAL_FREQUENCY_MHZ,
                               threshold=DEFAULT_SIGNAL_THRESHOLD,
                               verbose=True):
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

#   FUNKCJE OBLICZENIOWE DLA 2 ANTEN  

#Obliczanie punktów przecięcia dwóch okręgów
def find_circle_intersections(p0, r0, p1, r1):
    d = np.linalg.norm(p1 - p0)
    if d > r0 + r1 or d < abs(r0 - r1) or d == 0:
        return None # Warunki braku przecięcia
    
    a = (r0**2 - r1**2 + d**2) / (2 * d)
    if r0**2 < a**2:
        return None # Błąd zaokrąglenia, traktujemy jak brak przecięcia

    h = math.sqrt(r0**2 - a**2)
    p2 = p0 + a * (p1 - p0) / d
    x1 = p2[0] + h * (p1[1] - p0[1]) / d
    y1 = p2[1] - h * (p1[0] - p0[0]) / d
    x2 = p2[0] - h * (p1[1] - p0[1]) / d
    y2 = p2[1] + h * (p1[0] - p0[0]) / d
    return [np.array([x1, y1]), np.array([x2, y2])]

#Brak przecięcia, estymacja najbardziej prawdopodobnej lokalizacji 
def find_best_estimate_no_intersection(p0, r0, p1, r1):
    d = np.linalg.norm(p1 - p0)
    if d == 0: return None
    unit_vector = (p1 - p0) / d
    point_on_0 = p0 + r0 * unit_vector
    point_on_1 = p1 - r1 * unit_vector
    best_estimate = (point_on_0 + point_on_1) / 2
    return best_estimate

#   FUNKCJA OBLICZENIOWA DLA 3 ANTEN  
#Obliczanie lokalizacji dla trzech okręgów
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

def triangulate_jammer_location(file_paths, 
                              antenna_positions_meters=None,
                              reference_lat=50.06143,
                              reference_lon=19.93658,
                              tx_power=DEFAULT_CALIBRATED_TX_POWER,
                              path_loss_exp=DEFAULT_CALIBRATED_PATH_LOSS_EXPONENT,
                              frequency_mhz=DEFAULT_SIGNAL_FREQUENCY_MHZ,
                              threshold=DEFAULT_SIGNAL_THRESHOLD,
                              verbose=False):

    if len(file_paths) < 2 or len(file_paths) > 3:
        return {
            'success': False,
            'distances': None,
            'location_meters': None,
            'location_geographic': None,
            'message': 'Wymagane są 2 lub 3 pliki antenna',
            'num_antennas': len(file_paths)
        }
    
    # Domyślne pozycje anten (w metrach)
    if antenna_positions_meters is None:
        antenna_positions_meters = [
            np.array([0.0, 0.0]),      # Antena 0 - punkt odniesienia
            np.array([0.5, 0.0]),      # Antena 1 - 0.5m na wschód
            np.array([0.0, 0.5])       # Antena 2 - 0.5m na północ (jeśli używana)
        ]
    
    # Oblicz odległości dla każdej anteny
    distances = []
    for i, file_path in enumerate(file_paths):
        dist = calculate_distance_from_file(
            file_path, tx_power, path_loss_exp, frequency_mhz, threshold, verbose
        )
        distances.append(dist)
        if dist is None:
            return {
                'success': False,
                'distances': distances,
                'location_meters': None,
                'location_geographic': None,
                'message': f'Nie udało się obliczyć odległości dla anteny {i} z pliku {file_path}',
                'num_antennas': len(file_paths)
            }
    
    # Triangulacja w zależności od liczby anten
    if len(file_paths) == 3:
        # 3 anteny - trilateracja
        location = trilaterate(
            antenna_positions_meters[0], distances[0],
            antenna_positions_meters[1], distances[1],
            antenna_positions_meters[2], distances[2]
        )
        
        if location is None:
            return {
                'success': False,
                'distances': distances,
                'location_meters': None,
                'location_geographic': None,
                'message': 'Anteny są współliniowe - nie można jednoznacznie określić lokalizacji',
                'num_antennas': 3
            }
        
        message = f'Trilateracja dla 3 anten - lokalizacja: x={location[0]:.2f}m, y={location[1]:.2f}m'
        
    else:
        # 2 anteny - przecięcie okręgów
        intersections = find_circle_intersections(
            antenna_positions_meters[0], distances[0],
            antenna_positions_meters[1], distances[1]
        )
        
        if intersections:
            loc1, loc2 = intersections
            dist1 = np.linalg.norm(loc1)
            dist2 = np.linalg.norm(loc2)

            location = loc1 if dist1 <= dist2 else loc2
            
            message = f'Bilateracja dla 2 anten - 2 możliwe lokalizacje: ' + \
                     f'LOK1: x={loc1[0]:.2f}m, y={loc1[1]:.2f}m | ' + \
                     f'LOK2: x={loc2[0]:.2f}m, y={loc2[1]:.2f}m | ' + \
                     f'Wybrano LOK{"1" if dist1 <= dist2 else "2"} (bliższą centrum - może być błędne!)'
        else:
            # Brak przecięcia - estymacja
            location = find_best_estimate_no_intersection(
                antenna_positions_meters[0], distances[0],
                antenna_positions_meters[1], distances[1]
            )
            if location is None:
                return {
                    'success': False,
                    'distances': distances,
                    'location_meters': None,
                    'location_geographic': None,
                    'message': 'Nie udało się znaleźć estymacji lokalizacji',
                    'num_antennas': 2
                }
            message = f'Estymacja dla 2 anten (brak przecięcia) - lokalizacja: x={location[0]:.2f}m, y={location[1]:.2f}m'
    
    # Konwersja na współrzędne geograficzne
    delta_lat_deg, delta_lon_deg, delta_lat_min, delta_lon_min = meters_to_geographic_degrees(
        location[0], location[1], reference_lat
    )
    
    absolute_lat = reference_lat + delta_lat_deg
    absolute_lon = reference_lon + delta_lon_deg
    
    # NOWE: Dodaj informację o alternatywnych lokalizacjach dla 2 anten
    result = {
        'success': True,
        'distances': distances,
        'location_meters': location.tolist(),
        'location_geographic': {
            'lat': absolute_lat,
            'lon': absolute_lon,
            'lat_offset_degrees': delta_lat_deg,
            'lon_offset_degrees': delta_lon_deg,
            'lat_offset_minutes': delta_lat_min,
            'lon_offset_minutes': delta_lon_min
        },
        'message': message,
        'num_antennas': len(file_paths)
    }
    
    # Dodaj alternatywne lokalizacje dla przypadku 2 anten z przecięciem
    if len(file_paths) == 2 and 'intersections' in locals() and intersections:
        loc1, loc2 = intersections
        
        # Konwertuj oba punkty na współrzędne geograficzne
        delta_lat1, delta_lon1, _, _ = meters_to_geographic_degrees(loc1[0], loc1[1], reference_lat)
        delta_lat2, delta_lon2, _, _ = meters_to_geographic_degrees(loc2[0], loc2[1], reference_lat)
        
        result['alternative_locations'] = [
            {
                'location_meters': loc1.tolist(),
                'location_geographic': {
                    'lat': reference_lat + delta_lat1,
                    'lon': reference_lon + delta_lon1,
                    'lat_offset_degrees': delta_lat1,
                    'lon_offset_degrees': delta_lon1
                }
            },
            {
                'location_meters': loc2.tolist(),
                'location_geographic': {
                    'lat': reference_lat + delta_lat2,
                    'lon': reference_lon + delta_lon2,
                    'lat_offset_degrees': delta_lat2,
                    'lon_offset_degrees': delta_lon2
                }
            }
        ]
    
    return result

#   MAIN - przykład użycia

if __name__ == "__main__":
    # Przykładowe pliki - zmień na swoje ścieżki
    example_files = [
        '/home/szymon/Downloads/GPS_JAMMING/GPS-JAMMING/GpsJammerApp/test1.bin',
        '/home/szymon/Downloads/GPS_JAMMING/GPS-JAMMING/GpsJammerApp/test2.bin',
        '/home/szymon/Downloads/GPS_JAMMING/GPS-JAMMING/GpsJammerApp/test3.bin'
    ]
    
    print("=== PRZYKŁAD UŻYCIA TRIANGULACJI JAMMERA ===\n")
    
    # Test z 3 antenami
    print("Test z 3 antenami:")
    result_3ant = triangulate_jammer_location(
        example_files,
        reference_lat=50.06143,  # Kraków
        reference_lon=19.93658,
        verbose=True
    )
    
    if result_3ant['success']:
        loc_geo = result_3ant['location_geographic']
        print(f"📍 Lokalizacja jammera:")
        print(f"   Współrzędne geograficzne: {loc_geo['lat']:.8f}°N, {loc_geo['lon']:.8f}°E")
        print(f"   Przesunięcie: {loc_geo['lat_offset_degrees']:.6f}° ({loc_geo['lat_offset_minutes']:.2f}') lat")
        print(f"                 {loc_geo['lon_offset_degrees']:.6f}° ({loc_geo['lon_offset_minutes']:.2f}') lon")
        print(f"   W metrach: x={result_3ant['location_meters'][0]:.2f}m, y={result_3ant['location_meters'][1]:.2f}m")
        print(f"Odległości: {result_3ant['distances']}")
    else:
        print("❌ BŁĄD:", result_3ant['message'])
    
    print("\n" + "="*60 + "\n")
    
    # Test z 2 antenami
    print("Test z 2 antenami:")
    result_2ant = triangulate_jammer_location(
        example_files[:2],  # tylko pierwsze 2 pliki
        reference_lat=50.06143,
        reference_lon=19.93658,
        verbose=True
    )
    
    if result_2ant['success']:
        loc_geo = result_2ant['location_geographic']
        print("✅ SUKCES!")
        print(f"📍 Wybrana lokalizacja jammera:")
        print(f"   Współrzędne geograficzne: {loc_geo['lat']:.8f}°N, {loc_geo['lon']:.8f}°E")
        print(f"   Przesunięcie: {loc_geo['lat_offset_degrees']:.6f}° ({loc_geo['lat_offset_minutes']:.2f}') lat")
        print(f"                 {loc_geo['lon_offset_degrees']:.6f}° ({loc_geo['lon_offset_minutes']:.2f}') lon")
        print(f"   W metrach: x={result_2ant['location_meters'][0]:.2f}m, y={result_2ant['location_meters'][1]:.2f}m")
        print(f"📏 Odległości: {result_2ant['distances']}")
        
        # Pokaż alternatywne lokalizacje jeśli są dostępne
        if 'alternative_locations' in result_2ant:
            print(f"\n🔄 UWAGA: Dla 2 anten istnieją 2 możliwe lokalizacje!")
            for i, alt_loc in enumerate(result_2ant['alternative_locations'], 1):
                alt_geo = alt_loc['location_geographic']
                alt_meters = alt_loc['location_meters']
                print(f"   Opcja {i}: {alt_geo['lat']:.8f}°N, {alt_geo['lon']:.8f}°E")
                print(f"           (x={alt_meters[0]:.2f}m, y={alt_meters[1]:.2f}m)")
            print("   💡 Użyj trzeciej anteny dla jednoznacznego określenia lokalizacji!")
    else:
        print("❌ BŁĄD:", result_2ant['message'])

"""
=== PRZYKŁAD UŻYCIA W INNYM KODZIE ===

from triangulateRSSI import triangulate_jammer_location

# Przykład 1: Podstawowe użycie z 3 plikami
files = ['antenna0.bin', 'antenna1.bin', 'antenna2.bin']
result = triangulate_jammer_location(files, reference_lat=50.06143, reference_lon=19.93658)

if result['success']:
    geo = result['location_geographic']
    print(f"Jammer wykryty na: {geo['lat']:.6f}°N, {geo['lon']:.6f}°E")
    print(f"Przesunięcie: {geo['lat_offset_minutes']:.1f}' lat, {geo['lon_offset_minutes']:.1f}' lon")
else:
    print(f"Błąd: {result['message']}")

# Przykład 2: Dostosowane parametry
result = triangulate_jammer_location(
    files, 
    reference_lat=50.0,
    reference_lon=20.0,
    tx_power=45.0,              # moc jammera w dBm
    path_loss_exp=2.5,          # wykładnik tłumienia
    frequency_mhz=1575.42,      # częstotliwość GPS L1
    threshold=0.05,             # próg detekcji
    verbose=False               # bez szczegółowych logów
)

# Przykład 3: Własne pozycje anten (w metrach od punktu referencyjnego)
custom_antenna_positions = [
    np.array([0.0, 0.0]),       # Antena 0: punkt odniesienia
    np.array([1.0, 0.0]),       # Antena 1: 1m na wschód
    np.array([0.5, 0.866])      # Antena 2: trójkąt równoboczny
]

result = triangulate_jammer_location(
    files,
    antenna_positions_meters=custom_antenna_positions,
    reference_lat=50.06143,
    reference_lon=19.93658
)

# Przykład 4: Tylko 2 anteny
result_2ant = triangulate_jammer_location(
    files[:2],  # tylko 2 pliki
    reference_lat=50.06143,
    reference_lon=19.93658
)

# Przykład 5: Integracja z istniejącym kodem
def detect_jammer_location(file_list, base_lat, base_lon):
    result = triangulate_jammer_location(file_list, base_lat, base_lon, verbose=False)
    
    if result['success']:
        return {
            'found': True,
            'lat': result['location_geographic']['lat'],
            'lon': result['location_geographic']['lon'],
            'distances': result['distances'],
            'method': f"{result['num_antennas']}-antenna triangulation"
        }
    else:
        return {
            'found': False,
            'error': result['message']
        }

# Użycie:
jammer_info = detect_jammer_location(['ant0.bin', 'ant1.bin'], 50.0, 19.0)
if jammer_info['found']:
    print(f"Jammer at: {jammer_info['lat']}, {jammer_info['lon']}")
"""
