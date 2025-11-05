import numpy as np
import sys
import os

def analyze_chunk_power(
    raw_uint8_chunk: np.ndarray, 
    power_threshold: float
) -> (bool, float):
    if raw_uint8_chunk.size % 2 != 0 or raw_uint8_chunk.size == 0:
        return False, 0.0

    iq_samples_f32 = (raw_uint8_chunk.astype(np.float32) - 127.5)
    
    iq_complex = iq_samples_f32[0::2] + 1j * iq_samples_f32[1::2]
    
    average_power = np.mean(np.abs(iq_complex)**2)
    
    is_jamming_now = average_power > power_threshold
    
    return is_jamming_now, average_power

def analyze_file_for_jamming(file_path: str, power_threshold: float) -> tuple:
    CHUNK_SIZE_BYTES = 131072
    
    current_jamming_state = False 
    total_samples_processed = 0
    jamming_start_sample = None
    jamming_end_sample = None
    
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
                    jamming_start_sample = timestamp_sample
                
                elif not is_jamming_now and was_jamming_previously:
                    jamming_end_sample = timestamp_sample

                current_jamming_state = is_jamming_now
                total_samples_processed += num_new_samples_in_chunk

        if current_jamming_state and jamming_start_sample is not None:
            jamming_end_sample = total_samples_processed
            
        return jamming_start_sample, jamming_end_sample
        
    except Exception as e:
        print(f"Błąd podczas analizy pliku: {e}")
        return None, None

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("BŁĄD: Niepoprawne użycie.")
        print("Sposób użycia: python checkIfJamming.py <nazwa_pliku.bin> <próg_mocy>")
        print("Przykład:       python checkIfJamming.py nagranie.iq 5000.0")
        sys.exit(1)

    SDR_FILE_PATH = sys.argv[1]
    
    try:
        CALIBRATED_POWER_THRESHOLD = float(sys.argv[2])
    except ValueError:
        print(f"BŁĄD: <próg_mocy> musi być liczbą (np. '5000.0'), a nie '{sys.argv[2]}'")
        sys.exit(1)

    if not os.path.exists(SDR_FILE_PATH):
        print(f"BŁĄD: Nie znaleziono pliku: {SDR_FILE_PATH}")
        sys.exit(1)

    print(f"--- Analiza jammingu w pliku {SDR_FILE_PATH} ---")
    print(f"Próg mocy: {CALIBRATED_POWER_THRESHOLD}")
    
    jamming_start, jamming_end = analyze_file_for_jamming(SDR_FILE_PATH, CALIBRATED_POWER_THRESHOLD)
    
    if jamming_start is not None and jamming_end is not None:
        print(f"WYNIK: jamming_start_sample={jamming_start}, jamming_end_sample={jamming_end}")
    elif jamming_start is not None:
        print(f"WYNIK: jamming_start_sample={jamming_start}, jamming_end_sample=EOF")
    else:
        print("WYNIK: jamming_start_sample=None, jamming_end_sample=None")
