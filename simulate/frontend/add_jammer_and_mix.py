import numpy as np
import pandas as pd
from haversine import haversine, Unit
import os.path
import math
import argparse

# ustawienia na twardo (pliki i inne)
SAMPLING_RATE = 2048000  
GPS_WEAKEN_SCALE = 0.05  
GPS_SIGNAL_FILE = 'test.bin'
OUTPUT_FILE = 'symulacja_jammera.bin'
GPS_TRAJ_FILE = 'traj.csv' 
JAMMER_SIGNAL_FILE = 'jammers/jammer_file.bin'


# ustawienia jammera
JAMMER_MAX_RANGE_METERS = 10.0  # Maksymalny zasięg, po którym moc = 0 (promień jammera)
JAMMER_LOCATION = (50.00000000,19.9000090,350.0) 

DYNAMIC_JAMMER_POWER = 1.0 
STATIC_JAMMER_POWER = 1.0  

AMPLITUDE_REFERENCE_DISTANCE_METERS = 15.0 

# ustawienia trybu statycznego (brak traj.csv)
DELAY_SECONDS = 60      
DURATION_SECONDS = 30    
STATIC_RECEIVER_LOCATION = (50.0000000, 19.9000000, 350.0)


def latlon_to_ecef(lat, lon, alt):
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


gps_data = np.fromfile(GPS_SIGNAL_FILE, dtype=np.int8).astype(np.float32)
jammer_data = np.fromfile(JAMMER_SIGNAL_FILE, dtype=np.int8).astype(np.float32)
gps_slaby = gps_data * GPS_WEAKEN_SCALE

min_len = min(len(gps_slaby), len(jammer_data))
gps_slaby = gps_slaby[:min_len]
jammer_data = jammer_data[:min_len]
jammer_power_profile = np.zeros_like(gps_slaby)

if os.path.exists(GPS_TRAJ_FILE):
    print("Tryb DYNAMICZNY")
    JAMMER_ECEF = latlon_to_ecef(JAMMER_LOCATION[0], JAMMER_LOCATION[1], JAMMER_LOCATION[2])
    try:
        traj_df = pd.read_csv(GPS_TRAJ_FILE, header=None, names=['time', 'x', 'y', 'z'])
    except Exception as e:
        print(f"Błąd wczytywania pliku trajektorii: {e}")
        exit()
    try:
        os.remove(GPS_TRAJ_FILE)
        print(f"Plik {GPS_TRAJ_FILE} został pomyślnie wczytany i usunięty.")
    except OSError as e:
        print(f"Nie można usunąć pliku {GPS_TRAJ_FILE}. Błąd: {e}")

    power_profile_per_timestep = [] 
    for index, row in traj_df.iterrows():
        receiver_ecef = (row['x'], row['y'], row['z'])
        total_distance = math.sqrt(
            (receiver_ecef[0] - JAMMER_ECEF[0])**2 +
            (receiver_ecef[1] - JAMMER_ECEF[1])**2 +
            (receiver_ecef[2] - JAMMER_ECEF[2])**2
        )
        if total_distance > JAMMER_MAX_RANGE_METERS:
            power_scale = 0.0  # Poza zasięgiem
        elif total_distance < AMPLITUDE_REFERENCE_DISTANCE_METERS:
            power_scale = DYNAMIC_JAMMER_POWER 
        else:
            # Realistyczny model spadku AMPLITUDY (prawo 1/d)
            # Używamy wykładnika **1 (zamiast **2 dla mocy)
            power_scale = DYNAMIC_JAMMER_POWER * (AMPLITUDE_REFERENCE_DISTANCE_METERS / total_distance)**1

        power_profile_per_timestep.append(power_scale)

    try:
        time_step = traj_df['time'].iloc[1] - traj_df['time'].iloc[0]
    except IndexError:
        time_step = 1.0
    samples_per_timestep = int(SAMPLING_RATE * 2 * time_step) 

    if samples_per_timestep == 0:
        print("Błąd: samples_per_timestep wynosi 0. Sprawdź plik trajektorii lub SAMPLING_RATE.")
        exit()
    print("Obliczam płynny profil mocy (interpolacja liniowa)...")
    all_power_segments = []
    
    for i in range(len(power_profile_per_timestep) - 1):
        p_start = power_profile_per_timestep[i]
        p_end = power_profile_per_timestep[i+1]
        segment = np.linspace(p_start, p_end, samples_per_timestep, dtype=np.float32, endpoint=False) 
        all_power_segments.append(segment)

    if power_profile_per_timestep:
        last_power_value = power_profile_per_timestep[-1]
        last_segment = np.full(samples_per_timestep, last_power_value, dtype=np.float32)
        all_power_segments.append(last_segment)

    if all_power_segments:
         dynamic_jammer_power = np.concatenate(all_power_segments).astype(np.float32)
    else:
         dynamic_jammer_power = np.array([], dtype=np.float32) 

    profile_len = min(len(dynamic_jammer_power), len(jammer_power_profile))
    jammer_power_profile[:profile_len] = jammer_data[:profile_len] * dynamic_jammer_power[:profile_len]

