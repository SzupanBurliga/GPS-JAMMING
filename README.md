# GPS JAMMING - System detekcji i lokalizacji zakłóceń GPS

System do analizy sygnałów GPS, detekcji zakłóceń oraz lokalizacji źródeł jammerów metodą triangulacji RSSI.

## Wymagania systemowe

- **System operacyjny**: Linux (testowane na Ubuntu 22.04)
- **Python**: 3.10+
- **RAM**: minimum 8GB
- **Kompilator C**: gcc, make

## Instalacja

### 1. Pobranie projektu
```bash
git clone <repository-url>
cd GPS-JAMMING
```

### 2. Utworzenie środowiska wirtualnego
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Instalacja zależności
```bash
pip install -r requirements.txt
```

Lub ręcznie:
```bash
pip install --upgrade pip
pip install PySide6==6.5.2 PySide6-QtWebEngine==6.5.2
pip install numpy pandas scipy matplotlib haversine scikit-learn
```

### 4. Kompilacja backendu C
```bash
# Instalacja zależności dla Ubuntu:
sudo apt install build-essential libfftw3-dev libusb-1.0-0-dev libfec-dev 

cd GpsJammerApp/backend/bin
make clean && make
```

### 5. (Opcjonalne) Instalacja gps-sdr-sim do symulacji
```bash
cd simulate
git clone https://github.com/osqzss/gps-sdr-sim.git
cd gps-sdr-sim
make
cd ../..
```

## Uruchomienie

### Główna aplikacja GUI
```bash
python GpsJammerApp/app.py
```

### Generator symulacji GPS
```bash
python simulate/frontend/gnss_frontend.py
```

## Funkcjonalności

### Analiza sygnałów GPS
- Wczytywanie plików I/Q (format uint8, rtl-sdr)
- Analiza mocy sygnału w czasie rzeczywistym
- Detekcja zakłóceń jammingu
- Dekodowanie pozycji GPS (lat, lon, wysokość)

### Triangulacja źródła jammera
- Metoda RSSI (2-3 anteny)
- Wyświetlanie pozycji jammera na mapie
- Obliczanie odległości od każdej anteny
- Używa ostatniej znanej pozycji GPS przed jammingiem

### Wizualizacja
- Mapa interaktywna (Leaflet + OpenStreetMap)
- Marker pozycji jammera
- Okręgi zasięgu od każdej anteny
- Panel wyników z danymi w czasie rzeczywistym

### Symulacje
- Generowanie czystych sygnałów GPS
- Dodawanie różnych typów jammerów (CW, sweep, pulsed)
- Symulacja ruchu (trajektorie)
- Miksowanie sygnału GPS z jammerem

## Wykorzystanie

### Przykład 1: Analiza nagrania z 3 anten
```bash
# 1. Wybierz 3 pliki .bin z nagrań (test1.bin, test2.bin, test3.bin)
# 2. Kliknij "Rozpocznij Analizę"
# 3. System automatycznie:
#    - Wykrywa jamming
#    - Pobiera ostatnią pozycję GPS przed jammingiem
#    - Wykonuje triangulację RSSI
#    - Wyświetla pozycję jammera na mapie
```

### Przykład 2: Kalibracja progu detekcji
```bash
python GpsJammerApp/app/checkIfJamming.py nagranie.bin --kalibruj
# Zwraca sugerowany próg mocy dla tego pliku
```

### Przykład 3: Generowanie testowych danych
```bash
# Uruchom frontend symulacji
python simulate/frontend/gnss_frontend.py

# Wybierz tryb "Jammer", ustaw parametry i wygeneruj plik
```

## Struktura projektu

```
GPS-JAMMING/
├── GpsJammerApp/           # Główna aplikacja
│   ├── app.py             # Punkt wejścia
│   ├── app/               # Moduły aplikacji
│   │   ├── ui_mainwindow.py
│   │   ├── worker.py
│   │   ├── checkIfJamming.py
│   │   └── config.py
│   ├── backend/           # Backend HTTP C
│   └── resources/         # Zasoby (HTML, CSS)
├── simulate/              # Narzędzia symulacyjne
│   └── frontend/          # GUI symulacji
├── skrypty/               # Skrypty analizy
│   ├── triangulateRSSI.py
│   ├── triangulateTDOA.py
│   └── widmo_plot.py
└── requirements.txt       # Zależności Python
```

