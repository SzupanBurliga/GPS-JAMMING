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

### 2. Automatyczna instalacja (zalecane)
```bash
chmod +x install.sh
./install.sh
```

Lub ręczna instalacja:

### 2. Utworzenie środowiska wirtualnego
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Instalacja zależności
```bash
pip install -r requirements.txt
```

### 4. Kompilacja backendu HTTP C
```bash
cd GpsJammerApp/backendhttp
make
cd ../..
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
source .venv/bin/activate  # Aktywuj środowisko wirtualne
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
- Pasek postępu pokazujący rzeczywisty postęp analizy
- Wyświetlanie danych w formacie `[czas, lat, lon, próbka]`

### Triangulacja źródła jammera
- Metoda RSSI (2-3 anteny)
- Wyświetlanie pozycji jammera na mapie
- Obliczanie odległości od każdej anteny
- Używa ostatniej znanej pozycji GPS przed jammingiem
- Automatyczna triangulacja po zakończeniu analizy

### Wizualizacja
- Mapa interaktywna (Leaflet + OpenStreetMap)
- Marker pozycji jammera (JAM)
- Czerwone okręgi zasięgu od każdej anteny
- Panel wyników z danymi w czasie rzeczywistym (40% szerokości)
- Mapa zajmuje 60% szerokości okna
- Zoom na pozycję jammera po triangulacji

### Nagrywanie sygnałów
- Nagrywanie z RTL-SDR
- Obsługa BiasT (włączanie/wyłączanie)
- Konfiguracja częstotliwości, gain, częstotliwości próbkowania
- Nagrywanie wielu plików z różnych anten

### Symulacje
- Generowanie czystych sygnałów GPS
- Dodawanie różnych typów jammerów (CW, sweep, pulsed)
- Symulacja ruchu (trajektorie)
- Miksowanie sygnału GPS z jammerem

## Wykorzystanie

### Przykład 1: Analiza nagrania z 3 anten
1. Uruchom aplikację: `python GpsJammerApp/app.py`
2. Wybierz 3 pliki .bin z nagrań (test1.bin, test2.bin, test3.bin)
3. Kliknij "🔍 Rozpocznij Analizę"
4. System automatycznie:
   - Wykrywa jamming
   - Pokazuje postęp analizy w czasie rzeczywistym
   - Pobiera ostatnią pozycję GPS przed jammingiem
   - Wykonuje triangulację RSSI
   - Wyświetla pozycję jammera na mapie

### Przykład 2: Kalibracja progu detekcji
```bash
python GpsJammerApp/app/checkIfJamming.py nagranie.bin --kalibruj
# Zwraca sugerowany próg mocy dla tego pliku
```

### Przykład 3: Nagrywanie sygnału
1. Podłącz RTL-SDR do USB
2. W aplikacji kliknij "Nagraj pliki"
3. Skonfiguruj parametry (częstotliwość, gain, czas nagrywania)
4. Opcjonalnie włącz BiasT dla aktywnej anteny
5. Kliknij "Start Recording"

### Przykład 4: Generowanie testowych danych
```bash
python simulate/frontend/gnss_frontend.py
# Wybierz tryb "Jammer", ustaw parametry i wygeneruj plik
```

## Struktura projektu

```
GPS-JAMMING/
├── GpsJammerApp/           # Główna aplikacja
│   ├── app.py             # Punkt wejścia
│   ├── requirements.txt   # Zależności Python
│   ├── app/               # Moduły aplikacji
│   │   ├── ui_mainwindow.py      # Interfejs głównego okna
│   │   ├── worker.py             # Wątek analizy GPS
│   │   ├── checkIfJamming.py     # Detekcja jammingu
│   │   ├── config.py             # Konfiguracja (LAT, LON, ZOOM)
│   │   ├── recording_dialog.py   # Dialog nagrywania
│   │   └── settings_dialog.py    # Dialog ustawień
│   ├── backendhttp/       # Backend HTTP C (gnssdec)
│   │   └── bin/
│   │       ├── gnssdec    # Skompilowany program C
│   │       └── makefile
│   └── resources/         # Zasoby (HTML, mapa)
│       └── map_template.html
├── simulate/              # Narzędzia symulacyjne
│   └── frontend/
│       ├── gnss_frontend.py      # GUI symulacji
│       └── add_jammer_and_mix.py # Miksowanie GPS+jammer
├── skrypty/               # Skrypty analizy
│   ├── triangulateRSSI.py   # Triangulacja RSSI
│   ├── triangulateTDOA.py   # Triangulacja TDOA
│   └── widmo_plot.py        # Analiza widma
├── requirements.txt       # Główne zależności Python
├── install.sh            # Skrypt instalacyjny Linux
└── README.md             # Ten plik
```

## Konfiguracja

### Domyślne ustawienia mapy
Edytuj [`GpsJammerApp/app/config.py`](GpsJammerApp/app/config.py):
```python
LAT = 50.06143   # Szerokość geograficzna (Kraków)
LNG = 19.93658   # Długość geograficzna
ZOOM = 13        # Poziom zoomu początkowego
```

### Zoom dla pozycji na żywo
W [`GpsJammerApp/app/ui_mainwindow.py`](GpsJammerApp/app/ui_mainwindow.py) znajdź funkcję `update_map_position()`:
```python
desired_zoom = 18  # 15-18 zalecane dla GPS (domyślnie 18)
```

### Pozycje anten (triangulacja)
Kliknij "⚙️ Ustawienia" w GUI i wprowadź współrzędne anten w metrach:
```python
# Domyślne pozycje (można zmienić w GUI):
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

