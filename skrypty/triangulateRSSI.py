import numpy as np
import math

#   Obowiązkowe Antena 0 i 1  
FILE_ANT0 = '17_10/capture1710_0_15m.bin'
FILE_ANT1 = '17_10/capture1710_1.bin'
ANT0_POS = np.array([0.0, 0.0])
ANT1_POS = np.array([0.5, 0.0])

#   Opcjonalne Antena 2 
# jeżeli nie używana, pozostawić None
FILE_ANT2 = '17_10/capture1710_1.bin'#None 
ANT2_POS = np.array([0.0, 0.5])#None  

#PARAMETRY KALIBRACYJNE  
CALIBRATED_TX_POWER = 40.0
CALIBRATED_PATH_LOSS_EXPONENT = 3.0

#PARAMETRY SYGNAŁU 
SIGNAL_FREQUENCY_MHZ = 1575.42
SIGNAL_THRESHOLD = 0.1

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

#Obliczanie odległości metodą RSSI
def calculate_distance_from_file(iq_filename):
    print(f"  Analizowanie pliku '{iq_filename}'  ")
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

#   MAIN

if __name__ == "__main__":
    print("Rozpoczynanie lokalizacji na podstawie mocy sygnału (RSSI).\n")
    print("WAŻNE: Upewnij się, że parametry kalibracyjne i pozycje anten są poprawnie ustawione!\n")

    # Wczytywanie danych z obowiązkowych anten
    dist0 = calculate_distance_from_file(FILE_ANT0)
    dist1 = calculate_distance_from_file(FILE_ANT1)

    # Sprawdzenie, czy tryb 2-antenowy czy 3-antenowy
    USE_THREE_ANTENNAS = FILE_ANT2 is not None and ANT2_POS is not None

    if USE_THREE_ANTENNAS:
        #   LOGIKA DLA 3 ANTEN  
        print("Wykryto konfigurację dla 3 anten\n")
        dist2 = calculate_distance_from_file(FILE_ANT2)
        
        if dist0 is None or dist1 is None or dist2 is None:
            print("Nie udało się obliczyć jednej lub więcej odległości. Przerywanie pracy.")
            exit()
            
        print("  Obliczanie lokalizacji dla 3 anten  ")
        print(f"Dane wejściowe:")
        print(f"  Antena 0: pos={ANT0_POS}, promień={dist0:.2f} m")
        print(f"  Antena 1: pos={ANT1_POS}, promień={dist1:.2f} m")
        print(f"  Antena 2: pos={ANT2_POS}, promień={dist2:.2f} m\n")
        
        location = trilaterate(ANT0_POS, dist0, ANT1_POS, dist1, ANT2_POS, dist2)
        
        if location is not None:
            print(">>> Znaleziono najbardziej prawdopodobną lokalizację nadajnika:")
            print(f"    Lokalizacja: x = {location[0]:.2f} m, y = {location[1]:.2f} m")
        else:
            print("Nie udało się obliczyć lokalizacji. Sprawdź pozycje anten.")

    else:
        #   LOGIKA DLA 2 ANTEN  
        print("Nie wykryto konfiguracji dla 3. anteny. Uruchamianie obliczeń dla 2 anten\n")
        
        if dist0 is None or dist1 is None:
            print("Nie udało się obliczyć jednej z odległości. Przerywanie pracy.")
            exit()
        
        intersections = find_circle_intersections(ANT0_POS, dist0, ANT1_POS, dist1)
        
        if intersections:
            loc1, loc2 = intersections
            print(">>> Znaleziono dwie możliwe lokalizacje nadajnika (idealne przecięcie):")
            print(f"    Lokalizacja 1: x = {loc1[0]:.2f} m, y = {loc1[1]:.2f} m")
            print(f"    Lokalizacja 2: x = {loc2[0]:.2f} m, y = {loc2[1]:.2f} m")
        else:
            print("Okręgi nie przecinają się. Błędy pomiarowe są zbyt duże dla idealnego rozwiązania.")
            print("Uruchamianie estymacji w celu znalezienia najbardziej prawdopodobnego punktu\n")
            
            best_guess = find_best_estimate_no_intersection(ANT0_POS, dist0, ANT1_POS, dist1)
            
            if best_guess is not None:
                 print(">>> Znaleziono najbardziej prawdopodobną lokalizację (estymacja):")
                 print(f"    Lokalizacja: x = {best_guess[0]:.2f} m, y = {best_guess[1]:.2f} m")
            else:
                print("Nie udało się znaleźć oszacowania.")
