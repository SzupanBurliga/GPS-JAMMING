# GPS JAMMING - Kompletny przewodnik instalacji i uruchomienia

Przewodnik krok po kroku do uruchomienia systemu analizy i detekcji zakłóceń GPS od zera.

## 📋 Wymagania systemowe

- **System operacyjny**: Linux (zalecane Ubuntu 20.04+), Windows 10/11, macOS
- **Python**: 3.8+ (zalecane 3.10 lub 3.11)
- **RAM**: minimum 4GB (zalecane 8GB+)
- **Miejsce na dysku**: ~5GB na wszystkie zależności
- **Grafika**: karta obsługująca OpenGL (do map i wizualizacji)

## 🚀 Krok 1: Przygotowanie środowiska

### 1.1 Sklonuj/pobierz projekt
```bash
# Sklonuj repozytorium lub rozpakuj archiwum do wybranego katalogu
cd /ścieżka/do/projektu
# Struktura powinna wyglądać tak:
# GPS-JAMMING/
# ├── GpsJammerApp/
# ├── simulate/
# ├── skrypty/
# ├── frontend/
# └── README.md
```

### 1.2 Utwórz środowisko wirtualne
```bash
# Przejdź do katalogu głównego projektu
cd GPS-JAMMING

# Utwórz virtualenv
python3 -m venv .venv

# Aktywuj virtualenv
# Linux/macOS:
source .venv/bin/activate
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Windows (CMD):
.venv\Scripts\activate.bat
```

## 🔧 Krok 2: Instalacja podstawowych zależności

### 2.1 Zaktualizuj pip i zainstaluj bazowe pakiety
```bash
pip install --upgrade pip setuptools wheel
```

### 2.2 Zainstaluj zależności GUI (PySide6)
```bash
# Główne biblioteki GUI
pip install PySide6 PySide6-QtWebEngine

# Jeśli wystąpią problemy z QtWebEngine, spróbuj:
pip install PySide6==6.5.2 PySide6-QtWebEngine==6.5.2
```

### 2.3 Zainstaluj biblioteki do analizy sygnałów
```bash
# Podstawowe biblioteki numeryczne i DSP
pip install numpy pandas scipy matplotlib

# Biblioteki do geolokalizacji
pip install haversine

# Biblioteki do analizy widma i DSP
pip install scikit-learn
```

## 🛰️ Krok 3: Instalacja zaawansowanych zależności (opcjonalne)

### 3.1 GNU Radio (dla symulacji jammerów)
**⚠️ Uwaga**: GNU Radio ma złożone zależności systemowe

#### Linux (Ubuntu/Debian):
```bash
# Instalacja z repozytorium systemowego
sudo apt update
sudo apt install gnuradio gnuradio-dev

# Lub kompilacja ze źródeł (zaawansowane)
# sudo apt install git cmake g++ libboost-all-dev libgmp-dev swig python3-numpy python3-mako python3-sphinx python3-lxml libsdl1.2-dev libgsl-dev libfftw3-dev libusb-1.0-0 libusb-dev libhid-dev libasound2-dev python3-matplotlib libqt5gui5 libqt5core5a libqt5opengl5-dev python3-pyqt5 liblog4cpp5-dev libzmq3-dev python3-yaml python3-click python3-click-plugins python3-zmq python3-scipy python3-gi python3-gi-cairo gir1.2-gtk-3.0 libcodec2-dev libgsm1-dev
```

#### macOS:
```bash
# Używając Homebrew
brew install gnuradio
```

#### Windows:
```bash
# Najłatwiej przez conda
conda install -c conda-forge gnuradio
```

### 3.2 GPS SDR biblioteki (opcjonalne, dla zaawansowanej analizy)
```bash
# UWAGA: Te biblioteki mają specjalne wymagania i mogą nie działać na wszystkich systemach
pip install pygpssdr  # Może wymagać dodatkowych kroków instalacji
```

### 3.3 Biblioteki RTL-SDR (dla prawdziwych odbiorników SDR)
```bash
# Linux
sudo apt install rtl-sdr librtlsdr-dev

# Python binding
pip install pyrtlsdr
```

## 🧪 Krok 4: Sprawdzenie instalacji

