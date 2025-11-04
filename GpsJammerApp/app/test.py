import numpy as np
import pygpssdr.acquisition as acq
import pygpssdr.tracking as trk
import pygpssdr.navigation as nav
import pygpssdr.decode as dec
import time

# --- Konfiguracja, którą MUSISZ znać z nagrania ---
FILE_PATH = '/home/szymon/Downloads/jammerAfterMinute.bin'
# Kluczowe: częstotliwość próbkowania (np. z rtl_sdr)
SAMPLING_RATE_HZ = 2_048_000  # 2.048 Msps
# Częstotliwość pośrednia (jeśli jest, 0 dla pasma podstawowego)
INTERMEDIATE_FREQ_HZ = 0 
# Czas trwania pliku (dla testów, w sekundach)
DURATION_SEC = 200.0 
# Format pliku
FILE_FORMAT = np.uint8 

# --- Krok 1: Wczytanie i konwersja pliku uint8 ---

def load_and_convert_signal(filepath, fs, duration, file_format):
    """
    Wczytuje surowe próbki uint8 i konwertuje je do zespolonych 
    float32, centrując je wokół zera.
    """
    # Oblicz liczbę próbek (I i Q to osobne próbki)
    num_samples = int(fs * duration * 2) 
    
    print(f"Wczytywanie {num_samples} bajtów ({duration}s) z {filepath}...")
    try:
        raw_bytes = np.fromfile(filepath, dtype=file_format, count=num_samples)
    except Exception as e:
        print(f"Błąd wczytywania pliku: {e}")
        return None

    if raw_bytes.size == 0:
        print("Błąd: Plik jest pusty lub nie można go wczytać.")
        return None

    # Konwersja [0, 255] -> [-127.5, 127.5]
    centered_floats = raw_bytes.astype(np.float32) - 127.5
    
    # Stworzenie liczb zespolonych (I + j*Q)
    # Normalizacja do zakresu [-1.0, 1.0] jest dobrą praktyką
    iq_signal = (centered_floats[0::2] + 1j * centered_floats[1::2]) / 128.0
    
    return iq_signal

# --- Krok 2: Główna logika odbiornika ---

def main():
    print("--- Start Odbiornika GPS w Pythonie ---")
    
    # 1. Wczytaj sygnał
    signal = load_and_convert_signal(FILE_PATH, SAMPLING_RATE_HZ, 
                                     DURATION_SEC, FILE_FORMAT)
    if signal is None:
        return

    print(f"Sygnał wczytany. Liczba próbek zespolonych: {signal.size}")
    
    # 2. Akwizycja - szukanie satelitów
    print("Rozpoczynam akwizycję (szukanie satelitów)...")
    
    # Szukamy satelity o PRN 5 (tylko jako przykład)
    prn_to_find = 5 
    
    # 'pcps' to jedna z metod akwizycji w bibliotece
    # To jest BARDZO kosztowne obliczeniowo
    try:
        acq_result = acq.pcps(signal, 
                              fs=SAMPLING_RATE_HZ, 
                              fif=INTERMEDIATE_FREQ_HZ, 
                              prn=prn_to_find)
        
        # acq_result[0] > 0 oznacza, że znaleziono
        if acq_result[0] > 0:
            code_offset = acq_result[1]
            doppler_freq = acq_result[2]
            print(f"Sukces! Znaleziono PRN {prn_to_find}.")
            print(f"  Przesunięcie kodu: {code_offset} próbek")
            print(f"  Częstotliwość Dopplera: {doppler_freq:.2f} Hz")
        else:
            print(f"Nie znaleziono PRN {prn_to_find}. Spróbuj dłuższego nagrania.")
            return

    except Exception as e:
        print(f"Błąd podczas akwizycji: {e}")
        print("Upewnij się, że masz zainstalowane wszystkie zależności, np. `numba`.")
        return

    # 3. Śledzenie (Tracking)
    # Jeśli akwizycja się udała, przechodzimy do śledzenia
    print(f"\nRozpoczynam śledzenie PRN {prn_to_find}...")
    
    # To jest jeszcze bardziej złożone. Ta funkcja uruchamia pętle 
    # śledzące (DLL/PLL) na całym sygnale.
    # Wymaga to znacznie dłuższego sygnału niż 2 sekundy!
    # (Poniższy kod jest koncepcyjny, wymaga dłuższego pliku)
    
    # track_result = trk.track(signal, 
    #                         fs=SAMPLING_RATE_HZ, 
    #                         fif=INTERMEDIATE_FREQ_HZ, 
    #                         prn=prn_to_find, 
    #                         doppler=doppler_freq, 
    #                         code_phase=code_offset)
    
    # Wynikiem śledzenia są m.in. zdekodowane bity (50 bps)
    # extracted_bits = track_result['bits'] 

    # 4. Dekodowanie wiadomości nawigacyjnej
    print("\nKrok 4: Dekodowanie (koncepcyjne)")
    print("Jeśli śledzenie się powiedzie, funkcja 'track' zwróci bity.")
    
    # Załóżmy, że mamy bity: extracted_bits = [1, 0, 1, 1, 0, ...]
    
    # Następnie musisz znaleźć preambułę, aby zsynchronizować ramki
    # subframe_data = dec.find_preamble(extracted_bits, ...)
    
    # A na końcu, gdy masz zdekodowane 5 pod-ramek, możesz 
    # wyciągnąć z nich czas.
    # (To wymaga zebrania przynajmniej 30 sekund danych)
    
    # Przykład (pseudo-kod):
    # nav_data = nav.NavData(subframe_data)
    # tow = nav_data.subframe1.TOW
    # week_num = nav_data.subframe1.WN
    # utc_time = convert_gps_to_utc(week_num, tow)
    
    print(f"\n--- Zakończono ---")
    print("Prawdziwe dekodowanie UTC wymagałoby znacznie dłuższego")
    print("nagrania (min. 30 sekund) i pełnej implementacji kroków 3 i 4.")


if __name__ == "__main__":
    # Ustaw wyższy czas trwania, jeśli masz długi plik
    # DURATION_SEC = 30.0 
    main()