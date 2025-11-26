import numpy as np
import os

# ==========================================
# KONFIGURACJA
# ==========================================
FILE_LEGIT = "test2.bin"       
FILE_SPOOF = "test.bin"     
FILE_OUTPUT = "fixed_power_attack.bin"

SAMPLE_RATE = 2048000          
ATTACK_START_TIME = 50.0       
RAMP_DURATION = 20.0           

# Ustawiamy głośność na 25%, żeby nie krzyczało
GLOBAL_SCALING = 0.25 

def mix_uint8_fix():
    print(f"--- GENEROWANIE (FIX MOCY - OFFSET 128) ---")
    
    if not os.path.exists(FILE_LEGIT) or not os.path.exists(FILE_SPOOF):
        print("BŁĄD: Brak plików!")
        return

    # 1. WCZYTUJEMY JAKO UINT8 (Tak jak kazałeś)
    # Wczytujemy surowe bajty.
    print("Wczytuję jako uint8...")
    raw_legit = np.fromfile(FILE_LEGIT, dtype=np.uint8)
    raw_spoof = np.fromfile(FILE_SPOOF, dtype=np.uint8)

    min_len = min(len(raw_legit), len(raw_spoof))
    # Wyrównanie do parzystej (I+Q)
    if min_len % 2 != 0: min_len -= 1
    
    raw_legit = raw_legit[:min_len]
    raw_spoof = raw_spoof[:min_len]
    
    # 2. INTERPRETACJA BITÓW (MAGIA)
    # gps-sdr-sim generuje bajty, gdzie 0 to cisza, a 255 to -1 (U2).
    # Ale wczytaliśmy je jako uint8, więc Python myśli, że 255 to duża liczba.
    # Używamy .view(), żeby poprawnie odczytać te same bity jako liczby ze znakiem.
    # To nie zmienia pliku, tylko matematykę.
    sig_legit = raw_legit.view(np.int8).astype(np.float32)
    sig_spoof = raw_spoof.view(np.int8).astype(np.float32)

    # 3. MASKA CZASOWA (RAMP-UP)
    idx_start = int(ATTACK_START_TIME * SAMPLE_RATE * 2)
    idx_end = int((ATTACK_START_TIME + RAMP_DURATION) * SAMPLE_RATE * 2)
    
    spoofer_envelope = np.zeros(min_len, dtype=np.float32)
    
    if idx_end < min_len:
        ramp_len = idx_end - idx_start
        spoofer_envelope[idx_start:idx_end] = np.linspace(0.0, 1.0, ramp_len)
        spoofer_envelope[idx_end:] = 1.0
    else:
        rem = min_len - idx_start
        if rem > 0: spoofer_envelope[idx_start:] = np.linspace(0.0, 1.0, rem)

    print("Mieszanie sygnałów...")

    # 4. MIESZANIE + SZUM + SCALING
    # Dodajemy szum, żeby nie było sterylnie
    noise = np.random.normal(0, 1.0, size=len(sig_legit))
    
    mixed = (sig_legit + (sig_spoof * spoofer_envelope) + noise) * GLOBAL_SCALING

    # 5. PRZESUNIĘCIE ZERA (OFFSET +128) - TO NAPRAWIA DETEKCJĘ
    # Twój detektor oczekuje, że cisza to 128.
    # My mamy ciszę w 0.
    # Więc dodajemy 128.
    print("Dodaję Offset +128 (Format RTL-SDR)...")
    mixed = mixed + 128.0

    # 6. ZAPIS JAKO UINT8
    # Zabezpieczenie przed przekręceniem licznika
    mixed = np.clip(mixed, 0, 255)
    
    mixed_uint8 = mixed.astype(np.uint8)
    mixed_uint8.tofile(FILE_OUTPUT)
    
    print(f"\nSUKCES! Zapisano: {FILE_OUTPUT}")
    print("Teraz detektor powinien widzieć ciszę jako 128 (czyli moc 0).")

if __name__ == "__main__":
    mix_uint8_fix()