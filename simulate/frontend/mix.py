import numpy as np
import os

# --- PARAMETRY DO USTAWIEΝIA ---

# Nazwy plików wejściowych
GPS_FILENAME = "test.bin"   # ⬅️ ZMIEŃ na nazwę Twojego pliku GPS
JAMMER_FILENAME = "test_jammer.bin" # ⬅️ ZMIEŃ na nazwę Twojego pliku z jammerem

# Nazwa pliku wyjściowego
OUTPUT_FILENAME = "gps_z_jammerem.bin"

# --- SKRYPT MIESZAJĄCY ---

print("--- Skrypt do wstrzykiwania jammera ---")

# Sprawdzenie, czy pliki istnieją
if not os.path.exists(GPS_FILENAME):
    print(f"❌ BŁĄD: Plik GPS '{GPS_FILENAME}' nie został znaleziony!")
    exit()
if not os.path.exists(JAMMER_FILENAME):
    print(f"❌ BŁĄD: Plik jammera '{JAMMER_FILENAME}' nie został znaleziony!")
    exit()

# 1. Wczytanie plików binarnych jako tablice 8-bitowych liczb całkowitych
print(f"🛰️  Wczytywanie sygnału GPS z pliku: {GPS_FILENAME}")
gps_signal = np.fromfile(GPS_FILENAME, dtype=np.int8)

print(f"📡 Wczytywanie sygnału jammera z pliku: {JAMMER_FILENAME}")
jammer_signal = np.fromfile(JAMMER_FILENAME, dtype=np.int8)

# 2. Dopasowanie długości sygnału jammera do sygnału GPS
# Jeśli jammer jest krótszy, zostanie zapętlony (powtórzony) tyle razy,
# ile potrzeba, aby pokryć całą długość sygnału GPS.
if len(jammer_signal) < len(gps_signal):
    print(" INFO: Sygnał jammera jest krótszy. Zapętlam go, aby dopasować długość...")
    num_repeats = int(np.ceil(len(gps_signal) / len(jammer_signal)))
    tiled_jammer = np.tile(jammer_signal, num_repeats)
    # Przycinamy zapętloną tablicę do dokładnej długości sygnału GPS
    jammer_signal_full = tiled_jammer[:len(gps_signal)]
else:
    # Jeśli jammer jest dłuższy, przycinamy go
    jammer_signal_full = jammer_signal[:len(gps_signal)]

print("🎚️  Mieszanie sygnałów (dodawanie próbek)...")

# 3. Sumowanie sygnałów
# WAŻNE: Najpierw konwertujemy próbki na typ o większym zakresie (int16),
# aby uniknąć błędów przepełnienia przy dodawaniu (np. 100 + 100 = 200, co nie mieści się w int8).
combined_signal_int16 = gps_signal.astype(np.int16) + jammer_signal_full.astype(np.int16)

# 4. Normalizacja i zapis do pliku
# Po dodaniu, wartości mogą wykraczać poza zakres int8 [-128, 127].
# "Przycinamy" je do tego zakresu, aby uniknąć błędów.
combined_signal_clipped = np.clip(combined_signal_int16, -127, 127)

# Konwertujemy z powrotem do formatu int8 i zapisujemy do pliku
final_signal = combined_signal_clipped.astype(np.int8)
final_signal.tofile(OUTPUT_FILENAME)

print(f"\n✅ Gotowe! Zmiksowany sygnał został zapisany w pliku: {OUTPUT_FILENAME}")