### 4.1 Test podstawowej funkcjonalności
```bash
# Przejdź do katalogu głównego projektu
cd GPS-JAMMING

# Test importów Pythona
python3 -c "
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from PySide6.QtWidgets import QApplication
from PySide6.QtWebEngineWidgets import QWebEngineView
print('✅ Wszystkie podstawowe biblioteki zainstalowane poprawnie!')
print(f'Python: {sys.version}')
print(f'NumPy: {np.__version__}')
print(f'Pandas: {pd.__version__}')
"
```

### 4.2 Test GUI
```bash
# Szybki test czy PySide6 działa z systemem graficznym
python3 -c "
from PySide6.QtWidgets import QApplication, QLabel
import sys
app = QApplication(sys.argv)
label = QLabel('Test OK - GUI działa!')
label.show()
print('✅ GUI test zakończony. Jeśli widzisz okienko - wszystko OK!')
"
```

## 🎯 Krok 5: Uruchomienie głównej aplikacji

### 5.1 Uruchom główne GUI
```bash
# Zawsze uruchamiaj z katalogu głównego projektu!
cd GPS-JAMMING
python GpsJammerApp/wstepny.py
```

**Co powinno się stać:**
- Otworzy się okno z mapą i panelem kontrolnym
- Mapa powinna załadować się w przeglądarce (Leaflet + OpenStreetMap)
- Panel po lewej stronie powinien zawierać przyciski do analizy

### 5.2 Test podstawowych funkcji
1. **Zmiana typu mapy** - kliknij przyciski: "🗺️ OpenStreetMap", "🛰️ Satelitarna", "🏔️ Topograficzna"
2. **Wybór pliku** - kliknij "📁 Wybierz plik" (możesz wybrać dowolny plik .bin)
3. **Live tracking** - kliknij "▶️ Start" aby przetestować symulację śledzenia na żywo

## 🔬 Krok 6: Uruchomienie narzędzi symulacyjnych

### 6.1 Frontend do generowania symulacji GPS
```bash
# Z katalogu głównego
python simulate/frontend/gnss_frontend.py
```

**Co to robi:**
- Otworzy okno z formularzem do generowania plików GPS
- Umożliwia symulację ruchu i jammerów
- **⚠️ Wymaga gps-sdr-sim** (zobacz krok 6.2)

### 6.2 Instalacja gps-sdr-sim (wymagane do symulacji)
```bash
# Klonuj i kompiluj gps-sdr-sim
cd GPS-JAMMING/simulate
git clone https://github.com/osqzss/gps-sdr-sim.git
cd gps-sdr-sim

# Linux/macOS
make
# Windows - potrzebujesz Visual Studio lub MinGW

# Sprawdź czy działa
./gps-sdr-sim -h
```

## 📊 Krok 7: Uruchomienie skryptów analizy

### 7.1 Analiza widma
```bash
# Przykład analizy widma pliku I/Q
python skrypty/widmo_plot.py dane_testowe.bin --fs 2048000 --fc 1575420000
```

### 7.2 Detekcja jammerów
```bash
# Analiza pliku pod kątem zakłóceń
python GpsJammerApp/app/checkIfJamming.py plik_nagrania.bin 5000.0
```

### 7.3 Triangulacja RSSI
```bash
# Edytuj skrypt aby dostosować ścieżki do plików
nano skrypty/triangulateRSSI.py
# Następnie uruchom
python skrypty/triangulateRSSI.py
```

### 7.4 Triangulacja TDOA
```bash
# Podobnie, edytuj ścieżki
nano skrypty/triangulateTDOA.py
python skrypty/triangulateTDOA.py
```

## 🗂️ Krok 8: Przygotowanie danych testowych

### 8.1 Struktura katalogów
```bash
# Utwórz katalogi na dane
mkdir -p data/recordings
mkdir -p data/cache
mkdir -p plots
```

### 8.2 Pobierz przykładowe pliki (jeśli dostępne)
```bash
# Umieść pliki .bin w katalogu data/recordings/
# Pliki powinny być w formacie rtl-sdr (uint8, I/Q interleaved)
```

### 8.3 Wygeneruj testowe dane
```bash
# Użyj frontendu symulacyjnego do wygenerowania próbek
python simulate/frontend/gnss_frontend.py
# Ustaw parametry i kliknij "Rozpocznij"
```

## 🔧 Rozwiązywanie problemów

