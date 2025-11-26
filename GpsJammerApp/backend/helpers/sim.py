import json
import glob
import math
import pandas as pd
import numpy as np
import re
import os

# ==========================================
# KONFIGURACJA POZYCJI REFERENCYJNEJ
# ==========================================
# Tutaj wpisz współrzędne "danej pozycji", od której liczymy błąd.
# Wstawiłem przykładowe wartości z Twojego pierwszego loga.
REF_LAT = 50.01724747
REF_LON = 19.94023277
REF_HGT = 225.0

# Nazwa pliku wynikowego
OUTPUT_EXCEL = "wyniki_analizy_gps.xlsx"

def haversine_distance_3d(lat1, lon1, alt1, lat2, lon2, alt2):
    """
    Oblicza odległość 3D w metrach między dwoma punktami GPS.
    Używa formuły Haversine dla odległości poziomej i Pitagorasa dla wysokości.
    """
    R = 6371000  # Promień Ziemi w metrach

    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2)**2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(dlambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    horizontal_dist = R * c
    vertical_dist = abs(alt1 - alt2)

    # Odległość 3D (przekątna)
    return math.sqrt(horizontal_dist**2 + vertical_dist**2)

def parse_log_file(filepath, filename_short):
    """
    Parsuje pojedynczy plik tekstowy z mieszaną zawartością JSON.
    """
    parsed_data = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Dzielimy plik po separatorze "===="
    # Zakładamy, że JSON jest pomiędzy nagłówkami a separatorami
    chunks = content.split('=' * 80)

    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue

        try:
            # Szukamy początku i końca JSONa (klamry {})
            json_start = chunk.find('{')
            json_end = chunk.rfind('}') + 1
            
            if json_start != -1 and json_end != -1:
                json_str = chunk[json_start:json_end]
                data = json.loads(json_str)

                # Wyciągamy potrzebne dane
                if 'position' in data and 'observations' in data:
                    lat = data['position'].get('lat')
                    lon = data['position'].get('lon')
                    hgt = data['position'].get('hgt')
                    
                    # Obliczamy średni SNR dla tej epoki (średnia z satelitów widocznych w tym momencie)
                    snr_values = [obs['snr'] for obs in data['observations'] if 'snr' in obs]
                    avg_snr_epoch = np.mean(snr_values) if snr_values else 0

                    # Obliczamy odchylenie od pozycji referencyjnej
                    deviation = haversine_distance_3d(lat, lon, hgt, REF_LAT, REF_LON, REF_HGT)

                    parsed_data.append({
                        "Plik": filename_short,
                        "Czas_Sys": data.get('time'),
                        "Lat": lat,
                        "Lon": lon,
                        "Hgt": hgt,
                        "Liczba_Sat": len(snr_values),
                        "Sredni_SNR_Epoka": avg_snr_epoch,
                        "Odchylenie_m": deviation
                    })
        except json.JSONDecodeError:
            continue # Ignorujemy fragmenty, które nie są poprawnym JSONem
        except Exception as e:
            print(f"Błąd przy przetwarzaniu fragmentu w pliku {filename_short}: {e}")

    return parsed_data

def main():
    all_records = []
    
    # Generowanie listy plików capture_nowy_test1.txt do capture_nowy_test10.txt
    # (lub wszystkich pasujących do wzorca, jeśli chcesz bardziej ogólnie)
    file_list = [f"capture_nowy_test{i}.txt" for i in range(1, 11)]

    print("Rozpoczynam analizę plików...")

    for filename in file_list:
        if os.path.exists(filename):
            print(f"Przetwarzanie: {filename}")
            file_data = parse_log_file(filename, filename)
            all_records.extend(file_data)
        else:
            print(f"OSTRZEŻENIE: Plik {filename} nie istnieje.")

    if not all_records:
        print("Nie znaleziono żadnych poprawnych danych.")
        return

    # Tworzenie DataFrame z wszystkimi danymi
    df_details = pd.DataFrame(all_records)

    # 1. Średnie dla każdego pliku
    df_file_summary = df_details.groupby("Plik").agg(
        Srednie_Odchylenie_m=('Odchylenie_m', 'mean'),
        Max_Odchylenie_m=('Odchylenie_m', 'max'),
        Sredni_SNR=('Sredni_SNR_Epoka', 'mean'),
        Liczba_Epok=('Plik', 'count')
    ).reset_index()

    # 2. Średnie globalne (dla 10 plików razem)
    global_avg_deviation = df_details['Odchylenie_m'].mean()
    global_avg_snr = df_details['Sredni_SNR_Epoka'].mean()
    
    df_global_summary = pd.DataFrame([{
        "Opis": "Średnia ze wszystkich 10 plików",
        "Globalne_Srednie_Odchylenie_m": global_avg_deviation,
        "Globalny_Sredni_SNR": global_avg_snr,
        "Calkowita_Liczba_Probek": len(df_details)
    }])

    # Zapis do Excela
    print(f"Zapisywanie wyników do {OUTPUT_EXCEL}...")
    with pd.ExcelWriter(OUTPUT_EXCEL, engine='openpyxl') as writer:
        # Arkusz 1: Szczegółowe dane (każdy pomiar)
        df_details.to_excel(writer, sheet_name='Szczegóły', index=False)
        
        # Arkusz 2: Podsumowanie per plik
        df_file_summary.to_excel(writer, sheet_name='Per Plik', index=False)
        
        # Arkusz 3: Podsumowanie globalne
        df_global_summary.to_excel(writer, sheet_name='Globalne', index=False)

    print("Gotowe! Sprawdź plik Excel.")
    
    # Wyświetlenie podglądu w konsoli
    print("\n--- PODSUMOWANIE DLA PLIKÓW ---")
    print(df_file_summary[['Plik', 'Srednie_Odchylenie_m', 'Sredni_SNR']].to_string(index=False))
    print("\n--- PODSUMOWANIE GLOBALNE ---")
    print(f"Średnie odchylenie: {global_avg_deviation:.4f} m")
    print(f"Średni SNR: {global_avg_snr:.4f} dB")

if __name__ == "__main__":
    main()