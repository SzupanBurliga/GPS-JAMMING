import json
import re
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
from scipy.signal import savgol_filter

# ============================================================================
# ⚙️ KONFIGURACJA
TARGET_FILE = 'capture_nowy_test1.txt' 
# ============================================================================

# Stałe GPS
C_LIGHT = 299792458.0
F_L1 = 1575.42e6
LAMBDA_L1 = C_LIGHT / F_L1

def parse_file_raw(filepath):
    data_points = []
    if not os.path.exists(filepath):
        print(f"❌ Błąd: Nie znaleziono pliku {filepath}")
        return pd.DataFrame()

    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    blocks = re.split(r'\n={5,}\n', content)
    print(f"🔄 Wczytuję dane...")

    for block in blocks:
        match = re.search(r'(\{.*\})', block, re.DOTALL)
        if not match: continue
        try:
            data = json.loads(match.group(1))
            elapsed = data.get('elapsed_time')
            observations = data.get('observations', [])
            if elapsed is None: continue

            for obs in observations:
                prn = obs.get('prn')
                raw_val = obs.get('doppler') # To jest pseudorange w Twoim pliku
                snr = obs.get('snr', 0)

                if prn is not None and raw_val is not None:
                    data_points.append({
                        'time': float(elapsed),
                        'prn': int(prn),
                        'pseudorange': float(raw_val),
                        'snr': float(snr)
                    })
        except:
            continue
    return pd.DataFrame(data_points)

def plot_clean_motion(df):
    if df.empty:
        print("❌ Brak danych.")
        return

    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(14, 8))
    
    prns = df['prn'].unique()
    prns.sort()
    
    print(f"✅ Znaleziono satelity: {prns}")
    
    # Kolory dla satelitów
    colors = plt.cm.hsv(np.linspace(0, 1, len(prns)))

    for i, prn in enumerate(prns):
        subset = df[df['prn'] == prn].sort_values('time')
        if len(subset) < 50: continue # Pomijamy satelity, które tylko mignęły

        # 1. Obliczamy Dopplera z różnicy odległości
        delta_p = subset['pseudorange'].diff()
        delta_t = subset['time'].diff()
        
        # Unikamy dzielenia przez zero
        valid = delta_t > 0
        if not valid.any(): continue
        
        time_axis = subset.loc[valid, 'time']
        range_rate = -(delta_p[valid] / delta_t[valid])
        raw_doppler = range_rate / LAMBDA_L1
        
        # 2. FILTRACJA SKOKÓW ZEGARA (To naprawia te +/- 2000k)
        # Odejmujemy medianę, żeby wycentrować wykres wokół zera
        median_dop = raw_doppler.median()
        centered_doppler = raw_doppler - median_dop
        
        # Maska: Akceptujemy tylko zmiany w zakresie +/- 800 Hz od średniej
        # Prawdziwy ruch auta to max +/- 200 Hz zmiany.
        mask = np.abs(centered_doppler) < 800 
        
        clean_time = time_axis[mask]
        clean_doppler = centered_doppler[mask]
        
        if len(clean_doppler) < 50: continue

        # 3. WYGŁADZANIE (Żeby było widać "ładne fale" a nie szum)
        try:
            # Savitzky-Golay świetnie zachowuje kształt górek (Twoje hamowania)
            smooth_doppler = savgol_filter(clean_doppler, window_length=51, polyorder=3)
        except:
            smooth_doppler = clean_doppler.rolling(window=30, center=True).mean()

        # Rysujemy
        ax.plot(clean_time, smooth_doppler, label=f'PRN {prn}', color=colors[i], linewidth=2)

    ax.set_title('Analiza Dynamiki Jazdy (Wszystkie Satelity)\nWidoczne przyspieszenia i hamowania', fontsize=16)
    ax.set_xlabel('Czas [s]', fontsize=12)
    ax.set_ylabel('Względna Zmiana Częstotliwości [Hz]', fontsize=12)
    
    ax.legend(loc='upper right', bbox_to_anchor=(1.1, 1))
    ax.grid(True, linestyle='--', alpha=0.3)
    
    # Ustawiamy sztywny zakres Y, żeby wyciąć ewentualne pozostałe śmieci
    ax.set_ylim(-400, 400) 

    plt.tight_layout()
    output_file = 'analiza_wszystkie_satelity_test.png'
    plt.savefig(output_file)
    print(f"\n✅ Wykres zapisano jako: {output_file}")
    plt.show()

if __name__ == "__main__":
    df = parse_file_raw(TARGET_FILE)
    plot_clean_motion(df)