import json
import matplotlib.pyplot as plt
import numpy as np
import sys
import os
import glob
import re
import pandas as pd

# === KONFIGURACJA ===
INPUT_PATTERN = "capture_10min.txt"  # Wzorzec nazw plików
OUTPUT_DIR = "wyniki_analizy_statycznej"        # Gdzie zapisać wykresy
EXCEL_NAME = "raport_zbiorczy_STATIC.xlsx"  # Nazwa pliku Excel
# ====================

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def parse_file(filepath):
    """Czyta plik i zwraca słowniki z danymi"""
    data_snr = {}
    data_resid = {}
    data_az = {}
    data_el = {}
    time_axis = {}
    lats = []
    lons = []
    raw_rows = [] # Do Excela
    
    sample_counter = 0
    
    with open(filepath, 'r') as f:
        content = f.read()
        
    decoder = json.JSONDecoder()
    pos = 0
    
    while True:
        match = content.find('{', pos)
        if match == -1: break
        try:
            res, index = decoder.raw_decode(content[match:])
            pos = match + index
            
            # Parsowanie JSONa
            sample_counter += 1
            time_str = res.get("time", "")
            
            # Pozycja
            if "position" in res:
                pos_data = res["position"]
                if pos_data.get("lat", 0) != 0:
                    lats.append(pos_data.get("lat"))
                    lons.append(pos_data.get("lon"))
            
            # Obserwacje
            if "observations" in res:
                for obs in res["observations"]:
                    prn = obs.get("prn")
                    if prn is None: continue
                    
                    snr = obs.get("snr", 0)
                    resid = obs.get("residual", 0)
                    az = obs.get("az", 0)
                    el = obs.get("el", 0)
                    # Pamiętamy: w Twoich danych 'doppler' to pseudorange
                    pseudo = obs.get("doppler", 0) 

                    # Zbieranie do struktur wykresowych
                    if prn not in data_snr:
                        data_snr[prn] = []
                        data_resid[prn] = []
                        data_az[prn] = []
                        data_el[prn] = []
                        time_axis[prn] = []
                    
                    data_snr[prn].append(snr)
                    data_resid[prn].append(resid)
                    data_az[prn].append(az)
                    data_el[prn].append(el)
                    time_axis[prn].append(sample_counter)
                    
                    # Zbieranie do Excela (Flattened data)
                    raw_rows.append({
                        "Plik": os.path.basename(filepath),
                        "Próbka": sample_counter,
                        "Czas": time_str,
                        "PRN": prn,
                        "SNR": snr,
                        "Residual": resid,
                        "Azimuth": az,
                        "Elevation": el,
                        "Pseudorange_Raw": pseudo
                    })

        except ValueError:
            pos = match + 1
            
    return {
        "snr": data_snr, "resid": data_resid, "az": data_az, "el": data_el,
        "time": time_axis, "lats": lats, "lons": lons, "excel_data": raw_rows
    }