### Problem: Błąd importu PySide6
```bash
# Spróbuj różnych wersji
pip uninstall PySide6 PySide6-QtWebEngine
pip install PySide6==6.5.2 PySide6-QtWebEngine==6.5.2

# Lub użyj PyQt5 jako alternatywę (wymaga zmian w kodzie)
pip install PyQt5 PyQtWebEngine
```

### Problem: Mapa się nie ładuje
- Sprawdź połączenie internetowe (mapa pobiera kafelki z OSM)
- Sprawdź czy QtWebEngine jest zainstalowane
- Spróbuj uruchomić w trybie debugowania

### Problem: GNU Radio nie działa
- GNU Radio jest opcjonalne - aplikacja główna powinna działać bez niego
- Skrypty jammerów wymagają GNU Radio tylko do generowania sygnałów zakłócających

### Problem: "FileNotFoundError" przy symulacji
- Sprawdź czy gps-sdr-sim jest skompilowany i dostępny
- Sprawdź ścieżki w `simulate/frontend/gnss_frontend.py`
- Pobierz pliki efemeryd (brdc*.n) z [NASA](https://cddis.nasa.gov/archive/gnss/data/daily/)

## 📚 Kolejne kroki

### Eksploruj funkcjonalność:
1. **Analiza plików** - użyj `GpsJammerApp/wstepny.py`
2. **Symulacje** - eksperymentuj z `simulate/frontend/gnss_frontend.py`  
3. **Skrypty analizy** - dostosuj parametry w `skrypty/`
4. **Wizualizacje** - sprawdź wyniki w `frontend/map.py`

### Zaawansowane użycie:
- Podłącz prawdziwy odbiornik RTL-SDR
- Skonfiguruj własne algorytmy detekcji w `GpsJammerApp/app/checkIfJamming.py`
- Rozszerz GUI o nowe funkcje w `GpsJammerApp/app/ui_mainwindow.py`

## 📁 Struktura projektu

```
GPS-JAMMING/
├── README.md                    # Ten przewodnik
├── GpsJammerApp/               # Główna aplikacja GUI
│   ├── wstepny.py             # Punkt wejścia - URUCHOM TO
│   ├── app/
│   │   ├── ui_mainwindow.py   # Główne okno aplikacji
│   │   ├── checkIfJamming.py  # Algorytmy detekcji
│   │   ├── config.py          # Konfiguracja
│   │   └── worker.py          # Wątki robocze
│   └── resources/
│       └── map_template.html  # Szablon mapy
├── simulate/                   # Narzędzia symulacyjne
│   ├── frontend/
│   │   ├── gnss_frontend.py   # GUI do generowania symulacji
│   │   └── jammers/           # Różne typy jammerów
│   └── gps-sdr-sim/          # Zewnętrzny generator GPS (do pobrania)
├── skrypty/                   # Skrypty analizy
│   ├── triangulateRSSI.py     # Triangulacja RSSI
│   ├── triangulateTDOA.py     # Triangulacja TDOA
│   └── widmo_plot.py          # Analiza widma
├── frontend/                  # Dodatkowe narzędzia wizualizacji
│   └── map.py
├── data/                      # Katalog na dane (stwórz ręcznie)
├── plots/                     # Wyniki wizualizacji
└── notatki/                   # Dokumentacja i notatki
    ├── notes.md
    └── todo.txt
```

## 🎯 Szybki start (TL;DR)

Dla niecierpliwych - minimalna instalacja:

```bash
# 1. Sklonuj/pobierz projekt
cd GPS-JAMMING

# 2. Stwórz venv
python3 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate.bat  # Windows

# 3. Zainstaluj minimum
pip install PySide6 PySide6-QtWebEngine numpy pandas matplotlib

# 4. Uruchom główną aplikację
python GpsJammerApp/wstepny.py
```

---

🎉 **Gratulacje!** Masz teraz w pełni działający system do analizy zakłóceń GPS. Jeśli napotkasz problemy, sprawdź `notatki/notes.md` i `notatki/todo.txt` dla dodatkowych wskazówek.

## 📞 Pomoc i wsparcie

- **Issues**: Zgłaszaj problemy w repozytorium GitHub
- **Dokumentacja**: Sprawdź pliki w katalogu `notatki/`
- **Przykłady**: Zobacz `docs/` (jeśli istnieje)

**Ostatnia aktualizacja**: Listopad 2025
