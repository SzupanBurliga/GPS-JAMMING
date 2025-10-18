import numpy as np
import math

# --- 1KONFIGURACJA ---

# Ścieżki do plików I/Q
FILE_ANT0 = '17_10/capture1710_0_15m.bin'
FILE_ANT1 = '17_10/capture1710_1.bin'

# Położenie anten w metrach (kartezjański układ 2D)
ANT0_POS = np.array([0.0, 0.0])
ANT1_POS = np.array([0.5, 0.0])

# --- PARAMETRY KALIBRACYJNE ---
CALIBRATED_TX_POWER = 40.0
CALIBRATED_PATH_LOSS_EXPONENT = 3.0

# --- Inne parametry sygnału ---
SIGNAL_FREQUENCY_MHZ = 1575.42
SIGNAL_THRESHOLD = 0.1

# --- FUNKCJE ---

def read_iq_data(filename):
    """Wczytuje i przetwarza dane IQ uint8 z pliku."""
    try:
        raw_data = np.fromfile(filename, dtype=np.uint8)
        float_data = (raw_data.astype(np.float32) - 127.5) / 127.5
        complex_data = float_data[0::2] + 1j * float_data[1::2]
        return complex_data
    except FileNotFoundError:
        print(f"BŁĄD: Plik '{filename}' nie został znaleziony.")
        return None

def find_change_point(amplitude_data, threshold):
    """Znajduje pierwszy indeks, w którym amplituda przekracza próg."""
    change_indices = np.where(amplitude_data > threshold)[0]
    return change_indices[0] if len(change_indices) > 0 else None

def calculate_distance_from_file(iq_filename):
    """Główna funkcja analizująca jeden plik i zwracająca oszacowaną odległość."""
    print(f"--- Analizowanie pliku '{iq_filename}' ---")
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

def find_circle_intersections(p0, r0, p1, r1):
    """Oblicza punkty przecięcia dwóch okręgów."""
    d = np.linalg.norm(p1 - p0)
    if d > r0 + r1 or d < abs(r0 - r1) or d == 0:
        return None # Warunki braku przecięcia
    
    # Uniknięcie błędu math domain error dla bardzo małych h
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

def find_best_estimate_no_intersection(p0, r0, p1, r1):
    """
    Estymuje najbardziej prawdopodobną lokalizację, gdy okręgi się nie przecinają.
    Znajduje punkt na linii łączącej środki okręgów, leżący w połowie drogi
    między najbliższymi punktami brzegowymi tych okręgów.
    """
    d = np.linalg.norm(p1 - p0)
    if d == 0: return None # Unikaj dzielenia przez zero
    unit_vector = (p1 - p0) / d

    # Punkty brzegowe okręgu 0 na linii łączącej środki
    c0_p1 = p0 + r0 * unit_vector
    c0_p2 = p0 - r0 * unit_vector

    # Punkty brzegowe okręgu 1 na linii łączącej środki
    c1_p1 = p1 + r1 * unit_vector
    c1_p2 = p1 - r1 * unit_vector
    
    # Słownik par punktów i odległości między nimi
    distances = {
        np.linalg.norm(c0_p1 - c1_p2): (c0_p1, c1_p2),
        np.linalg.norm(c0_p2 - c1_p1): (c0_p2, c1_p1),
        np.linalg.norm(c0_p1 - c1_p1): (c0_p1, c1_p1),
        np.linalg.norm(c0_p2 - c1_p2): (c0_p2, c1_p2)
    }
    
    min_dist = min(distances.keys())
    closest_pair = distances[min_dist]
    
    # Najlepszym oszacowaniem jest środek najkrótszego odcinka
    best_estimate = (closest_pair[0] + closest_pair[1]) / 2
    return best_estimate

if __name__ == "__main__":
    print("Rozpoczynanie lokalizacji na podstawie mocy sygnału (RSSI).\n")
    print("WAŻNE: Upewnij się, że parametry kalibracyjne są poprawnie ustawione!\n")

    dist0 = calculate_distance_from_file(FILE_ANT0)
    dist1 = calculate_distance_from_file(FILE_ANT1)

    if dist0 is None or dist1 is None:
        print("Nie udało się obliczyć jednej z odległości. Przerywanie pracy.")
        exit()

    print("--- Obliczanie lokalizacji ---")
    print(f"Szukanie przecięcia okręgu o środku w {ANT0_POS} i promieniu {dist0:.2f} m")
    print(f"oraz okręgu o środku w {ANT1_POS} i promieniu {dist1:.2f} m\n")
    
    intersections = find_circle_intersections(ANT0_POS, dist0, ANT1_POS, dist1)

    if intersections:
        loc1, loc2 = intersections
        print(">>> Znaleziono dwie możliwe lokalizacje nadajnika (idealne przecięcie):")
        print(f"    Lokalizacja 1: x = {loc1[0]:.2f} m, y = {loc1[1]:.2f} m")
        print(f"    Lokalizacja 2: x = {loc2[0]:.2f} m, y = {loc2[1]:.2f} m")
    else:
        print("OSTRZEŻENIE: Okręgi nie przecinają się. Błędy pomiarowe są zbyt duże dla idealnego rozwiązania.")
        print("Uruchamianie estymacji w celu znalezienia najbardziej prawdopodobnego punktu...\n")
        
        best_guess = find_best_estimate_no_intersection(ANT0_POS, dist0, ANT1_POS, dist1)
        
        if best_guess is not None:
             print(">>> Znaleziono najbardziej prawdopodobną lokalizację (estymacja):")
             print(f"    Lokalizacja: x = {best_guess[0]:.2f} m, y = {best_guess[1]:.2f} m")
        else:
            print("Nie udało się znaleźć oszacowania.")