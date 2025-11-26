import json
import re
import os
import glob
import pandas as pd
import matplotlib.pyplot as plt

# ============================================================================
# ⚙️ KONFIGURACJA
# ============================================================================
# Podaj tutaj pełną ścieżkę do folderu z plikami captureX.txt
# Pamiętaj o ukośniku na końcu.
LOGS_FOLDER = 'capture_ruch7.txt'
# ============================================================================

def parse_single_file(filepath):
    """Wczytuje jeden plik i wyciąga z niego dane Dopplera."""
    filename = os.path.basename(filepath)
    data_points = []
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except Exception as e:
        print(f"⚠️ Błąd odczytu pliku {filename}: {e}")
        return []

    # Dzielimy plik po separatorze (linia znaków =)
    # Używamy wyrażenia regularnego, aby złapać różne długości separatora
    blocks = re.split(r'\n={5,}\n', content)

    for i, block in enumerate(blocks):
        # Szukamy JSONa (wszystko między klamrami { ... })
        # re.DOTALL sprawia, że kropka łapie też nowe linie
        match = re.search(r'(\{.*\})', block, re.DOTALL)
        
        if not match:
            continue # To nie jest blok z danymi JSON, pomijamy

        json_str = match.group(1)

        try:
            data = json.loads(json_str)
            
            # Pobieramy czas symulacji
            elapsed = data.get('elapsed_time')
            if elapsed is None:
                continue

            # Pobieramy listę obserwowanych satelitów
            observations = data.get('observations', [])
            
            # Jeśli lista jest pusta (brak locka), pomijamy
            if not observations:
                continue

            for obs in observations:
                prn = obs.get('prn')
                doppler = obs.get('doppler')
                snr = obs.get('snr')

                if prn is not None and doppler is not None:
                    data_points.append({
                        'file': filename,
                        'time': elapsed,
                        'prn': int(prn),
                        'doppler': float(doppler),
                        'snr': float(snr)
                    })

        except json.JSONDecodeError:
            # Czasami JSON jest ucięty lub uszkodzony - ignorujemy to cicho
            continue
        except Exception as e:
            print(f"⚠️ Inny błąd w bloku {i} pliku {filename}: {e}")
            continue

    return data_points

def main():
    print(f"📂 Szukam plików w: {LOGS_FOLDER}")
    
    if not os.path.isdir(LOGS_FOLDER):
        print("❌ BŁĄD: Podany folder nie istnieje!")
        return

    # Znajdź wszystkie pliki pasujące do wzorca capture*.txt
    file_pattern = os.path.join(LOGS_FOLDER, "capture*.txt")
    files = glob.glob(file_pattern)
    
    # Sortujemy pliki numerycznie (capture1, capture2... a nie capture1, capture10)
    # Wyciągamy liczby z nazwy pliku do sortowania
    files.sort(key=lambda f: int(re.search(r'capture(\d+)', f).group(1)) if re.search(r'capture(\d+)', f) else 0)

    if not files:
        print("❌ Nie znaleziono żadnych plików capture*.txt w tym folderze.")
        return

    print(f"✅ Znaleziono {len(files)} plików. Rozpoczynam analizę...\n")

    all_data = []
    for f in files:
        print(f"   -> Przetwarzanie: {os.path.basename(f)}...")
        file_data = parse_single_file(f)
        all_data.extend(file_data)

    if not all_data:
        print("\n❌ Brak danych Dopplera. Pliki mogą być puste lub symulacja trwała za krótko (<10s).")
        return

    # --- TWORZENIE WYKRESU ---
    print("\n📊 Generowanie wykresu...")
    df = pd.DataFrame(all_data)
    
    # Wybieramy 4 najczęściej pojawiające się satelity (PRN), żeby wykres był czytelny
    top_prns = df['prn'].value_counts().nlargest(4).index.tolist()

    plt.style.use('dark_background')
    fig, axes = plt.subplots(nrows=len(top_prns), ncols=1, figsize=(12, 10), sharex=True)
    
    if len(top_prns) == 1: axes = [axes] # Obsługa przypadku tylko 1 satelity

    fig.suptitle('Analiza Dopplera - Porównanie Plików', fontsize=16)

    # Kolory dla plików (cykliczne)
    colors = plt.cm.jet(np.linspace(0, 1, len(files)))

    for idx, prn in enumerate(top_prns):
        ax = axes[idx]
        subset = df[df['prn'] == prn]
        
        # Rysujemy linię dla każdego pliku osobno
        for i, filepath in enumerate(files):
            filename = os.path.basename(filepath)
            file_subset = subset[subset['file'] == filename]
            
            if not file_subset.empty:
                # Centrujemy Dopplera wokół zera dla czytelności (odejmujemy średnią)
                mean_doppler = file_subset['doppler'].mean()
                ax.plot(file_subset['time'], file_subset['doppler'] - mean_doppler, 
                        label=filename, color=colors[i], linewidth=1, alpha=0.8)

        ax.set_ylabel(f'PRN {prn}\nOffset Dopplera [Hz]')
        ax.grid(True, linestyle='--', alpha=0.3)
        if idx == 0:
            ax.legend(loc='upper right', bbox_to_anchor=(1.15, 1), fontsize='small')

    axes[-1].set_xlabel('Czas symulacji [s]')
    plt.tight_layout()
    
    output_img = 'wynik_doppler_ruch.png'
    plt.savefig(output_img)
    print(f"\n✅ GOTOWE! Wykres zapisano jako: {output_img}")
    print(f"   Znaleziono łącznie {len(df)} próbek pomiarowych.")

if __name__ == "__main__":
    import numpy as np # Potrzebne do kolorów
    main()