import numpy as np
import sys
import os

CHUNK_SIZE_BYTES = 131072

def analyze_chunk_power(
    raw_uint8_chunk: np.ndarray, 
    power_threshold: float
) -> tuple[bool, float]:
    
    if raw_uint8_chunk.size % 2 != 0 or raw_uint8_chunk.size == 0:
        return False, 0.0

    iq_samples_f32 = (raw_uint8_chunk.astype(np.float32) - 127.5)
    iq_complex = iq_samples_f32[0::2] + 1j * iq_samples_f32[1::2]
    average_power = np.mean(np.abs(iq_complex)**2)
    is_jamming_now = average_power > power_threshold
    
    return is_jamming_now, average_power

def analyze_file_for_jamming(file_path: str, power_threshold: float) -> list:
    current_jamming_state = False 
    total_samples_processed = 0
    jamming_events = [] 
    current_jamming_start = None
    
    try:
        with open(file_path, 'rb') as f:
            while True:
                raw_bytes = f.read(CHUNK_SIZE_BYTES)
                if not raw_bytes:
                    break
                
                raw_chunk_uint8 = np.frombuffer(raw_bytes, dtype=np.uint8)
                num_new_samples_in_chunk = raw_chunk_uint8.size // 2
                
                if num_new_samples_in_chunk == 0:
                    continue 

                is_jamming_now, avg_power = analyze_chunk_power(
                    raw_chunk_uint8,
                    power_threshold 
                )
                
                was_jamming_previously = current_jamming_state
                timestamp_sample = total_samples_processed

                if is_jamming_now and not was_jamming_previously:
                    current_jamming_start = timestamp_sample
                
                elif not is_jamming_now and was_jamming_previously:
                    if current_jamming_start is not None:
                        jamming_events.append((current_jamming_start, timestamp_sample))
                        current_jamming_start = None

                current_jamming_state = is_jamming_now
                total_samples_processed += num_new_samples_in_chunk

        if current_jamming_state and current_jamming_start is not None:
            jamming_events.append((current_jamming_start, total_samples_processed))
            
        return jamming_events
        
    except Exception as e:
        print(f"Błąd podczas analizy pliku: {e}")
        return []

def calibrate_file(file_path: str):
    power_values = []
    
    try:
        with open(file_path, 'rb') as f:
            while True:
                raw_bytes = f.read(CHUNK_SIZE_BYTES)
                if not raw_bytes:
                    break
                
                raw_chunk_uint8 = np.frombuffer(raw_bytes, dtype=np.uint8)
                _, avg_power = analyze_chunk_power(raw_chunk_uint8, 0.0)
                
                if avg_power == 0.0 and raw_chunk_uint8.size == 0:
                    continue
                    
                power_values.append(avg_power)

        print("--- Kalibracja zakończona ---")
        
        if not power_values:
            print("Plik jest pusty lub nie zawiera poprawnych danych.")
            return

        all_powers_np = np.array(power_values)
        noise_floor_median = np.median(all_powers_np)
        suggested_threshold = noise_floor_median * 4.8
        
        print("\n--- Statystyki mocy (skala cyfrowa I²+Q²) ---")
        print(f"Typowy poziom szumu (Mediana): {noise_floor_median:.2f}")
        print(f"Moc szczytowa (max):         {np.max(all_powers_np):.2f}")
        print(f"Moc minimalna (min):         {np.min(all_powers_np):.2f}")
        
        print(f"\nSugerowany <próg_mocy> (Mediana * 4.8): {suggested_threshold:.2f}")
        print(f"Użyj: python {os.path.basename(__file__)} {file_path} {suggested_threshold:.2f}")

    except Exception as e:
        print(f"Błąd podczas kalibracji pliku: {e}")

def print_usage_and_exit():
    script_name = os.path.basename(__file__)
    print("BŁĄD: Niepoprawne użycie.")
    print("\nSposób użycia (Tryb Analizy):")
    print(f"  python {script_name} <nazwa_pliku.bin> <próg_mocy>")
    print(f"Przykład: python {script_name} nagranie.iq 120.0")
    
    print("\nSposób użycia (Tryb Kalibracji):")
    print(f"  python {script_name} <nazwa_pliku.bin> --kalibruj")
    print(f"Przykład: python {script_name} nagranie.iq --kalibruj")
    sys.exit(1)

if __name__ == "__main__":
    
    if len(sys.argv) != 3:
        print_usage_and_exit()

    SDR_FILE_PATH = sys.argv[1]
    SECOND_ARG = sys.argv[2]
    
    MODE = None
    CALIBRATED_POWER_THRESHOLD = None
    
    if SECOND_ARG == '--kalibruj':
        MODE = 'calibrate'
    else:
        MODE = 'analyze'
        try:
            CALIBRATED_POWER_THRESHOLD = float(SECOND_ARG)
        except ValueError:
            print(f"BŁĄD: <próg_mocy> musi być liczbą (np. '120.0'), a nie '{SECOND_ARG}'")
            print_usage_and_exit()

    if not os.path.exists(SDR_FILE_PATH):
        print(f"BŁĄD: Nie znaleziono pliku: {SDR_FILE_PATH}")
        sys.exit(1)
    
    if MODE == 'calibrate':
        print(f"--- Tryb kalibracji: {SDR_FILE_PATH} ---")
        print("Proszę czekać, trwa analiza pliku...")
        calibrate_file(SDR_FILE_PATH)
        
    elif MODE == 'analyze':
        jamming_events = analyze_file_for_jamming(
            SDR_FILE_PATH, 
            CALIBRATED_POWER_THRESHOLD
        )
        
        if not jamming_events:
            print("WYNIK: Nie wykryto żadnego jammingu")
            print("jamming_events=[]")
        else:
            print(f"WYNIK: Wykryto {len(jamming_events)} okres(ów) jammingu:")
            for i, (start, end) in enumerate(jamming_events, 1):
                print(f"  Zdarzenie {i}: próbki {start} - {end} (długość: {end - start} próbek)")
            print(f"\njamming_events={jamming_events}")