import numpy as np
import pandas as pd
from haversine import haversine, Unit  # Wciąż potrzebne dla Trybu Statycznego
import os.path
import math

# --- USTAWIENIA OGÓLNE ---
SAMPLING_RATE = 2048000  # Ustaw na 2.6e6 lub inną wartość
GPS_WEAKEN_SCALE = 0.05  # Osłabienie sygnału GPS

# --- USTAWIENIA PLIKÓW ---
GPS_TRAJ_FILE = 'traj.csv' 
GPS_SIGNAL_FILE = 'test.bin'
JAMMER_SIGNAL_FILE = 'test_jammer.bin'
OUTPUT_FILE = 'final_output_z_zagluszeniem.bin'

# --- WSPÓLNE USTAWIENIA JAMMERA (dla obu trybów) ---
JAMMER_MAX_RANGE_METERS = 15.0  # Zasięg 15 metrów
# Lokalizacja jammera w LAT/LON/ALT (do konwersji)
JAMMER_LOCATION = (50.0000000, 19.904000, 350.0) 

# --- TRYB 1: USTAWIENIA DYNAMICZNE (jeśli traj.csv istnieje) ---
DYNAMIC_JAMMER_POWER = 1.0 # Moc jammera w punkcie 0m

# --- TRYB 2: USTAWIENIA STATYCZNE (jeśli traj.csv nie istnieje) ---
DELAY_SECONDS = 80      
DURATION_SECONDS = 10    
STATIC_JAMMER_POWER = 1.0 # Moc jammera w punkcie 0m
STATIC_RECEIVER_LOCATION = (50.000000, 19.900000, 220.0)

# =============================================================================
# FUNKCJA: Konwersja Lat/Lon/Alt na ECEF (X, Y, Z)
# =============================================================================
def latlon_to_ecef(lat, lon, alt):
    """Konwertuje współrzędne WGS-84 (Lat, Lon, Alt) na ECEF (X, Y, Z)."""
    a = 6378137.0         
    f = 1 / 298.257223563 
    e_sq = f * (2 - f)    

    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)
    N = a / math.sqrt(1 - e_sq * math.sin(lat_rad)**2)

    X = (N + alt) * math.cos(lat_rad) * math.cos(lon_rad)
    Y = (N + alt) * math.cos(lat_rad) * math.sin(lon_rad)
    Z = ((N * (1 - e_sq)) + alt) * math.sin(lat_rad)
    return (X, Y, Z)
# =============================================================================

# -----------------------------------------------------------------
# --- GŁÓWNY SKRYPT ---
# -----------------------------------------------------------------

print("Wczytywanie plików binarnych...")
gps_data = np.fromfile(GPS_SIGNAL_FILE, dtype=np.int8).astype(np.float32)
jammer_data = np.fromfile(JAMMER_SIGNAL_FILE, dtype=np.int8).astype(np.float32)

print("Osłabianie sygnału GPS...")
gps_slaby = gps_data * GPS_WEAKEN_SCALE

min_len = min(len(gps_slaby), len(jammer_data))
gps_slaby = gps_slaby[:min_len]
jammer_data = jammer_data[:min_len]

jammer_power_profile = np.zeros_like(gps_slaby)

# --- GŁÓWNA LOGIKA WYBORU TRYBU ---
if os.path.exists(GPS_TRAJ_FILE):
    #
    # --- TRYB 1: DYNAMICZNY (plik traj.csv istnieje) ---
    #
    print(f"Wykryto plik '{GPS_TRAJ_FILE}'. Uruchamiam tryb DYNAMICZNY (zasięg).")
    print("Format trajektorii: ECEF (X,Y,Z).")
    
    print("Konwertuję lokalizację jammera (Lat/Lon) na ECEF (X,Y,Z)...")
    JAMMER_ECEF = latlon_to_ecef(JAMMER_LOCATION[0], JAMMER_LOCATION[1], JAMMER_LOCATION[2])
    print(f"Pozycja jammera (ECEF): X={JAMMER_ECEF[0]:.1f}, Y={JAMMER_ECEF[1]:.1f}, Z={JAMMER_ECEF[2]:.1f}")

    try:
        traj_df = pd.read_csv(GPS_TRAJ_FILE, header=None, names=['time', 'x', 'y', 'z'])
    except Exception as e:
        print(f"BŁĄD: Nie mogłem wczytać {GPS_TRAJ_FILE}: {e}")
        exit()

    print(f"Wczytano trajektorię odbiornika: {len(traj_df)} punktów.")
    
    power_profile_per_timestep = [] 
    for index, row in traj_df.iterrows():
        receiver_ecef = (row['x'], row['y'], row['z'])
        
        total_distance = math.sqrt(
            (receiver_ecef[0] - JAMMER_ECEF[0])**2 +
            (receiver_ecef[1] - JAMMER_ECEF[1])**2 +
            (receiver_ecef[2] - JAMMER_ECEF[2])**2
        )

        # Logika mocy (spadek liniowy)
        if total_distance > JAMMER_MAX_RANGE_METERS:
            power_scale = 0.0  # Poza zasięgiem
        else:
            power_scale = DYNAMIC_JAMMER_POWER * (1.0 - (total_distance / JAMMER_MAX_RANGE_METERS))
        
        power_profile_per_timestep.append(power_scale)
        # -----------------------------------------------------------------

    print("Utworzono profil mocy jammera.")
    
    try:
        # Poprawnie odczytaj krok czasowy (np. 0.1s)
        time_step = traj_df['time'].iloc[1] - traj_df['time'].iloc[0]
    except IndexError:
        time_step = 1.0 # Na wypadek gdyby plik miał 1 linię
    
    print(f"Wykryty krok czasowy: {time_step} s")
    samples_per_timestep = int(SAMPLING_RATE * 2 * time_step) 

    if samples_per_timestep == 0:
        print("BŁĄD: samples_per_timestep wynosi zero. Sprawdź SAMPLING_RATE.")
        exit()

    try:
        dynamic_jammer_power = np.repeat(power_profile_per_timestep, samples_per_timestep).astype(np.float32)
    except ValueError as e:
        print(f"BŁĄD: Długość trajektorii nie pasuje do długości plików binarnych. {e}")
        exit()

    profile_len = min(len(dynamic_jammer_power), len(jammer_power_profile))
    jammer_power_profile[:profile_len] = jammer_data[:profile_len] * dynamic_jammer_power[:profile_len]

