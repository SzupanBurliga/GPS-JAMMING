import json
import re
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

# ============================================================================
# ⚙️ KONFIGURACJA
TARGET_FILE = 'capture_nowy_test1.txt' 

# Siła wygładzania (Im większa liczba, tym gładsza linia, ale mniej dokładna na końcach)
SMOOTHING_WINDOW = 25  
# ============================================================================

def parse_log_file_for_skyplot(filepath):
    """Wczytuje plik i wyciąga dane o Azymucie i Elewacji."""
    data_points = []
    
    if not os.path.exists(filepath):
        print(f"❌ BŁĄD: Nie znaleziono pliku '{filepath}'")
        return pd.DataFrame()

    print(f"🔄 Wczytuję dane z {filepath}...")
    
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    blocks = re.split(r'\n={5,}\n', content)

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
                az = obs.get('az')
                el = obs.get('el')

                if prn is not None and az is not None and el is not None:
                    # Filtrujemy zerowe odczyty (błędy)
                    if az == 0.0 and el == 0.0: continue
                        
                    data_points.append({
                        'time': float(elapsed),
                        'prn': int(prn),
                        'az': float(az),
                        'el': float(el)
                    })
        except:
            continue
            
    return pd.DataFrame(data_points)

def plot_smooth_skyplot(df):
    if df.empty:
        print("❌ Brak danych.")
        return

    # Ustawienia wykresu
    plt.style.use('default') 
    fig = plt.figure(figsize=(10, 10))
    ax = fig.add_subplot(111, projection='polar')
    
    # Konfiguracja osi
    ax.set_theta_zero_location("N")  
    ax.set_theta_direction(-1)       
    ax.set_ylim(0, 90)
    ax.set_yticks([0, 30, 60, 90])
    ax.set_yticklabels(['90°', '60°', '30°', '0°']) 
    ax.set_facecolor('#f8f9fa') # Lekko szare tło
    ax.grid(True, linestyle=':', alpha=0.6)
    
    prns = sorted(df['prn'].unique())
    print(f"✅ Znaleziono satelity: {prns}")
    
    # Kolory
    colors = plt.cm.turbo(np.linspace(0, 1, len(prns)))

    for i, prn in enumerate(prns):
        subset = df[df['prn'] == prn].sort_values('time')
        
        if len(subset) < 10: continue

        # --- WYGŁADZANIE DANYCH ---
        # Używamy średniej kroczącej (rolling mean) żeby usunąć "drgania"
        # min_periods=1 sprawia, że nie tracimy danych na brzegach
        subset['az_smooth'] = subset['az'].rolling(window=SMOOTHING_WINDOW, center=True, min_periods=1).mean()
        subset['el_smooth'] = subset['el'].rolling(window=SMOOTHING_WINDOW, center=True, min_periods=1).mean()

        # Konwersja do układu polarnego (na wygładzonych danych)
        theta = np.deg2rad(subset['az_smooth'])
        r = 90 - subset['el_smooth']
        
        # Rysowanie ścieżki (GŁADKA LINIA)
        ax.plot(theta, r, label=f'PRN {prn}', color=colors[i], linewidth=2.5, alpha=0.8)
        
        # Kropka końcowa (Gdzie jest teraz)
        ax.scatter(theta.iloc[-1], r.iloc[-1], color=colors[i], s=120, edgecolors='black', zorder=10)
        
        # Kropka początkowa (Skąd przyleciał)
        ax.scatter(theta.iloc[0], r.iloc[0], color=colors[i], s=30, alpha=0.4)

        # Etykieta PRN
        ax.annotate(f"{prn}", xy=(theta.iloc[-1], r.iloc[-1]), xytext=(8, 8), 
                    textcoords='offset points', color='black', fontweight='bold', fontsize=11,
                    bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=colors[i], alpha=0.8))

    ax.set_title(f'Wygładzona Trajektoria Satelitów (Skyplot)\nPlik: {TARGET_FILE}', fontsize=15, pad=20)
    ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.0), title="Satelity")
    
    plt.tight_layout()
    output_file = 'skyplot_smooth.png'
    plt.savefig(output_file, dpi=150)
    print(f"\n🌌 Gładki wykres zapisano jako: {output_file}")
    plt.show()

if __name__ == "__main__":
    df = parse_log_file_for_skyplot(TARGET_FILE)
    plot_smooth_skyplot(df)