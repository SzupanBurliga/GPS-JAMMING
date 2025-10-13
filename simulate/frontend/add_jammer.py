#!/usr/bin/env python3
"""
mix_jammer_simple_v2.py — nakładanie jammera (noise/tone) na IQ int8 (I,Q interleaved).

Nowości:
 - jammer działa tylko gdy odległość <= radius
 - kilka modeli tłumienia: linear, inverse, inverse-square
 - opcjonalny miękki edge (cosine taper) na końcu promienia
 - poprawki bezpieczeństwa/normalizacji

Przykłady:
  python mix_jammer_simple_v2.py --iq gpssim.bin --out gpssim_jammed.bin --type noise --strength 0.5
  python mix_jammer_simple_v2.py --iq gpssim.bin --out gpssim_jammed.bin --type tone --strength 0.3 --freq 10000 --fs 2048000
  python mix_jammer_simple_v2.py --iq gpssim.bin --out gpssim_jammed.bin --type noise --traj traj.csv \
        --jam-lat 39.087822 --jam-lon -94.577656 --jam-alt 100 --radius 200 --falloff inverse-square --edge 20

Uwaga o traj.csv:
 - skrypt przyjmuje, że traj.csv zawiera wiersze: time(s) X(m) Y(m) Z(m)
 - X,Y,Z powinny być w tym samym układzie współrzędnych co wynik funkcji lla_to_ecef (czyli ECEF),
   albo musisz uprzednio zapisać traj w ECEF. Jeśli Twoje traj to ENU lub lokalne współrzędne, skonwertuj je do ECEF.
"""
import argparse
import os
import math
import numpy as np

# --------- WGS84 helper (LLA -> ECEF) ----------
def lla_to_ecef(lat_deg, lon_deg, h_m):
    a = 6378137.0
    f = 1.0 / 298.257223563
    e2 = f * (2 - f)
    lat = math.radians(lat_deg)
    lon = math.radians(lon_deg)
    sinl = math.sin(lat); cosl = math.cos(lat)
    sinλ = math.sin(lon); cosλ = math.cos(lon)
    N = a / math.sqrt(1 - e2 * sinl * sinl)
    X = (N + h_m) * cosl * cosλ
    Y = (N + h_m) * cosl * sinλ
    Z = (N * (1 - e2) + h_m) * sinl
    return np.array([X, Y, Z], dtype=float)

# --------- traj loader / interpolator ----------
def read_traj(traj_path):
    """Czyta traj.csv w formacie: time(s), X(m), Y(m), Z(m) lub z komentarzem # naglowek"""
    times=[]; X=[]; Y=[]; Z=[]
    with open(traj_path, "r", encoding="utf-8") as f:
        for line in f:
            line=line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.replace(',', ' ').split()
            if len(parts) < 4:
                continue
            times.append(float(parts[0])); X.append(float(parts[1])); Y.append(float(parts[2])); Z.append(float(parts[3]))
    if len(times)==0:
        raise RuntimeError("traj empty or wrong format")
    return np.array(times), np.array(X), np.array(Y), np.array(Z)

def interp_positions(times, X, Y, Z, sample_times):
    """Prosta liniowa interpolacja (bez scipy)"""
    xs = np.interp(sample_times, times, X, left=X[0], right=X[-1])
    ys = np.interp(sample_times, times, Y, left=Y[0], right=Y[-1])
    zs = np.interp(sample_times, times, Z, left=Z[0], right=Z[-1])
    return xs, ys, zs

# --------- falloff functions ----------
def falloff_linear(d, radius):
    """f(d) = 1 - d/r (clipped)"""
    r = np.clip(1.0 - d / radius, 0.0, 1.0)
    return r

def falloff_inverse(d, radius, eps=1e-6):
    """f(d) ~ 1 / (1 + (d/d0)) normalized so f(0)=1 and f(radius)=0
       We'll map d in [0, radius] -> [1, 0] via 1/(1 + alpha*d) and normalize.
       Choose alpha so f(radius) ~= 0.01 (przybliżenie) -> alpha = (1/0.01 - 1)/radius
    """
    if radius <= 0:
        return np.zeros_like(d)
    alpha = (1.0/0.01 - 1.0) / radius
    v = 1.0 / (1.0 + alpha * d)
    # normalize to 0..1 over [0, radius]
    v = (v - v_at_radius(alpha, radius)) / (1.0 - v_at_radius(alpha, radius) + 1e-12)
    return np.clip(v, 0.0, 1.0)

def v_at_radius(alpha, radius):
    return 1.0 / (1.0 + alpha * radius)

def falloff_inverse_square(d, radius, eps=1e-12):
    """f(d) ~ 1 / (1 + (d/d0)^2) normalized similarly to inverse"""
    if radius <= 0:
        return np.zeros_like(d)
    # choose beta so value at radius is small (0.01)
    beta = (1.0/0.01 - 1.0)
    v = 1.0 / (1.0 + beta * (d / radius)**2)
    v = (v - v_at_radius_sq(beta)) / (1.0 - v_at_radius_sq(beta) + 1e-12)
    return np.clip(v, 0.0, 1.0)

def v_at_radius_sq(beta):
    return 1.0 / (1.0 + beta)

