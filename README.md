# GPS JAMMING - System detekcji i lokalizacji zakłóceń GPS

System do analizy sygnałów GPS, detekcji zakłóceń oraz lokalizacji źródeł jammerów metodą triangulacji RSSI.

## Wymagania systemowe

- **System operacyjny**: Linux (testowane na Ubuntu 24.04.3 LTS)
- **Python**: 3.10+
- **RAM**: minimum 8GB
- **Kompilator C**: gcc, make
- **Połączenie internetowe**: wyświetlanie mapy

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

### 4. Kompilacja backendu
```bash
cd GpsJammerApp/backend/bin
make clean
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

### 6. (Opcjonalnie) Instalacja sterowników do RTL_SDR Blog v4
```bash
git clone https://github.com/rtlsdrblog/rtl-sdr-blog
cd rtl-sdr-blog
mkdir build
cd build
cmake ../ -DINSTALL_UDEV_RULES=ON
make
sudo make install
sudo cp ../rtl-sdr.rules /etc/udev/rules.d/
sudo ldconfig
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

## Najważniejsze funkcje

- Analiza mocy i wykrywanie jammingu w wątku [`GpsJammerApp/app/worker.GPSAnalysisThread`](GpsJammerApp/app/worker.py)
- Interfejs GUI i mapa Leaflet w [`GpsJammerApp/app/ui_mainwindow.MainWindow`](GpsJammerApp/app/ui_mainwindow.py)
- Panel nagrywania RTL-SDR w [`GpsJammerApp/app/recording_dialog.RecordingDialog`](GpsJammerApp/app/recording_dialog.py)
- Triangulacja RSSI oparta o [`skrypty/triangulateRSSI.triangulate_jammer_location`](skrypty/triangulateRSSI.py)
- Generator danych testowych w [`simulate/frontend/gnss_frontend.py`](simulate/frontend/gnss_frontend.py)
- Backend DSP w C: [`GpsJammerApp/backend/bin/gnssdec`](GpsJammerApp/backendhttp/bin/gnssdec)

## Jak pracować z systemem

1. Wybierz maks. 3 pliki .bin i uruchom analizę (przycisk **🔍 Rozpocznij Analizę**).
2. Po detekcji jammingu aplikacja rysuje marker **JAM** na mapie i dodaje wyniki do panelu „Wyniki analizy”.
3. Ustawienia progu mocy, pozycji anten i trybu hold znajdziesz w dialogu **⚙️ Ustawienia**.
4. Nagrywanie nowych próbek uruchomisz w **Nagraj pliki**, a symulacje w module `simulate/frontend`.

## Konfiguracja

- Startowe parametry mapy: [`GpsJammerApp/app/config.py`](GpsJammerApp/app/config.py)
- Poziom zoomu podczas śledzenia pozycji: [`GpsJammerApp/app/ui_mainwindow.update_map_position`](GpsJammerApp/app/ui_mainwindow.py)
- Domyślne pozycje anten: dialog ustawień oraz `skrypty/triangulateRSSI.py`

## Dane wejściowe i wyjściowe

- Wejście: pliki RTL-SDR (uint8, układ I/Q, 2.048 MS/s)
- Wyjście w panelu: wiersze `[czas, lat, lon, próbka]`, podsumowanie jammingu oraz sekcja **TRIANGULACJA ZAKOŃCZONA**.
- Mapa: marker **JAM** i okręgi zasięgu anten, aktualizowane JavaScriptem w [`GpsJammerApp/resources/map_template.html`](GpsJammerApp/resources/map_template.html).

## Najczęstsze problemy

- **PySide6**: przeinstaluj wersję 6.5.2 wraz z QtWebEngine.
- **Mapa**: sprawdź dostęp do Internetu i obecność `map_template.html`.
- **Backend C**: po zmianach uruchom `make clean && make` w [`GpsJammerApp/backend`](GpsJammerApp/backendhttp).
- **Triangulacja**: wymagane min. 2 pliki oraz poprawne ustawienie anten.
- **RTL-SDR**: upewnij się, że `rtl_test` działa i użytkownik jest w grupie `plugdev`.

## Struktura projektu (skrót)

- [`GpsJammerApp/app`](GpsJammerApp/app) – logika GUI, wykrywanie, triangulacja
- [`GpsJammerApp/backend`](GpsJammerApp/backendhttp) – program `gnssdec` w C
- [`simulate/frontend`](simulate/frontend) – generowanie próbek i symulacje
- [`skrypty`](skrypty) – narzędzia CLI (RSSI, TDOA, widmo)
- [`requirements.txt`](requirements.txt) – zależności Pythona

## Licencja

- Backend C (`gnssdec`): GNU GPL v2
- Generowanie próbek GPS: MIT (Takuji Ebinuma)
- Pozostała część projektu: do uzgodnienia

## Znane ograniczenia

- Obsługiwane tylko na Linuxie
- Mapa wymaga połączenia internetowego
- Triangulacja TDOA potrzebuje idealnej synchronizacji czasu
- Symulacje wykorzystują zewnętrzne efemerydy BRDC
