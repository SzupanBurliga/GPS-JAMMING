import numpy as np
from scipy import signal
import math

# --- KONFIGURACJA ---
# TODO: Dostosować wartości dla dokładnośći

# 1. Ścieżki do plików I/Q
FILE_ANT0 = '17_10/capture1710_0_15m.bin'
FILE_ANT1 = '17_10/capture1710_1.bin'

# 2. Parametry odbiornika
SAMPLE_RATE = 2048000  # Częstotliwość próbkowania [Hz]
CENTER_FREQ = 1575420000  # Częstotliwość środkowa [Hz]

# 3. Położenie anten (w metrach, w kartezjańskim układzie współrzędnych)
ANT0_POS = np.array([0, 0])
ANT1_POS = np.array([0.5, 0]) # Przykład: 0.5 metra odległości, pomiary były przeprowadzane w ten sposób

# 4. Parametry synchronizacji programowej
NOISE_SAMPLE_SIZE = 200000
DETECTION_WINDOW_SIZE = 1000
DETECTION_THRESHOLD_FACTOR = 50.0

# 5. Rozmair wycinka korelacji TDOA
CORRELATION_SLICE_SIZE = 50000 

# 6. Stałe
SPEED_OF_LIGHT = 299792458  # Prędkość światła w m/s

def load_iq_data(filename):
    """Wczytuje dane I/Q z pliku binarnego (format rtl-sdr: uint8) i konwertuje je do liczb zespolonych."""
    raw_data = np.fromfile(filename, dtype=np.uint8)
    iq_data = (raw_data[0::2].astype(np.float32) - 127.5) + 1j * (raw_data[1::2].astype(np.float32) - 127.5)
    return iq_data

def find_interference_start(iq_data, noise_samples, window_size, threshold_factor):
    """Znajduje indeks próbki, gdzie moc sygnału gwałtownie wzrasta."""
    if len(iq_data) < noise_samples + window_size: return -1
    power = np.abs(iq_data)**2
    noise_power = np.mean(power[:noise_samples])
    if noise_power == 0: noise_power = 1e-9
    moving_avg_power = np.convolve(power, np.ones(window_size)/window_size, mode='valid')
    detection_threshold = noise_power * threshold_factor
    start_indices = np.where(moving_avg_power > detection_threshold)[0]
    if len(start_indices) > 0:
        return start_indices[0] + window_size // 2
    else:
        return -1

if __name__ == "__main__":
    print("Wczytywanie danych I/Q...")
    try:
        signal0_full = load_iq_data(FILE_ANT0)
        signal1_full = load_iq_data(FILE_ANT1)
    except FileNotFoundError as e:
        print(f"Błąd: Nie znaleziono pliku! {e}")
        exit()

    # --- KROK 1: SYNCHRONIZACJA PROGRAMOWA ---
    print("\nRozpoczynanie synchronizacji programowej...")
    start0 = find_interference_start(signal0_full, NOISE_SAMPLE_SIZE, DETECTION_WINDOW_SIZE, DETECTION_THRESHOLD_FACTOR)
    start1 = find_interference_start(signal1_full, NOISE_SAMPLE_SIZE, DETECTION_WINDOW_SIZE, DETECTION_THRESHOLD_FACTOR)

    if start0 == -1 or start1 == -1:
        print("BŁĄD KRYTYCZNY: Nie udało się wykryć początku interferencji.")
        exit()
        
    print(f"Wykryto początek interferencji w pliku 0 na próbce: {start0}")
    print(f"Wykryto początek interferencji w pliku 1 na próbce: {start1}")
    
    # --- KROK 2: OBLICZENIE TDOA NA KRÓTKIM WYCINKU SYGNAŁU ---
    # Sprawdzenie, czy mamy wystarczająco dużo danych na wycinek
    if len(signal0_full) < start0 + CORRELATION_SLICE_SIZE or \
       len(signal1_full) < start1 + CORRELATION_SLICE_SIZE:
        print("BŁĄD: Niewystarczająca ilość danych po wykryciu interferencji do analizy.")
        exit()

    # Stwórz wyrównane wycinki
    signal0_slice = signal0_full[start0 : start0 + CORRELATION_SLICE_SIZE]
    signal1_slice = signal1_full[start1 : start1 + CORRELATION_SLICE_SIZE]
    
    print(f"\nSygnały wyrównane. Przetwarzanie wycinka {CORRELATION_SLICE_SIZE} próbek.")

    print("Obliczanie korelacji wzajemnej na wycinkach sygnału...")
    correlation = signal.correlate(signal1_slice, signal0_slice, mode='full')
    abs_correlation = np.abs(correlation)

    lag_samples = np.argmax(abs_correlation) - (len(signal0_slice) - 1)
    print(f"Znaleziono maksymalną korelację przy przesunięciu {lag_samples} próbek.")

    tdoa = lag_samples / SAMPLE_RATE
    print(f"Różnica czasu dotarcia (TDOA): {tdoa * 1e9:.2f} ns")

    path_difference = tdoa * SPEED_OF_LIGHT
    print(f"Różnica w odległości do anten: {path_difference:.4f} m")

    # --- KROK 3: OBLICZENIE KIERUNKU ---
    antenna_distance = np.linalg.norm(ANT1_POS - ANT0_POS)
    
    if antenna_distance == 0:
        print("Błąd: Odległość między antenami wynosi 0.")
        exit()

    cos_theta_arg = path_difference / antenna_distance
    
    if abs(cos_theta_arg) > 1:
        print("\nOSTRZEŻENIE: Obliczona różnica ścieżek jest większa niż odległość między antenami.")
        print("Możliwe przyczyny: błąd w konfiguracji odległości anten lub bardzo silne odbicia (multipath).")
        exit()

    theta = math.acos(cos_theta_arg)
    
    baseline_angle_rad = math.atan2(ANT1_POS[1] - ANT0_POS[1], ANT0_POS[0] - ANT0_POS[0])
    azimuth1_rad = baseline_angle_rad + theta
    azimuth2_rad = baseline_angle_rad - theta
    
    azimuth1_deg = (math.degrees(azimuth1_rad)) % 360
    azimuth2_deg = (math.degrees(azimuth2_rad)) % 360

    print("\n--- WYNIKI ---")
    print(f"Odległość między antenami: {antenna_distance:.2f} m")
    print(f"Kąt nadejścia fali interferencyjnej (względem osi anten): {math.degrees(theta):.2f} stopni")
    print(f"Potencjalne kierunki do źródła interferencji (azymuty):")
    print(f"  Kierunek 1: {azimuth1_deg:.2f} stopni")

    print(f"  Kierunek 2: {azimuth2_deg:.2f} stopni")