# cosine taper near the edge: for d in [radius-edge, radius] multiply by 0..1 (smooth)
def cosine_edge_mask(d, radius, edge):
    if edge <= 0:
        return np.ones_like(d)
    mask = np.ones_like(d)
    start = radius - edge
    # for d < start => 1; for d>radius => 0; for start<=d<=radius => cos taper
    idx = (d >= start) & (d <= radius)
    x = (d[idx] - start) / (edge + 1e-12)  # 0..1
    mask[idx] = 0.5 * (1.0 + np.cos(math.pi * (1.0 - x)))  # goes from 1->0 smoothly
    mask[d > radius] = 0.0
    return mask

# --------- main ----------
def main():
    p = argparse.ArgumentParser()
    p.add_argument("--iq", required=True, help="Input IQ .bin (int8 interleaved I,Q)")
    p.add_argument("--out", required=True, help="Output jammed file")
    p.add_argument("--fs", type=float, default=2048000.0, help="Sample rate (Hz)")
    p.add_argument("--type", choices=["noise","tone"], default="noise", help="Typ jammera")
    p.add_argument("--strength", type=float, default=0.4, help="Global peak strength (0..1) maks 1.0")
    p.add_argument("--freq", type=float, default=0.0, help="dla tone: offset freq [Hz]")
    p.add_argument("--traj", help="Opcjonalny traj.csv (time(s), X(m), Y(m), Z(m)) — X,Y,Z w metrach (ECEF)")
    p.add_argument("--jam-lat", type=float, help="Jammera lat (deg) — jeśli podajesz traj, wymagane")
    p.add_argument("--jam-lon", type=float, help="Jammera lon (deg)")
    p.add_argument("--jam-alt", type=float, default=0.0, help="Jammera alt (m)")
    p.add_argument("--radius", type=float, default=0.0, help="Jeśli >0: jammer działa tylko w promieniu [m]")
    p.add_argument("--falloff", choices=["linear","inverse","inverse-square"], default="linear",
                   help="Model tłumienia mocy w funkcji odległości")
    p.add_argument("--edge", type=float, default=0.0,
                   help="Szerokość 'miękkiej krawędzi' (m) przy końcu radius -> cosine taper")
    args = p.parse_args()

    if not os.path.isfile(args.iq):
        raise SystemExit("Input IQ file not found.")

    filesize = os.path.getsize(args.iq)
    if filesize % 2 != 0:
        print("Warning: file size not even — expecting interleaved I/Q int8")

    n_samples = filesize // 2
    duration = n_samples / args.fs
    print(f"Input samples: {n_samples}, duration ~ {duration:.2f}s")

    raw = np.fromfile(args.iq, dtype=np.int8, count=n_samples*2)
    I = raw[0::2].astype(np.float32) / 128.0
    Q = raw[1::2].astype(np.float32) / 128.0
    rx = I + 1j*Q

    rng = np.random.default_rng(123456)
    if args.type == "noise":
        jam = (rng.standard_normal(n_samples) + 1j * rng.standard_normal(n_samples)).astype(np.complex64)
    else:
        t = np.arange(n_samples) / args.fs
        jam = np.exp(1j * 2.0 * math.pi * args.freq * t).astype(np.complex64)

    # normalize jammer to unit RMS
    jam = jam / (np.sqrt(np.mean(np.abs(jam)**2)) + 1e-12)

    # compute per-sample amplitude mask
    if args.traj and args.jam_lat is not None and args.jam_lon is not None and args.radius > 0.0:
        times, X, Y, Z = read_traj(args.traj)
        sample_times = np.arange(n_samples) / args.fs
        rx_x, rx_y, rx_z = interp_positions(times, X, Y, Z, sample_times)
        jam_ecef = lla_to_ecef(args.jam_lat, args.jam_lon, args.jam_alt)
        dists = np.sqrt((rx_x - jam_ecef[0])**2 + (rx_y - jam_ecef[1])**2 + (rx_z - jam_ecef[2])**2)

        # base falloff in 0..1 for d in [0, radius]. Outside radius -> 0
        if args.falloff == "linear":
            base = falloff_linear(dists, args.radius)
        elif args.falloff == "inverse":
            base = falloff_inverse(dists, args.radius)
        else:  # inverse-square
            base = falloff_inverse_square(dists, args.radius)

        # apply cosine edge taper to smooth at edges
        edge_mask = cosine_edge_mask(dists, args.radius, args.edge)
        amp = base * edge_mask * args.strength
        print(f"Using distance-based mask from trajectory (radius {args.radius:.1f} m, falloff {args.falloff}, edge {args.edge} m)")
    else:
        amp = np.full(n_samples, args.strength, dtype=np.float32)
        if args.traj:
            print("traj provided but jam-lat/jam-lon/radius missing — ignoring traj masking.")
        print(f"Using constant strength = {args.strength}")

    # apply amplitude and mix
    jam_scaled = jam * amp
    mixed = rx + jam_scaled

    # avoid clipping: scale if necessary to fit [-127..127] after mapping to 127
    peak = np.max(np.abs(mixed))
    if peak > 0.999:
        mixed = mixed / (peak + 1e-12) * 0.999

    I_out = np.round(mixed.real * 127.0).astype(np.int8)
    Q_out = np.round(mixed.imag * 127.0).astype(np.int8)
    out_interleaved = np.empty(I_out.size * 2, dtype=np.int8)
    out_interleaved[0::2] = I_out
    out_interleaved[1::2] = Q_out

    out_dir = os.path.dirname(args.out) or "."
    os.makedirs(out_dir, exist_ok=True)
    with open(args.out, "wb") as f:
        out_interleaved.tofile(f)

    print("Wrote jammed file:", args.out)

if __name__ == "__main__":
    main()
