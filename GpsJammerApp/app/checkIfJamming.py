"""
Samodzielny skrypt do analizy pliku .bin (nagranie rtl_sdr)
pod kątem wykrywania jammingu na podstawie progu mocy.

Sposób użycia:
python analyze_sdr_file.py <nazwa_pliku.bin> <próg_mocy>

Przykład:
python analyze_sdr_file.py moje_nagranie.iq 5000.0
"""

import numpy as np
import time
import sys
import os

def check_jamming_stateful(
    raw_uint8_chunk: np.ndarray, 
    power_threshold: float, 
    was_jamming_previously: bool
) -> bool:
    """
    Analizuje fragment surowych próbek uint8 (I/Q) i drukuje zmiany stanu 
    jammingu.

    Args:
        raw_uint8_chunk (np.ndarray): Fragment danych prosto z rtl_sdr 
                                      w formacie numpy uint8.
        power_threshold (float): Ustalony próg mocy do kalibracji.
        was_jamming_previously (bool): Stan z poprzedniego wywołania funkcji.

    Returns:
        bool: Aktualny stan jammingu (True jeśli jest, False jeśli nie ma),
              który należy podać jako 'was_jamming_previously' 
              w następnym wywołaniu.
    """
    if raw_uint8_chunk.size % 2 != 0:
        print("Błąd: Nieparzysta liczba próbek, pomijam fragment.", flush=True)
        return was_jamming_previously

    if raw_uint8_chunk.size == 0:
        return was_jamming_previously

    iq_samples_f32 = (raw_uint8_chunk.astype(np.float32) - 127.5)
    iq_complex = iq_samples_f32[0::2] + 1j * iq_samples_f32[1::2]
    average_power = np.mean(np.abs(iq_complex)**2)
    #print(f"(Debug: Średnia moc = {average_power:.2f})")
    is_jamming_now = average_power > power_threshold

    if is_jamming_now and not was_jamming_previously:
        print(f"[{time.strftime('%H:%M:%S')}] WYKRYTO JAMMING (Moc: {average_power:.2f})", flush=True)
    elif is_jamming_now and was_jamming_previously:
        print(f"[{time.strftime('%H:%M:%S')}] jamming (Moc: {average_power:.2f})", flush=True)
    elif not is_jamming_now and was_jamming_previously:
        print(f"[{time.strftime('%H:%M:%S')}] KONIEC JAMMINGU (Moc: {average_power:.2f})", flush=True)

    return is_jamming_now

if __name__ == "__main__":
    CHUNK_SIZE_BYTES = 131072

    if len(sys.argv) != 3:
        print("BŁĄD: Niepoprawne użycie.")
        print("Sposób użycia: python analyze_sdr_file.py <nazwa_pliku.bin> <próg_mocy>")
        print("Przykład:       python analyze_sdr_file.py nagranie.iq 5000.0")
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

    print(f"--- Start Analizatora Pliku ---")
    print(f"Plik:       {SDR_FILE_PATH}")
    print(f"Próg mocy:  {CALIBRATED_POWER_THRESHOLD}")
    print(f"Rozmiar fragmentu: {CHUNK_SIZE_BYTES} bajtów")
    print("---------------------------------")
    
    current_jamming_state = False 

    try:
        with open(SDR_FILE_PATH, 'rb') as f:
            while True:
                raw_bytes = f.read(CHUNK_SIZE_BYTES)
                
                if not raw_bytes:
                    print("\n--- Koniec pliku ---")
                    break
                
                raw_chunk = np.frombuffer(raw_bytes, dtype=np.uint8)
                
                current_jamming_state = check_jamming_stateful(
                    raw_chunk,
                    CALIBRATED_POWER_THRESHOLD,
                    current_jamming_state
                )

    except KeyboardInterrupt:
        print("\nPrzerwano analizę (Ctrl+C).")
    except Exception as e:
        print(f"\nWystąpił nieoczekiwany błąd: {e}")
    finally:
        if current_jamming_state:
            print(f"[{time.strftime('%H:%M:%S')}] KONIEC JAMMINGU (Koniec przetwarzania)")
        
        print("--- Analizator zakończył pracę ---")