else:
    #
    # --- TRYB 2: STATYCZNY (plik traj.csv nie istnieje) ---
    #
    print(f"Brak pliku '{GPS_TRAJ_FILE}'. Uruchamiam tryb STATYCZNY (opóźnienie + sprawdzanie zasięgu).")
    print("Format lokalizacji: Lat/Lon.")
    
    print("Sprawdzam zasięg dla lokalizacji statycznej...")
    jammer_coords_2d = (JAMMER_LOCATION[0], JAMMER_LOCATION[1])
    receiver_coords_2d = (STATIC_RECEIVER_LOCATION[0], STATIC_RECEIVER_LOCATION[1])
    
    distance_2d = haversine(jammer_coords_2d, receiver_coords_2d, unit=Unit.METERS)
    distance_alt = abs(JAMMER_LOCATION[2] - STATIC_RECEIVER_LOCATION[2])
    total_distance = np.sqrt(distance_2d**2 + distance_alt**2)
    
    print(f"Odległość odbiornika od jammera: {total_distance:.2f} m")

    if total_distance > JAMMER_MAX_RANGE_METERS:
        print(f"Odbiornik POZA ZASIĘGIEM (Zasięg: {JAMMER_MAX_RANGE_METERS} m). Jammer nie zostanie dodany.")
    else:
        # Oblicz moc na podstawie odległości
        power_scale = STATIC_JAMMER_POWER * (1.0 - (total_distance / JAMMER_MAX_RANGE_METERS))
        print(f"Odbiornik W ZASIĘGU. Obliczona moc jammera: {power_scale*100:.1f}%")
            
        start_index = int(SAMPLING_RATE * DELAY_SECONDS * 2)
        duration_samples = int(SAMPLING_RATE * DURATION_SECONDS * 2)
        
        jammer_copy_len = min(len(jammer_data), duration_samples)
        space_available = len(jammer_power_profile) - start_index
        final_copy_len = min(jammer_copy_len, space_available)

        if final_copy_len > 0:
            print(f"Dodaję jammer (moc {power_scale*100:.1f}%) od {DELAY_SECONDS}s do {DELAY_SECONDS + (final_copy_len / (SAMPLING_RATE * 2)):.2f}s")
            jammer_power_profile[start_index : start_index + final_copy_len] = \
                jammer_data[:final_copy_len] * power_scale 
        else:
            print("Ostrzeżenie: Plik GPS jest za krótki (sprawdź DELAY_SECONDS).")
    # -----------------------------------------------------------------


# --- KONIEC LOGIKI IF/ELSE ---

# 4. Połącz sygnały
print("Łączenie sygnałów...")
sygnal_wynikowy_float = gps_slaby + jammer_power_profile

# 5. Przytnij (clip) i konwertuj z powrotem do int8
sygnal_wynikowy_float = np.clip(sygnal_wynikowy_float, -128.0, 127.0)
final_signal_int8 = sygnal_wynikowy_float.astype(np.float32) # Poprawka: Zostaw float do następnego kroku

# 6. Konwertuj na uint8 dla gnss-sdrlib
# Poprawka: konwertuj z float, a nie z int8, aby uniknąć podwójnej utraty precyzji
final_signal_uint8 = (sygnal_wynikowy_float.astype(np.int16) + 128).astype(np.uint8)

# 7. Zapisz finalny plik
final_signal_uint8.tofile(OUTPUT_FILE)

print(f"Gotowe! Zapisano jako {OUTPUT_FILE}")