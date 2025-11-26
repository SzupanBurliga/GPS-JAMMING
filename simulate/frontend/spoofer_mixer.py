import numpy as np
import pandas as pd
import math
import argparse
import os
import sys

DEFAULT_LEGIT_SCALE = 0.105       
DEFAULT_MAX_SPOOFER_SCALE = 0.70  
DEFAULT_NOISE_STD = 4.5           
CHUNK_SIZE = 1024 * 1024          

EARTH_RADIUS = 6378137.0

def latlon_to_ecef(lat, lon, alt):
    f = 1 / 298.257223563 
    e_sq = f * (2 - f)    
    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)
    N = EARTH_RADIUS / math.sqrt(1 - e_sq * math.sin(lat_rad)**2)
    X = (N + alt) * math.cos(lat_rad) * math.cos(lon_rad)
    Y = (N + alt) * math.cos(lat_rad) * math.sin(lon_rad)
    Z = ((N * (1 - e_sq)) + alt) * math.sin(lat_rad)
    return (X, Y, Z)

def calculate_distance_3d(p1, p2):
    return math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2 + (p1[2]-p2[2])**2)

def main():
    parser = argparse.ArgumentParser(description="Bezpieczne Miksowanie (NATURAL OVERPOWER).")

    parser.add_argument("--legit-file", required=True)
    parser.add_argument("--spoofer-file", required=True)
    parser.add_argument("--output-file", required=True)
    
    parser.add_argument("--victim-lat", type=float, default=None)
    parser.add_argument("--victim-lon", type=float, default=None)
    parser.add_argument("--victim-alt", type=float, default=None)
    parser.add_argument("--spoofer-lat", type=float, default=50.060)
    parser.add_argument("--spoofer-lon", type=float, default=19.940)
    parser.add_argument("--spoofer-alt", type=float, default=220.0)
    parser.add_argument("--traj-file", default=None)
    
    parser.add_argument("--spoofer-power", type=float, default=0.1)
    parser.add_argument("--spoofer-max-scale", type=float, default=DEFAULT_MAX_SPOOFER_SCALE)
    parser.add_argument("--max-range", type=float, default=500.0)
    
    parser.add_argument("--delay-seconds", type=float, default=150.0)
    
    parser.add_argument("--legit-scale", type=float, default=DEFAULT_LEGIT_SCALE)
    parser.add_argument("--noise-std", type=float, default=DEFAULT_NOISE_STD)
    parser.add_argument("--samplerate", type=float, default=2048000.0)
    parser.add_argument("--fade-duration", type=float, default=5.0)

    args = parser.parse_args()

    print(f"--- MIKSER (NATURAL OVERPOWER) ---")
    print(f"   [i] Legit: {DEFAULT_LEGIT_SCALE}")
    print(f"   [i] Spoofer: {DEFAULT_MAX_SPOOFER_SCALE}")
    
    try:
        size_legit = os.path.getsize(args.legit_file)
        size_spoofer = os.path.getsize(args.spoofer_file)
    except FileNotFoundError as e:
        print(f"BŁĄD: {e}"); sys.exit(1)

    total_bytes = min(size_legit, size_spoofer)
    total_samples = total_bytes
    
    spoofer_ecef = latlon_to_ecef(args.spoofer_lat, args.spoofer_lon, args.spoofer_alt)
    distances = []

    if args.traj_file and os.path.exists(args.traj_file):
        try:
            traj_df = pd.read_csv(args.traj_file, header=None, names=['t', 'x', 'y', 'z'])
            for _, row in traj_df.iterrows():
                dist = calculate_distance_3d((row['x'], row['y'], row['z']), spoofer_ecef)
                distances.append(dist)
        except Exception:
            sys.exit(1)
    elif args.victim_lat is not None:
        victim_ecef = latlon_to_ecef(args.victim_lat, args.victim_lon, args.victim_alt)
        dist = calculate_distance_3d(victim_ecef, spoofer_ecef)
        distances = [dist, dist]
    else:
        distances = [args.max_range, args.max_range]

    power_factors = []
    ref_dist = max(args.max_range / 2.0, 1.0) 
    for d in distances:
        if d > args.max_range:
            power_factors.append(0.0)
        else:
            d = max(d, 2.0)
            scale = args.spoofer_power * (ref_dist / d)
            if scale > args.spoofer_max_scale: scale = args.spoofer_max_scale
            power_factors.append(scale)

    xp = np.linspace(0, total_samples, len(power_factors))
    fp = power_factors

    bytes_per_sec = args.samplerate * 2 
    start_byte_idx = int(args.delay_seconds * bytes_per_sec)
    fade_bytes = int(args.fade_duration * bytes_per_sec)

    processed_bytes = 0
    
    with open(args.legit_file, 'rb') as f_legit, \
         open(args.spoofer_file, 'rb') as f_spoofer, \
         open(args.output_file, 'wb') as f_out:
        
        while processed_bytes < total_bytes:
            raw_legit = f_legit.read(CHUNK_SIZE)
            raw_spoofer = f_spoofer.read(CHUNK_SIZE)
            
            if not raw_legit or not raw_spoofer: break
                
            chunk_legit = np.frombuffer(raw_legit, dtype=np.int8).astype(np.float32)
            chunk_spoofer = np.frombuffer(raw_spoofer, dtype=np.int8).astype(np.float32)
            
            current_chunk_len = len(chunk_legit)
            if len(chunk_spoofer) < current_chunk_len:
                chunk_spoofer = np.pad(chunk_spoofer, (0, current_chunk_len - len(chunk_spoofer)))
            
            chunk_indices = np.arange(processed_bytes, processed_bytes + current_chunk_len)
            
            spoofer_env_factor = np.zeros(current_chunk_len, dtype=np.float32)
            chunk_start = processed_bytes
            env_power_chunk = np.interp(chunk_indices, xp, fp).astype(np.float32)
            
            overlap_start = max(chunk_start, start_byte_idx)
            overlap_end = chunk_start + current_chunk_len 
            
            if overlap_start < overlap_end:
                l_start = overlap_start - chunk_start
                spoofer_env_factor[l_start:] = 1.0
                
                fi_start = start_byte_idx
                fi_end = start_byte_idx + fade_bytes
                c_fi_start = max(chunk_start, fi_start)
                c_fi_end = min(chunk_start + current_chunk_len, fi_end)
                
                if c_fi_start < c_fi_end:
                    lf_start = c_fi_start - chunk_start
                    lf_end = c_fi_end - chunk_start
                    
                    curr_pos = chunk_indices[lf_start:lf_end]
                    ramp = (curr_pos - fi_start) / fade_bytes
                    ramp = np.clip(ramp, 0.0, 1.0)
                    spoofer_env_factor[lf_start:lf_end] = ramp

            mix_chunk = (chunk_legit * args.legit_scale) 
            
            mix_chunk += (chunk_spoofer * env_power_chunk * spoofer_env_factor)
            
            if args.noise_std > 0.0:
                noise = np.random.normal(0.0, args.noise_std, current_chunk_len).astype(np.float32)
                mix_chunk += noise
            
            mix_chunk = np.clip(mix_chunk, -128.0, 127.0)
            output_chunk = (mix_chunk.astype(np.int16) + 128).astype(np.uint8)
            f_out.write(output_chunk.tobytes())
            
            processed_bytes += current_chunk_len
            progress = (processed_bytes / total_bytes) * 100
            print(f"\r   Postęp: {progress:.1f}%", end="")
            
    print("\n--- GOTOWE ---")

if __name__ == "__main__":
    main()