# dla braku traj.csv (tryb statyczny)
else:
    print("Tryb STATYCZNY (Realistyczny model 1/d). Brak pliku traj.csv.")
    jammer_coords_2d = (JAMMER_LOCATION[0], JAMMER_LOCATION[1])
    receiver_coords_2d = (STATIC_RECEIVER_LOCATION[0], STATIC_RECEIVER_LOCATION[1])
    distance_2d = haversine(jammer_coords_2d, receiver_coords_2d, unit=Unit.METERS)
    distance_alt = abs(JAMMER_LOCATION[2] - STATIC_RECEIVER_LOCATION[2])
    total_distance = np.sqrt(distance_2d**2 + distance_alt**2)
    
    print(f"Odległość odbiornika od jammera: {total_distance:.2f} metrów.")
    if total_distance > JAMMER_MAX_RANGE_METERS:
        print(f"Odbiornik poza zasięgiem ({JAMMER_MAX_RANGE_METERS}m). Jammer nie zostanie dodany.")
    else:
        if total_distance < AMPLITUDE_REFERENCE_DISTANCE_METERS:
            power_scale = STATIC_JAMMER_POWER
        else:
            # Realistyczny model spadku AMPLITUDY (prawo 1/d)
            # Używamy wykładnika **1 (zamiast **2 dla mocy)
            power_scale = STATIC_JAMMER_POWER * (AMPLITUDE_REFERENCE_DISTANCE_METERS / total_distance)**1

        print(f"Odbiornik W ZASIĘGU. Obliczona skala amplitudy: {power_scale*100:.2f}%")
        start_index = int(SAMPLING_RATE * DELAY_SECONDS * 2)
        duration_samples = int(SAMPLING_RATE * DURATION_SECONDS * 2)
        jammer_copy_len = min(len(jammer_data), duration_samples)
        space_available = len(jammer_power_profile) - start_index
        final_copy_len = min(jammer_copy_len, space_available)

        if final_copy_len > 0:
            print(f"Dodaję jammer (skala {power_scale*100:.2f}%) od {DELAY_SECONDS}s do {DELAY_SECONDS + (final_copy_len / (SAMPLING_RATE * 2)):.2f}s")
            jammer_power_profile[start_index : start_index + final_copy_len] = \
                jammer_data[:final_copy_len] * power_scale 
        else:
            print("Ostrzeżenie: Plik GPS jest za krótki (sprawdź DELAY_SECONDS).")

print("Łączenie sygnału GPS i jammera...")
sygnal_wynikowy_float = gps_slaby + jammer_power_profile

# normalizacja i konwersja
sygnal_wynikowy_float = np.clip(sygnal_wynikowy_float, -128.0, 127.0)
final_signal_uint8 = (sygnal_wynikowy_float.astype(np.int16) + 128).astype(np.uint8)

print(f"Zapisywanie pliku wynikowego: {OUTPUT_FILE}")
final_signal_uint8.tofile(OUTPUT_FILE)