## Konfiguracja

### Domyślne ustawienia mapy
Edytuj [`GpsJammerApp/app/config.py`](GpsJammerApp/app/config.py):
```python
LAT = 50.06143   # Szerokość geograficzna (Kraków)
LNG = 19.93658   # Długość geograficzna
ZOOM = 13        # Poziom zoomu
```

### Pozycje anten (triangulacja)
Kliknij "⚙️ Ustawienia" w GUI lub edytuj w [`skrypty/triangulateRSSI.py`](skrypty/triangulateRSSI.py):
```python
antenna_positions_meters = [
    [0.0, 0.0],   # Antena 1 (punkt odniesienia)
    [0.5, 0.0],   # Antena 2 (0.5m na wschód)
    [0.0, 0.5]    # Antena 3 (0.5m na północ)
]
```

## Skrypty CLI

### Detekcja jammingu
```bash
python GpsJammerApp/app/checkIfJamming.py plik.bin 5000.0
# Zwraca: [próbka_początek, próbka_koniec] jeśli wykryto jamming
```

### Analiza widma
```bash
python skrypty/widmo_plot.py plik.bin --fs 2048000 --fc 1575420000
# Generuje wykres PSD i zapisuje do PNG
```

### Triangulacja RSSI
```bash
python skrypty/triangulateRSSI.py
# Wymaga edycji ścieżek do plików w skrypcie
```

### Triangulacja TDOA
```bash
python skrypty/triangulateTDOA.py
# Metoda różnicy czasu dotarcia (wymaga synchronizacji)
```

## Rozwiązywanie problemów

### Błąd importu PySide6
```bash
pip uninstall PySide6 PySide6-QtWebEngine
pip install PySide6==6.5.2 PySide6-QtWebEngine==6.5.2
```

### Mapa się nie ładuje
- Sprawdź połączenie internetowe
- Upewnij się, że QtWebEngine jest zainstalowane
- Sprawdź czy [`GpsJammerApp/resources/map_template.html`](GpsJammerApp/resources/map_template.html) istnieje

### Backend się nie kompiluje
```bash
cd GpsJammerApp/backend/bin
make clean
make
# Jeśli brakuje bibliotek:
sudo apt install build-essential libfftw3-dev libusb-1.0-0-dev libfec-dev 
```

### Błędy triangulacji
- Sprawdź format plików (uint8 I/Q)
- Upewnij się, że pozycje anten są poprawnie ustawione
- Sprawdź czy pliki zawierają jamming (użyj kalibracji)

## Format danych wejściowych

Aplikacja oczekuje plików w formacie rtl-sdr:
- **Format**: uint8
- **Układ**: I/Q interleaved (I₁, Q₁, I₂, Q₂, ...)
- **Częstotliwość próbkowania**: 2.048 MHz (domyślnie)
- **Rozszerzenie**: .bin

## Dane wyjściowe

### Panel "Wyniki Analizy - przykład outputu"
Znaleziono jamming

📍 TRIANGULACJA ZAKOŃCZONA:
  🎯 Pozycja jammera: 49.99999726°N, 19.90371989°E
  📏 Odległości od anten: ['8.6m', '8.6m', '8.6m']
  🔧 Metoda: 3-antenna triangulation
  📍 Pozycja ref: 49.999999, 19.903713 (próbka 114327552)
```

### Mapa
- Czerwony marker JAM - pozycja wykrytego jammera
- Czerwone okręgi - szacowana odległość od każdej z anten
- Popup z informacjami o lokalizacji i odległościach

## Uwagi

- System wymaga minimum 2 plików (2 anteny) do triangulacji
- Najlepsze wyniki przy 3 antenach
- Pozycje anten powinny tworzyć trójkąt (nie być współliniowe)
- Backend HTTP musi być skompilowany przed uruchomieniem
- Pliki symulacyjne wymagają gps-sdr-sim i plików efemeryd BRDC

## Autor

Projekt dyplomowy - 2024

## Licencja

Backend C (gnssdec): GNU GPL v2 (Copyright 2014 Taro Suzuki)
Reszta projektu: do uzgodnienia
