#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
from pathlib import Path
import numpy as np
import matplotlib
import matplotlib.pyplot as plt

def compute_psd_iq_uint8(path, fs, nfft=131072, overlap=0.5, max_segments=None):
    """
    Liczy średnie widmo mocy (PSD) dla pliku rtl_sdr:
    - format: I/Q interleaved, uint8 (0..255), offset 128
    - przetwarzanie blokami (Welch), okno Hann, overlap
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)

    mm = np.memmap(path, dtype=np.uint8, mode='r')
    total_bytes = mm.size
    if total_bytes < 2*nfft:
        # mały plik — wczytaj na raz i doraźnie dopaduj
        data = np.asarray(mm, dtype=np.float32) - 128.0
        if data.size % 2 != 0:
            data = data[:-1]
        I = data[0::2]; Q = data[1::2]
        x = (I + 1j*Q)
        # dopaduj do nfft
        if x.size < nfft:
            tmp = np.zeros(nfft, dtype=np.complex64)
            tmp[:x.size] = x
            x = tmp
        win = np.hanning(nfft).astype(np.float32)
        X = np.fft.fft(x[:nfft] * win, n=nfft)
        Pxx = (np.abs(X)**2) / (win**2).sum()
        return Pxx, 1

    nsamp = total_bytes // 2  # I/Q => 2 bajty na próbkę zespoloną
    seg = nfft
    step = max(1, int(seg * (1.0 - overlap)))

    # liczba pełnych segmentów
    n_segments = (nsamp - seg) // step + 1
    if max_segments is not None:
        n_segments = min(n_segments, max_segments)

    win = np.hanning(seg).astype(np.float32)
    win_power = (win**2).sum()

    Pxx_acc = None
    for k in range(n_segments):
        i0 = k * step
        b0 = 2 * i0           # bajt startu (bo I/Q)
        b1 = 2 * (i0 + seg)   # bajt końca segmentu
        block_u8 = np.asarray(mm[b0:b1], dtype=np.float32) - 128.0
        # rozdziel I/Q
        I = block_u8[0::2]; Q = block_u8[1::2]
        x = (I + 1j*Q)
        x = x - np.mean(x)         # usuń DC w segmencie
        xw = x * win
        X = np.fft.fft(xw, n=seg)
        Pxx = (np.abs(X)**2) / win_power
        if Pxx_acc is None:
            Pxx_acc = Pxx
        else:
            Pxx_acc += Pxx

    Pxx_mean = Pxx_acc / n_segments
    return Pxx_mean, n_segments

def main():
    ap = argparse.ArgumentParser(description="Widmo/PSD dla pliku rtl_sdr (I/Q uint8).")
    ap.add_argument("input", help="Plik wejściowy z rtl_sdr (uint8, I/Q interleaved).")
    ap.add_argument("--fs", type=float, default=2_048_000.0,
                    help="Częstotliwość próbkowania w Hz (domyślnie 2.048e6).")
    ap.add_argument("--fc", type=float, default=None,
                    help="Częstotliwość strojeniowa w Hz (opcjonalnie, tylko do podpisu).")
    ap.add_argument("--nfft", type=int, default=131072, help="Długość FFT/segmentu (potęga 2).")
    ap.add_argument("--overlap", type=float, default=0.5, help="Nakładanie segmentów (0..0.9).")
    ap.add_argument("--max-segments", type=int, default=None,
                    help="Ogranicz liczbę segmentów (szybsze działanie przy bardzo dużych plikach).")
    ap.add_argument("--png", type=str, default="widmo_gps.png", help="Plik wyjściowy PNG.")
    ap.add_argument("--title", type=str, default=None, help="Tytuł wykresu (opcjonalnie).")
    args = ap.parse_args()

    # Liczenie PSD
    Pxx, nseg = compute_psd_iq_uint8(args.input, args.fs, args.nfft, args.overlap, args.max_segments)
    # Przesunięcie do -Fs/2..+Fs/2
    Pxx = np.fft.fftshift(Pxx)
    f = np.fft.fftshift(np.fft.fftfreq(args.nfft, d=1.0/args.fs))

    # dB
    Pxx_dB = 10.0 * np.log10(Pxx + 1e-20)

    # Rysunek
    plt.figure(figsize=(11, 5))
    plt.plot(f, Pxx_dB, linewidth=0.9)
    plt.xlabel("Częstotliwość [Hz] (baseband)")
    plt.ylabel("PSD [dB]")
    tt = args.title or f"Widmo/PSD rtl_sdr — nfft={args.nfft}, segmentów={nseg}"
    if args.fc:
        tt += f" (fc={args.fc/1e6:.6f} MHz)"
    plt.title(tt)
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(args.png, dpi=150)
    try:
        plt.show()
    except Exception:
        pass

    print(f"[OK] Zapisano: {Path(args.png).resolve()}")
    print(f"Fs={args.fs:.3f} Hz, nfft={args.nfft}, segmenty={nseg}")

if __name__ == "__main__":
    main()
