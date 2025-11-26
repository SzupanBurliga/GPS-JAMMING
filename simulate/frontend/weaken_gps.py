import numpy as np
import argparse

GPS_WEAKEN_SCALE = 0.125
NOISE_STD = 6.25

def weaken_gps_signal(input_file, output_file, weaken_scale=GPS_WEAKEN_SCALE):
    try:
        print(f"Wczytywanie sygnału GPS z: {input_file}")
        gps_data = np.fromfile(input_file, dtype=np.int8).astype(np.float32)
        print(f"Wczytano {len(gps_data)} próbek")
    except FileNotFoundError:
        print(f"BŁĄD: Nie znaleziono pliku GPS: {input_file}")
        exit(1)
    except Exception as e:
        print(f"BŁĄD podczas wczytywania pliku: {e}")
        exit(1)

    print(f"Osłabianie sygnału (skala: {weaken_scale * 100:.2f}%)...")
    gps_weakened = gps_data * weaken_scale

    if NOISE_STD > 0.0:
        print(f"Dodawanie szumu AWGN (sigma = {NOISE_STD})...")
        noise = np.random.normal(0.0, NOISE_STD, gps_weakened.shape[0]).astype(np.float32)
        gps_weakened += noise

    gps_weakened = np.clip(gps_weakened, -128.0, 127.0)
    final_signal_uint8 = (gps_weakened.astype(np.int16) + 128).astype(np.uint8)

    print(f"Zapisywanie osłabionego sygnału do: {output_file}")
    final_signal_uint8.tofile(output_file)
    print(f"Osłabianie zakończone. Plik zapisany: {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Osłabia sygnał GPS zgodnie z GPS_WEAKEN_SCALE."
    )
    
    parser.add_argument(
        "--input-file",
        required=True,
        help="Plik wejściowy z sygnałem GPS (np. test.bin)"
    )
    parser.add_argument(
        "--output-file",
        required=True,
        help="Plik wyjściowy z osłabionym sygnałem GPS (np. test_weakened.bin)"
    )
    parser.add_argument(
        "--weaken-scale",
        type=float,
        default=GPS_WEAKEN_SCALE,
        help=f"Współczynnik osłabienia (domyślnie: {GPS_WEAKEN_SCALE})"
    )
    
    args = parser.parse_args()
    weaken_gps_signal(args.input_file, args.output_file, args.weaken_scale)