def generate_plot(data, filename):
    """Rysuje 4 wykresy i zapisuje do pliku"""
    fig = plt.figure(figsize=(16, 12))
    gs = fig.add_gridspec(2, 2)
    
    # 1. SNR
    ax1 = fig.add_subplot(gs[0, 0])
    for prn, vals in data["snr"].items():
        if len(vals) > 5:
            ax1.plot(data["time"][prn], vals, marker='.', markersize=2, label=f'G{prn}')
    ax1.set_title(f"1. Siła Sygnału SNR ({filename})")
    ax1.set_ylabel("dB")
    ax1.grid(True, alpha=0.5)
    ax1.legend(ncol=3, fontsize='x-small')

    # 2. RESIDUALS
    ax2 = fig.add_subplot(gs[0, 1])
    for prn, vals in data["resid"].items():
        if len(vals) > 5:
            ax2.plot(data["time"][prn], vals, marker='', linewidth=1)
    ax2.set_title("2. Błąd Odległości (Residuals)")
    ax2.set_ylabel("Metry")
    ax2.grid(True, alpha=0.5)
    ax2.axhline(15, color='r', linestyle='--')

    # 3. SKYPLOT
    ax3 = fig.add_subplot(gs[1, 0], projection='polar')
    ax3.set_theta_zero_location("N")
    ax3.set_theta_direction(-1)
    for prn in data["az"]:
        if len(data["az"][prn]) > 0:
            az_rad = np.radians(data["az"][prn][-1])
            el = data["el"][prn][-1]
            mean_resid = np.mean(data["resid"][prn])
            color = 'red' if mean_resid > 15 else 'green'
            ax3.scatter(az_rad, 90-el, c=color, s=100, edgecolors='k')
            ax3.text(az_rad, 90-el, f"{prn}", fontsize=9, fontweight='bold')
    ax3.set_title("3. Skyplot (Czerwony = Błąd > 15m)")
    ax3.set_rlim(0, 90)
    ax3.set_yticks([0, 30, 60])
    ax3.set_yticklabels(['90', '60', '30'])

    # 4. SCATTER PLOT POZYCJI
    ax4 = fig.add_subplot(gs[1, 1])
    lats = data["lats"]
    lons = data["lons"]
    if len(lats) > 10:
        mean_lat = np.mean(lats)
        mean_lon = np.mean(lons)
        # Konwersja na metry (względem średniej)
        y_m = [(l - mean_lat) * 111132 for l in lats]
        x_m = [(l - mean_lon) * 111132 * np.cos(np.radians(mean_lat)) for l in lons]
        
        ax4.plot(x_m, y_m, marker='.', linestyle='-', markersize=2, alpha=0.5)
        
        # Statystyka błędu pozycji (promień)
        dists = np.sqrt(np.array(x_m)**2 + np.array(y_m)**2)
        max_err = np.max(dists)
        
        ax4.set_title(f"4. Rozrzut Pozycji (Max Error: {max_err:.1f}m)")
        ax4.set_xlabel("Metry E-W")
        ax4.set_ylabel("Metry N-S")
        ax4.axis('equal')
        ax4.grid(True)
    else:
        ax4.text(0.5, 0.5, "Brak stabilnej pozycji", ha='center')

    plt.tight_layout()
    save_path = os.path.join(OUTPUT_DIR, f"plot_{filename.replace('.txt', '.png')}")
    plt.savefig(save_path, dpi=150)
    plt.close(fig)
    print(f" -> Zapisano wykres: {save_path}")

# === GŁÓWNA PĘTLA ===

# Znajdź pliki
files = glob.glob(INPUT_PATTERN)
# Sortowanie numeryczne (żeby 10 było po 9)
files.sort(key=lambda f: int(re.sub('\D', '', f)))

all_excel_rows = []
summary_stats = []

print(f"Znaleziono {len(files)} plików do przetworzenia.")

for filepath in files:
    fname = os.path.basename(filepath)
    print(f"Przetwarzanie: {fname}...")
    
    # 1. Parsowanie
    parsed = parse_file(filepath)
    if not parsed["excel_data"]:
        print("   [!] Pusty plik lub brak JSON")
        continue
        
    # 2. Generowanie Wykresu
    generate_plot(parsed, fname)
    
    # 3. Zbieranie danych do Excela
    all_excel_rows.extend(parsed["excel_data"])
    
    # 4. Obliczanie statystyk dla pliku
    snr_values = []
    resid_values = []
    for prn in parsed["snr"]:
        snr_values.extend(parsed["snr"][prn])
        resid_values.extend(parsed["resid"][prn])
        
    # Obliczanie błędu pozycji (jeśli jest)
    pos_error_std = 0
    if len(parsed["lats"]) > 10:
        # Odchylenie standardowe szerokości w metrach
        pos_error_std = np.std(parsed["lats"]) * 111132
    
    summary_stats.append({
        "Plik": fname,
        "Liczba Próbek": len(parsed["lats"]),
        "Średni SNR": np.mean(snr_values) if snr_values else 0,
        "Max SNR": np.max(snr_values) if snr_values else 0,
        "Średni Błąd (Residuum)": np.mean(resid_values) if resid_values else 0,
        "Max Błąd (Residuum)": np.max(resid_values) if resid_values else 0,
        "Stabilność Pozycji (StdDev m)": pos_error_std
    })

# === ZAPIS DO EXCELA ===
#print(f"Generowanie raportu Excel: {EXCEL_NAME}...")
#try:
#    with pd.ExcelWriter(EXCEL_NAME, engine='openpyxl') as writer:
        # Arkusz 1: Podsumowanie (Statystyki)
    #    df_summary = pd.DataFrame(summary_stats)
     #   df_summary.to_excel(writer, sheet_name="Podsumowanie", index=False)
        
        # Arkusz 2: Wszystkie Dane (Surowe)
     #   df_raw = pd.DataFrame(all_excel_rows)
     #   df_raw.to_excel(writer, sheet_name="Dane Szczegółowe", index=False)
        
#    print("SUKCES! Zakończono przetwarzanie.")

#except Exception as e:
#    print(f"Błąd zapisu Excela: {e}")
#    print("Upewnij się, że masz zainstalowane: pip install pandas openpyxl")
#