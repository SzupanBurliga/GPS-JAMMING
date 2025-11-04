#!/usr/bin/env python3

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

if __name__ == "__main__":
    CHUNK_SIZE_BYTES = 131072 

    if len(sys.argv) != 3:
        print("BŁĄD: Niepoprawne użycie.")
        print("Sposób użycia: python analyze_sdr_file_by_sample.py <nazwa_pliku.bin> <próg_mocy>")
        print("Przykład:       python analyze_sdr_file_by_sample.py nagranie.iq 5000.0")
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

    print(f"--- Start Analizatora Pliku (wg numeru próbki) ---")
    print(f"Plik:       {SDR_FILE_PATH}")
    print(f"Próg mocy:  {CALIBRATED_POWER_THRESHOLD}")
    print(f"Rozmiar fragmentu: {CHUNK_SIZE_BYTES} bajtów ({CHUNK_SIZE_BYTES // 2} próbek I/Q)")
    print("------------------------------------------------------")
    
    current_jamming_state = False 
    
    total_samples_processed = 0 
    max_power_detected = 0.0

    try:
        with open(SDR_FILE_PATH, 'rb') as f:
            while True:
                raw_bytes = f.read(CHUNK_SIZE_BYTES)
                
                if not raw_bytes:
                    print("\n--- Koniec pliku ---")
                    break
                
                raw_chunk_uint8 = np.frombuffer(raw_bytes, dtype=np.uint8)
                
                num_new_samples_in_chunk = raw_chunk_uint8.size // 2
                
                if num_new_samples_in_chunk == 0:
                    continue 

                is_jamming_now, avg_power = analyze_chunk_power(
                    raw_chunk_uint8,
                    CALIBRATED_POWER_THRESHOLD
                )
                
                if avg_power > max_power_detected:
                    max_power_detected = avg_power
                
                was_jamming_previously = current_jamming_state
                
                timestamp_sample = total_samples_processed

                if is_jamming_now and not was_jamming_previously:
                    print(f"[Sample {timestamp_sample}] WYKRYTO JAMMING (Moc: {avg_power:.2f})", flush=True)
                
                elif is_jamming_now and was_jamming_previously:
                    print(f"[Sample {timestamp_sample}] ...Jamming trwa (Moc: {avg_power:.2f})", flush=True)

                elif not is_jamming_now and was_jamming_previously:
                    print(f"[Sample {timestamp_sample}] KONIEC JAMMINGU (Moc: {avg_power:.2f})", flush=True)

                current_jamming_state = is_jamming_now
                
                total_samples_processed += num_new_samples_in_chunk

    except KeyboardInterrupt:
        print("\nPrzerwano analizę (Ctrl+C).")
    except Exception as e:
        print(f"\nWystąpił nieoczekiwany błąd: {e}")
    finally:
        if current_jamming_state:
            print(f"[Sample {total_samples_processed}] KONIEC JAMMINGU (Koniec pliku)")
        
        print(f"Maksymalna średnia moc fragmentu: {max_power_detected:.2f}")
        
        print(f"--- Analizator zakończył pracę (przetworzono {total_samples_processed} próbek I/Q) ---")
