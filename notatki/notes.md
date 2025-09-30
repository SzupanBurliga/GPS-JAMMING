Syzyfus maximus
---

# 📝 Notatka projektowa – gps-jammer-app

## 🎯 Cel projektu (BUŁACINA)

**Zakres pracy i oczekiwany wynik**:
Opracowanie, implementacja i przetestowanie **zintegrowanego systemu** do analizy, detekcji i lokalizacji zakłóceń wpływających na działanie systemów GNSS.

Zakres prac obejmuje:

* Analizę literatury nt. systemów GNSS, zakłóceń, metod detekcji i lokalizacji.
* Zaprojektowanie architektury systemu (akwizycja danych GNSS, opcjonalne generowanie zakłóceń).
* Implementację algorytmów analizy sygnałów GNSS i wielopoziomowej detekcji/klasyfikacji zakłóceń.
* Implementację metody lokalizacji źródeł zakłóceń.
* Opracowanie interfejsu graficznego (wizualizacja danych, zakłóceń, lokalizacji).
* Integrację komponentów i testy w labie oraz – jeśli możliwe – w warunkach rzeczywistych.

👉 Rezultat: **system demonstracyjny** zdolny do odbioru, analizy, detekcji i lokalizacji zakłóceń GNSS + dokumentacja + raport.

---

## 📌 To-Do (24.09 – cel: do końca tygodnia)

### Łysy kod

* [ ] Edycja – usunąć rzeczy nieużywane (na ten moment BladeRF praktycznie usunięty, pozostałe etapy to cherry picking zbędnych funkcji)
* [x] Wywalić GUI
* [x] Hardcodować configi
* [x] Dodać obsługę kodu z poziomu frontendu (przynajmniej częściowo)

### Sygnalówka

* [ ] Zaimplementować funkcję do **wykrywania zakłóceń**

  * Zmienna bool → czy występuje zakłócenie
  * Lista → jakie zakłócenia znaleziono
  * (Opcjonalnie) klasyfikacja typu zakłócenia

### Frontend

* [ ] Poprawić strukturę, żeby miała więcej sensu
* [ ] Ładnie porozdzielać komponenty

---

## 📂 Struktura projektu

```
gps-jammer-app/                       # Główny katalog aplikacji
├─ config/                            # Konfiguracje aplikacji
├─ data/                              # Dane wejściowe/wyjściowe
│  ├─ recordings/                     # Zapisane nagrania SDR/GPS
│  └─ cache/                          # Tymczasowe pliki
├─ resources/                         # Zasoby statyczne (grafika, style, UI)
│  ├─ icons/                          # Ikony do toolbarów, markerów
│  ├─ ui/                             # Pliki .ui z Qt Designer
│  └─ styles/                         # Style aplikacji (QSS)
│     ├─ main.qss                     # Główny stylesheet
│     ├─ dark.qss                     # Motyw ciemny
│     ├─ light.qss                    # Motyw jasny
│     └─ widgets/                     # Style widgetów
│        ├─ buttons.qss               # Przyciski
│        └─ panels.qss                # Panele
├─ src/                               # Źródła aplikacji (Python)
│  ├─ app.py                          # Punkt wejścia (main)
│  ├─ mainwindow.py                   # Logika głównego okna GUI
│  ├─ views/                          # Widoki GUI
│  │  ├─ map_widget.py                # Widget mapy
│  │  └─ panels.py                    # Panele boczne
│  ├─ logic/                          # Logika (kontrolery)
│  │  ├─ app_controller.py            # Kontroler główny
│  │  └─ map_controller.py            # Kontroler mapy
│  ├─ models/                         # Modele danych
│  │  ├─ geo.py                       # Geolokalizacja
│  │  ├─ detection.py                 # Detekcja zakłóceń
│  │  └─ sdr.py                       # Dane SDR
│  ├─ io_sources/                     # Źródła danych
│  │  ├─ rtl_file_reader.py           # Odczyt SDR
│  │  └─ metadata.py                  # Obsługa metadanych
│  ├─ dsp/                            # Digital Signal Processing
│  │  ├─ preprocessing.py             # Wstępne przetwarzanie
│  │  ├─ psd.py                       # Widmo mocy (PSD)
│  │  └─ features.py                  # Ekstrakcja cech
│  ├─ detectors/                      # Detektory zakłóceń
│  │  ├─ base.py                      # Interfejs bazowy
│  │  └─ prototype.py                 # Prototypowy detektor
│  ├─ workers/                        # Wątki / procesy
│  │  ├─ ingestion_worker.py          # Pobieranie danych
│  │  └─ detection_worker.py          # Detekcja zakłóceń
│  ├─ services/                       # Usługi aplikacji
│  │  ├─ storage.py                   # Obsługa zapisu/odczytu
│  │  ├─ settings_service.py          # Obsługa ustawień
│  │  └─ style_service.py             # Style QSS
│  ├─ utils/                          # Narzędzia pomocnicze
│  │  ├─ geo_math.py                  # Funkcje matematyczne
│  │  └─ logging_setup.py             # Konfiguracja logowania
│  └─ __init__.py                     # Init modułu src
└─ tests/                             # Testy automatyczne
   ├─ unit/                           # Jednostkowe
   └─ integration/                    # Integracyjne
```

---
