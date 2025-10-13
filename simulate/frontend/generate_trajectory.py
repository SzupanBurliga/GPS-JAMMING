import argparse
import csv
import math

# WGS-84 constants
A = 6378137.0                     # semi-major axis [m]
F = 1 / 298.257223563             # flattening
E2 = F * (2.0 - F)                # eccentricity squared

def lla_to_ecef(lat_deg: float, lon_deg: float, h_m: float):
    """Convert LLA (deg, deg, m) to ECEF (m, m, m) in WGS-84."""
    lat = math.radians(lat_deg)
    lon = math.radians(lon_deg)
    sin_lat, cos_lat = math.sin(lat), math.cos(lat)
    sin_lon, cos_lon = math.sin(lon), math.cos(lon)
    N = A / math.sqrt(1.0 - E2 * sin_lat * sin_lat)
    X = (N + h_m) * cos_lat * cos_lon
    Y = (N + h_m) * cos_lat * sin_lon
    Z = (N * (1.0 - E2) + h_m) * sin_lat
    return X, Y, Z

def linear_trajectory(start_lat, start_lon, start_alt,
                      end_lat, end_lon, end_alt,
                      duration_s, step_s, out_file):
    """
    Generates a linear LLA trajectory between start and end,
    converts each sample to ECEF and saves CSV compatible with gps-sdr-sim -u:
    # time(s), X(m), Y(m), Z(m)
    """
    if duration_s <= 0:
        raise ValueError("time must be > 0")
    if step_s <= 0:
        raise ValueError("step must be > 0")

    n_steps = int(round(duration_s / step_s))
    rows = []

    for i in range(n_steps + 1):
        t = round(i * step_s, 6)
        if i == n_steps:
            t = float(duration_s)

        frac = t / duration_s if duration_s > 0 else 0.0
        lat = start_lat + (end_lat - start_lat) * frac
        lon = start_lon + (end_lon - start_lon) * frac
        alt = start_alt + (end_alt - start_alt) * frac

        x, y, z = lla_to_ecef(lat, lon, alt)
        rows.append([f"{t:.1f}", f"{x:.3f}", f"{y:.3f}", f"{z:.3f}"])

    with open(out_file, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerows(rows)

    print(f"[generate_trajectory] Saved {len(rows)} rows to {out_file}")
    print(f"Start LLA: ({start_lat}, {start_lon}, {start_alt}) → "
          f"End LLA: ({end_lat}, {end_lon}, {end_alt}), duration={duration_s}s, step={step_s}s")
    print("Format: time(s), X(m), Y(m), Z(m) — ECEF WGS-84 (compatible with gps-sdr-sim -u)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate linear LLA trajectory and save ECEF CSV for gps-sdr-sim -u.")
    parser.add_argument("--start-lat", type=float, required=True)
    parser.add_argument("--start-lon", type=float, required=True)
    parser.add_argument("--start-alt", type=float, required=True)
    parser.add_argument("--end-lat", type=float, required=True)
    parser.add_argument("--end-lon", type=float, required=True)
    parser.add_argument("--end-alt", type=float, required=True)
    parser.add_argument("--duration", type=float, required=True, help="Total time [s]")
    parser.add_argument("--step", type=float, default=0.1, help="Sampling step [s] (0.1 s recommended)")
    parser.add_argument("--out", type=str, default="user_motion.csv")
    args = parser.parse_args()

    linear_trajectory(
        start_lat=args.start_lat,
        start_lon=args.start_lon,
        start_alt=args.start_alt,
        end_lat=args.end_lat,
        end_lon=args.end_lon,
        end_alt=args.end_alt,
        duration_s=args.duration,
        step_s=args.step,
        out_file=args.out
    )
