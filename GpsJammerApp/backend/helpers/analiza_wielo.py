import json
import matplotlib.pyplot as plt
import numpy as np
import sys
import os

# === KONFIGURACJA ===
filename = "capture_ruch3.txt"     # Plik z danymi
output_folder = "plots"        # Nazwa folderu na wykresy
# ====================

print(f"--- ANALIZA DANYCH Z JSON: {filename} ---")

if not os.path.exists(filename):
    print(f"Błąd: Nie znaleziono pliku {filename}")
    sys.exit(1)

# Słowniki na dane
data_snr = {}
data_resid = {}
data_az = {}
data_el = {}
time_axis = {}
lats = []
lons = []
sample_counter = 0

# Czytanie pliku
with open(filename, 'r') as f:
    content = f.read()

# Wyciąganie bloków JSON
json_blocks = []
decoder = json.JSONDecoder()
pos = 0

while True:
    match = content.find('{', pos)
    if match == -1:
        break
    try:
        res, index = decoder.raw_decode(content[match:])
        json_blocks.append(res)
        pos = match + index
    except ValueError:
        pos = match + 1

print(f"Znaleziono {len(json_blocks)} ramek danych.")

# Parsowanie danych
for block in json_blocks:
    sample_counter += 1
    
    if "position" in block:
        pos_data = block["position"]
        if pos_data.get("lat", 0) != 0 and pos_data.get("lon", 0) != 0:
            lats.append(pos_data.get("lat"))
            lons.append(pos_data.get("lon"))

    if "observations" in block:
        for obs in block["observations"]:
            prn = obs.get("prn")
            snr = obs.get("snr")
            residual = obs.get("residual")
            az = obs.get("az", 0)
            el = obs.get("el", 0)
            
            if prn is not None:
                if prn not in data_snr:
                    data_snr[prn] = []
                    data_resid[prn] = []
                    data_az[prn] = []
                    data_el[prn] = []
                    time_axis[prn] = []
                
                data_snr[prn].append(snr)
                data_resid[prn].append(residual)
                data_az[prn].append(az)
                data_el[prn].append(el)
                time_axis[prn].append(sample_counter)

# --- RYSOWANIE ---
fig = plt.figure(figsize=(16, 12))
gs = fig.add_gridspec(2, 2)

# 1. WYKRES SNR
ax1 = fig.add_subplot(gs[0, 0])
for prn, vals in data_snr.items():
    if len(vals) > 1:
        ax1.plot(time_axis[prn], vals, marker='.', label=f'PRN {prn}')
ax1.set_title("1. Siła Sygnału (SNR)", fontweight='bold')
ax1.set_xlabel("Numer próbki")
ax1.set_ylabel("SNR (dB)")
ax1.grid(True, linestyle='--', alpha=0.7)
ax1.legend(loc='lower right', fontsize='small', ncol=2)

# 2. WYKRES RESIDUALS
ax2 = fig.add_subplot(gs[0, 1])
for prn, vals in data_resid.items():
    if len(vals) > 1:
        ax2.plot(time_axis[prn], vals, marker='x', label=f'PRN {prn}')
ax2.set_title("2. Błąd Odległości (Residuum)\n(Skok o ~145m = 1 sample slip)", fontweight='bold')
ax2.set_xlabel("Numer próbki")
ax2.set_ylabel("Błąd (metry)")
ax2.grid(True, linestyle='--', alpha=0.7)

# 3. SKYPLOT
ax3 = fig.add_subplot(gs[1, 0], projection='polar')
ax3.set_theta_zero_location("N")
ax3.set_theta_direction(-1)
legend_handles = []
processed_prns = []

for prn in data_az.keys():
    if len(data_az[prn]) > 0:
        az_rad = np.radians(data_az[prn][-1])
        el = data_el[prn][-1]
        res_mean = np.mean(data_resid[prn])
        color = 'red' if abs(res_mean) > 15 else 'green'
        sc = ax3.scatter(az_rad, 90-el, c=color, s=150, edgecolors='black', alpha=0.8)
        ax3.text(az_rad, 90-el, f" {prn}", fontsize=9, fontweight='bold')
        
        if 'red' not in processed_prns and color == 'red':
            legend_handles.append((sc, "Błąd > 15m"))
            processed_prns.append('red')
        if 'green' not in processed_prns and color == 'green':
            legend_handles.append((sc, "OK (<15m)"))
            processed_prns.append('green')

ax3.set_title("3. Mapa Nieba (Skyplot)", va='bottom', fontweight='bold')
ax3.set_yticks([0, 30, 60])
ax3.set_yticklabels(['90', '60', '30'])
ax3.set_rlim(0, 90)
if legend_handles:
    ax3.legend([h[0] for h in legend_handles], [h[1] for h in legend_handles], loc='lower left', fontsize='small')

# 4. SCATTER PLOT
ax4 = fig.add_subplot(gs[1, 1])
if len(lats) > 5:
    mean_lat = np.mean(lats)
    mean_lon = np.mean(lons)
    y_m = [(l - mean_lat) * 111132 for l in lats]
    x_m = [(l - mean_lon) * 111132 * np.cos(np.radians(mean_lat)) for l in lons]
    
    ax4.plot(x_m, y_m, marker='o', linestyle='-', markersize=4, alpha=0.6, color='blue')
    ax4.set_title("4. Rozrzut Pozycji", fontweight='bold')
    ax4.set_xlabel("Wschód-Zachód [m]")
    ax4.set_ylabel("Północ-Południe [m]")
    ax4.axis('equal')
    ax4.grid(True)
else:
    ax4.text(0.5, 0.5, "Za mało danych pozycji", ha='center', va='center')

plt.tight_layout()

# === ZAPISYWANIE DO PLIKU ===

# 1. Sprawdź czy folder istnieje, jak nie to stwórz
if not os.path.exists(output_folder):
    os.makedirs(output_folder)
    print(f"Utworzono folder: {output_folder}")

# 2. Wygeneruj nazwę pliku: plot_(nazwa_pliku_danych).png
base_name = os.path.splitext(os.path.basename(filename))[0] # np. "moje_dane"
plot_filename = f"plot_{base_name}.png"
save_path = os.path.join(output_folder, plot_filename)

# 3. Zapisz
plt.savefig(save_path, dpi=300) # dpi=300 dla wysokiej jakości
print(f"--- SUKCES! Wykres zapisano w: {save_path} ---")

# Możesz zakomentować poniższą linię, jeśli nie chcesz, żeby wykres wyskakiwał na ekranie
plt.show()