### Triangulacja RSSI (standalone)
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
cd GpsJammerApp/backendhttp
make clean
make
# Jeśli brakuje bibliotek:
sudo apt install build-essential libfftw3-dev
```

### Błędy triangulacji
- Sprawdź format plików (uint8 I/Q)
- Upewnij się, że pozycje anten są poprawnie ustawione w GUI
- Sprawdź czy pliki zawierają jamming (użyj kalibracji)
- System wymaga minimum 2 plików do triangulacji

### Problemy z RTL-SDR
```bash
# Instalacja narzędzi RTL-SDR:
sudo apt install rtl-sdr

# Test urządzenia:
rtl_test

# Jeśli błąd uprawnień:
sudo usermod -a -G plugdev $USER
# Następnie wyloguj się i zaloguj ponownie
```

## Format danych wejściowych

Aplikacja oczekuje plików w formacie rtl-sdr:
- **Format**: uint8
- **Układ**: I/Q interleaved (I₁, Q₁, I₂, Q₂, ...)
- **Częstotliwość próbkowania**: 2.048 MHz (domyślnie)
- **Rozszerzenie**: .bin
- **Rozmiar próbki**: 2 bajty (1 bajt I + 1 bajt Q)

## Dane wyjściowe

### Panel "Wyniki Analizy"
Podczas analizy:
```
[5.2, 50.061430, 19.936580, 122880000]
[6.1, 50.061435, 19.936582, 163840000]
[7.3, 50.061440, 19.936585, 204800000]
```

Po zakończeniu:
```
Znaleziono jamming [122880000, 163840000]

📍 TRIANGULACJA ZAKOŃCZONA:
  🎯 Pozycja jammera: 49.99999726°N, 19.90371989°E
  📏 Odległości od anten: ['8.6m', '8.6m', '8.6m']
  🔧 Metoda: 3-antenna triangulation
  📍 Pozycja ref: 49.999999, 19.903713 (próbka 114327552)
```

### Mapa
- **Czerwony marker JAM** - pozycja wykrytego jammera
- **Czerwone okręgi** - zasięgi od każdej anteny
- **Niebieski marker** - pozycje GPS w czasie rzeczywistym
- **Popup** - informacje o lokalizacji i odległościach
- **Automatyczny zoom** - na pozycję jammera po triangulacji

## Systemy satelitarne

Aplikacja obsługuje:
- 🇺🇸 **GPS L1** (1575.42 MHz, 2.048 MHz sampling)
- 🇷🇺 **GLONASS G1** (1602.00 MHz, 10.00 MHz sampling)
- 🇪🇺 **Galileo E1** (1575.42 MHz, 2.048 MHz sampling)

Wybór systemu przez przyciski w GUI.

## Uwagi techniczne

- System wymaga minimum 2 plików (2 anteny) do triangulacji
- Najlepsze wyniki przy 3 antenach w konfiguracji trójkąta
- Pozycje anten powinny tworzyć trójkąt (nie być współliniowe)
- Backend HTTP (`gnssdec`) musi być skompilowany przed uruchomieniem
- Pliki symulacyjne wymagają gps-sdr-sim i plików efemeryd BRDC
- Pasek postępu oblicza % na podstawie elapsed_time i rozmiaru pliku
- Triangulacja wykonuje się automatycznie po wykryciu jammingu
- Wyniki triangulacji są dostępne od razu po zakończeniu analizy

## Zalecane parametry sprzętowe

### RTL-SDR
- **Gain**: 40-50 dB (dla GPS)
- **Częstotliwość**: 1575.42 MHz (GPS L1)
- **Sampling rate**: 2.048 MHz
- **BiasT**: Wymagany dla aktywnych anten GPS

### Anteny
- **Typ**: Aktywna antena GPS z LNA
- **Rozmieszczenie**: Trójkąt lub linia, min. 0.5m odstęp
- **Montaż**: Stabilny, na tej samej wysokości
- **Zasilanie**: Przez BiasT (3.3V lub 5V)

## Wydajność

- **Analiza pliku 100MB**: ~50-60 sekund
- **Triangulacja 3 anten**: ~2-5 sekund
- **Zużycie RAM**: 500MB-2GB (zależnie od rozmiaru pliku)
- **Zużycie CPU**: 1-2 rdzenie podczas analizy

## Autor

Projekt dyplomowy - 2024

## Licencja

- **Backend C (gnssdec)**: GNU GPL v2 (Copyright 2014 Taro Suzuki)
- **Reszta projektu**: Do uzgodnienia

## Kontakt i wsparcie

W razie problemów sprawdź:
1. Czy środowisko wirtualne jest aktywne
2. Czy wszystkie zależności są zainstalowane
3. Czy backend jest skompilowany
4. Logi w terminalu podczas uruchomienia

## Znane ograniczenia

- Działa tylko na Linux
- Wymaga połączenia internetowego (mapa)
- Triangulacja TDOA wymaga precyzyjnej synchronizacji czasowej
- Symulacje wymagają zewnętrznych plików efemeryd