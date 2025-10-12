import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QGroupBox, 
                             QTextEdit, QFileDialog, QProgressBar, QComboBox,
                             QSpinBox, QDoubleSpinBox)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QThread, pyqtSignal, Qt

# <<< TU USTAW WSPÓŁRZĘDNE I ZOOM >>>
LAT = 50.06143   # Kraków
LNG = 19.93658
ZOOM = 13
# <<< KONIEC USTAWIEŃ >>>

HTML = f"""
<!DOCTYPE html>
<html lang="pl">
<head>
  <meta charset="utf-8" />
  <title>Mapa GPS Jamming Analysis</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link
    rel="stylesheet"
    href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
    integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY="
    crossorigin=""
  />
  <script
    src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
    integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo="
    crossorigin=""
  ></script>
  <style>
    html, body, #map {{ height: 100%; margin: 0; }}
    .info {{
      padding: 6px 8px;
      font: 14px/16px Arial, Helvetica, sans-serif;
      background: white;
      background: rgba(255,255,255,0.8);
      box-shadow: 0 0 15px rgba(0,0,0,0.2);
      border-radius: 5px;
    }}
    .legend {{
      line-height: 18px;
      color: #555;
    }}
    .legend i {{
      width: 18px;
      height: 18px;
      float: left;
      margin-right: 8px;
      opacity: 0.7;
    }}
  </style>
</head>
<body>
  <div id="map"></div>
  <script>
    const lat = {LAT};
    const lng = {LNG};
    const zoom = {ZOOM};

    const map = L.map('map').setView([lat, lng], zoom);

    // Różne warstwy map
    const osmLayer = L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
    }});

    const satelliteLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
      maxZoom: 19,
      attribution: 'Tiles &copy; Esri'
    }});

    const topoLayer = L.tileLayer('https://{{s}}.tile.opentopomap.org/{{z}}/{{x}}/{{y}}.png', {{
      maxZoom: 17,
      attribution: 'Map data: &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>, <a href="http://viewfinderpanoramas.org">SRTM</a> | Map style: &copy; <a href="https://opentopomap.org">OpenTopoMap</a>'
    }});

    // Domyślna warstwa
    osmLayer.addTo(map);

    // Kontrola warstw
    const baseMaps = {{
      "OpenStreetMap": osmLayer,
      "Satelitarna": satelliteLayer,
      "Topograficzna": topoLayer
    }};

    L.control.layers(baseMaps).addTo(map);

    // Marker główny
    const mainMarker = L.marker([lat, lng]).addTo(map)
      .bindPopup(`<b>Punkt bazowy</b><br>Lat: ${{lat.toFixed(5)}}<br>Lng: ${{lng.toFixed(5)}}`)
      .openPopup();

    // Zmienne globalne dla markerów sygnałów
    let signalMarkers = [];
    let jammingZones = [];

    // Funkcja do dodawania punktów zakłóceń
    function addJammingPoint(lat, lng, strength, frequency) {{
      const color = strength > 80 ? 'red' : strength > 50 ? 'orange' : 'yellow';
      const marker = L.circleMarker([lat, lng], {{
        color: color,
        fillColor: color,
        fillOpacity: 0.6,
        radius: Math.max(5, strength / 10)
      }}).addTo(map);
      
      marker.bindPopup(`
        <b>Zakłócenie GPS</b><br>
        Siła: ${{strength}}%<br>
        Częstotliwość: ${{frequency}} MHz<br>
        Współrzędne: ${{lat.toFixed(6)}}, ${{lng.toFixed(6)}}
      `);
      
      signalMarkers.push(marker);
      return marker;
    }}

    // Funkcja do czyszczenia markerów
    function clearSignalMarkers() {{
      signalMarkers.forEach(marker => map.removeLayer(marker));
      signalMarkers = [];
    }}

    // Funkcja do zmiany warstwy (wywoływana z PyQt)
    function changeMapLayer(layerName) {{
      map.eachLayer(function(layer) {{
        if (layer._url) map.removeLayer(layer);
      }});
      
      switch(layerName) {{
        case 'osm':
          osmLayer.addTo(map);
          break;
        case 'satellite':
          satelliteLayer.addTo(map);
          break;
        case 'topo':
          topoLayer.addTo(map);
          break;
      }}
    }}

    // Legenda
    const legend = L.control({{position: 'bottomright'}});
    legend.onAdd = function (map) {{
      const div = L.DomUtil.create('div', 'info legend');
      div.innerHTML = `
        <h4>Siła zakłóceń GPS</h4>
        <i style="background:red"></i> Wysokie (80-100%)<br>
        <i style="background:orange"></i> Średnie (50-80%)<br>
        <i style="background:yellow"></i> Niskie (0-50%)<br>
      `;
      return div;
    }};
    legend.addTo(map);

    // Ekspozycja funkcji dla PyQt
    window.addJammingPoint = addJammingPoint;
    window.clearSignalMarkers = clearSignalMarkers;
    window.changeMapLayer = changeMapLayer;
  </script>
</body>
</html>
"""

class GPSAnalysisThread(QThread):
    """Thread do analizy plików GPS w tle"""
    analysis_complete = pyqtSignal(list)  # lista punktów z danymi
    progress_update = pyqtSignal(int)     # postęp 0-100
    
    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path
        
    def run(self):
        """Symulacja analizy pliku GPS - zastąp właściwą implementacją"""
        try:
            import random
            import time
            
            points = []
            file_size = os.path.getsize(self.file_path) if os.path.exists(self.file_path) else 1000000
            
            # Symulacja analizy - zastąp prawdziwą analizą sygnału
            for i in range(20):  # 20 punktów testowych
                if self.isInterruptionRequested():
                    return
                    
                # Generuj losowe punkty wokół Krakowa
                lat = LAT + random.uniform(-0.01, 0.01)
                lng = LNG + random.uniform(-0.01, 0.01)
                strength = random.randint(10, 95)
                frequency = round(random.uniform(1570, 1580), 2)
                
                points.append({
                    'lat': lat,
                    'lng': lng,
                    'strength': strength,
                    'frequency': frequency,
                    'timestamp': i
                })
                
                self.progress_update.emit(int((i + 1) / 20 * 100))
                time.sleep(0.1)  # Symulacja czasu analizy
                
            self.analysis_complete.emit(points)
            
        except Exception as e:
            print(f"Błąd analizy: {e}")
            self.analysis_complete.emit([])


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GPS Jamming Analysis - Mapa i Analiza Sygnałów")
        self.resize(1400, 800)
        
        # Style dla głównego okna
        self.setStyleSheet("""
        QMainWindow {
            background-color: #ecf0f1;
        }
        QLabel {
            color: #2c3e50;
            font-size: 12px;
            font-weight: bold;
        }
        """)
        
        # Widget główny
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # Layout główny (poziomy)
        main_layout = QHBoxLayout(main_widget)
        
        # Panel kontrolny po lewej stronie
        self.create_control_panel(main_layout)
        
        # Mapa po prawej stronie
        self.web_view = QWebEngineView()
        self.web_view.setHtml(HTML)
        main_layout.addWidget(self.web_view, 3)  # 3/4 szerokości dla mapy
        
        # Thread do analizy
        self.analysis_thread = None
        
    def create_control_panel(self, main_layout):
        """Tworzy panel kontrolny po lewej stronie"""
        control_panel = QWidget()
        control_panel.setMaximumWidth(350)
        control_panel.setMinimumWidth(300)
        main_layout.addWidget(control_panel, 1)  # 1/4 szerokości dla panelu
        
        # Style dla przycisków
        button_style = """
        QPushButton {
            background-color: #2c3e50;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 10px;
            font-size: 14px;
            font-weight: bold;
            margin: 2px;
        }
        QPushButton:hover {
            background-color: #34495e;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }
        QPushButton:pressed {
            background-color: #1a252f;
        }
        QPushButton:disabled {
            background-color: #7f8c8d;
            color: #bdc3c7;
        }
        """
        
        # Style dla przycisków mapy (różne kolory)
        map_button_style = """
        QPushButton {
            color: white;
            border: none;
            border-radius: 8px;
            padding: 10px;
            font-size: 13px;
            font-weight: bold;
            margin: 2px;
        }
        QPushButton:hover {
            box-shadow: 0 2px 4px rgba(0,0,0,0.3);
            transform: translateY(-1px);
        }
        QPushButton:pressed {
            transform: translateY(0px);
        }
        """
        
        # Style dla przycisków akcji
        action_button_style = """
        QPushButton {
            background-color: #27ae60;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 12px;
            font-size: 14px;
            font-weight: bold;
            margin: 3px;
        }
        QPushButton:hover {
            background-color: #2ecc71;
            box-shadow: 0 3px 6px rgba(0,0,0,0.2);
        }
        QPushButton:pressed {
            background-color: #229954;
        }
        """
        
        # Style dla przycisków niebezpiecznych (clear, delete)
        danger_button_style = """
        QPushButton {
            background-color: #e74c3c;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 10px;
            font-size: 14px;
            font-weight: bold;
            margin: 2px;
        }
        QPushButton:hover {
            background-color: #c0392b;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }
        QPushButton:pressed {
            background-color: #a93226;
        }
        """
        
        # Style dla przycisków testowych
        test_button_style = """
        QPushButton {
            background-color: #f39c12;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 10px;
            font-size: 14px;
            font-weight: bold;
            margin: 2px;
        }
        QPushButton:hover {
            background-color: #e67e22;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }
        QPushButton:pressed {
            background-color: #d68910;
        }
        """
        
        # Style dla grup
        group_style = """
        QGroupBox {
            font-weight: bold;
            font-size: 14px;
            border: 2px solid #bdc3c7;
            border-radius: 10px;
            margin-top: 10px;
            padding-top: 10px;
            background-color: #f8f9fa;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 8px 0 8px;
            color: #2c3e50;
            background-color: #f8f9fa;
        }
        """
        
        layout = QVBoxLayout(control_panel)
        
        # === GRUPA: Typ Mapy ===
        map_group = QGroupBox("Typ Mapy")
        map_group.setStyleSheet(group_style)
        map_layout = QVBoxLayout(map_group)
        
        self.osm_btn = QPushButton("🗺️ OpenStreetMap")
        self.osm_btn.clicked.connect(lambda: self.change_map_layer('osm'))
        self.osm_btn.setStyleSheet(map_button_style + "QPushButton { background-color: #3498db; }")
        map_layout.addWidget(self.osm_btn)
        
        self.satellite_btn = QPushButton("🛰️ Satelitarna")
        self.satellite_btn.clicked.connect(lambda: self.change_map_layer('satellite'))
        self.satellite_btn.setStyleSheet(map_button_style + "QPushButton { background-color: #9b59b6; }")
        map_layout.addWidget(self.satellite_btn)
        
        self.topo_btn = QPushButton("🏔️ Topograficzna")
        self.topo_btn.clicked.connect(lambda: self.change_map_layer('topo'))
        self.topo_btn.setStyleSheet(map_button_style + "QPushButton { background-color: #16a085; }")
        map_layout.addWidget(self.topo_btn)
        
        layout.addWidget(map_group)
        
        # === GRUPA: Analiza GPS ===
        analysis_group = QGroupBox("Analiza Sygnałów GPS")
        analysis_group.setStyleSheet(group_style)
        analysis_layout = QVBoxLayout(analysis_group)
        
        # Wybór pliku
        file_layout = QHBoxLayout()
        self.file_label = QLabel("Brak pliku")
        self.file_label.setWordWrap(True)
        self.file_label.setStyleSheet("""
        QLabel {
            background-color: #ecf0f1;
            border: 2px dashed #bdc3c7;
            border-radius: 5px;
            padding: 8px;
            font-style: italic;
            color: #7f8c8d;
        }
        """)
        file_layout.addWidget(self.file_label)
        
        self.browse_btn = QPushButton("📁 Wybierz plik")
        self.browse_btn.clicked.connect(self.browse_file)
        self.browse_btn.setStyleSheet(button_style)
        file_layout.addWidget(self.browse_btn)
        
        analysis_layout.addLayout(file_layout)
        
        # Parametry analizy
        params_layout = QVBoxLayout()
        
        # Częstotliwość
        freq_layout = QHBoxLayout()
        freq_layout.addWidget(QLabel("Częstotliwość [MHz]:"))
        self.freq_spin = QDoubleSpinBox()
        self.freq_spin.setRange(1500, 1600)
        self.freq_spin.setValue(1575.42)  # L1 GPS
        self.freq_spin.setDecimals(2)
        self.freq_spin.setStyleSheet("""
        QDoubleSpinBox {
            border: 2px solid #bdc3c7;
            border-radius: 5px;
            padding: 5px;
            font-size: 13px;
            background-color: white;
        }
        QDoubleSpinBox:focus {
            border-color: #3498db;
        }
        """)
        freq_layout.addWidget(self.freq_spin)
        params_layout.addLayout(freq_layout)
        
        # Próg wykrywania
        threshold_layout = QHBoxLayout()
        threshold_layout.addWidget(QLabel("Próg wykrywania [%]:"))
        self.threshold_spin = QSpinBox()
        self.threshold_spin.setRange(1, 100)
        self.threshold_spin.setValue(30)
        self.threshold_spin.setStyleSheet("""
        QSpinBox {
            border: 2px solid #bdc3c7;
            border-radius: 5px;
            padding: 5px;
            font-size: 13px;
            background-color: white;
        }
        QSpinBox:focus {
            border-color: #3498db;
        }
        """)
        threshold_layout.addWidget(self.threshold_spin)
        params_layout.addLayout(threshold_layout)
        
        analysis_layout.addLayout(params_layout)
        
        # Przyciski analizy
        self.analyze_btn = QPushButton("🔍 Rozpocznij Analizę")
        self.analyze_btn.clicked.connect(self.start_analysis)
        self.analyze_btn.setStyleSheet(action_button_style)
        analysis_layout.addWidget(self.analyze_btn)
        
        self.clear_btn = QPushButton("🗑️ Wyczyść Markery")
        self.clear_btn.clicked.connect(self.clear_markers)
        self.clear_btn.setStyleSheet(danger_button_style)
        analysis_layout.addWidget(self.clear_btn)
        
        # Pasek postępu
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
        QProgressBar {
            border: 2px solid #bdc3c7;
            border-radius: 8px;
            text-align: center;
            font-weight: bold;
            background-color: #ecf0f1;
        }
        QProgressBar::chunk {
            background-color: #3498db;
            border-radius: 6px;
        }
        """)
        analysis_layout.addWidget(self.progress_bar)
        
        layout.addWidget(analysis_group)
        
        # === GRUPA: Wyniki ===
        results_group = QGroupBox("Wyniki Analizy")
        results_group.setStyleSheet(group_style)
        results_layout = QVBoxLayout(results_group)
        
        self.results_text = QTextEdit()
        self.results_text.setMaximumHeight(200)
        self.results_text.setPlainText("Brak danych do analizy...")
        self.results_text.setStyleSheet("""
        QTextEdit {
            border: 2px solid #bdc3c7;
            border-radius: 8px;
            padding: 8px;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            background-color: #2c3e50;
            color: #ecf0f1;
        }
        """)
        results_layout.addWidget(self.results_text)
        
        layout.addWidget(results_group)
        
        # === GRUPA: Test Data ===
        test_group = QGroupBox("Dane Testowe")
        test_group.setStyleSheet(group_style)
        test_layout = QVBoxLayout(test_group)
        
        self.add_test_btn = QPushButton("🧪 Dodaj Testowe Punkty")
        self.add_test_btn.clicked.connect(self.add_test_points)
        self.add_test_btn.setStyleSheet(test_button_style)
        test_layout.addWidget(self.add_test_btn)
        
        layout.addWidget(test_group)
        
        # Spacer na dole
        layout.addStretch()
        
    def change_map_layer(self, layer_type):
        """Zmienia warstwę mapy"""
        self.web_view.page().runJavaScript(f"changeMapLayer('{layer_type}');")
        
    def browse_file(self):
        """Otwiera dialog wyboru pliku"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Wybierz plik z danymi GPS", 
            "../data/", 
            "Pliki binarne (*.bin);;Wszystkie pliki (*.*)"
        )
        
        if file_path:
            self.file_label.setText(os.path.basename(file_path))
            self.current_file = file_path
        
    def start_analysis(self):
        """Rozpoczyna analizę pliku GPS"""
        if not hasattr(self, 'current_file'):
            self.results_text.setPlainText("Najpierw wybierz plik do analizy!")
            return
            
        if self.analysis_thread and self.analysis_thread.isRunning():
            self.results_text.setPlainText("Analiza już trwa...")
            return
            
        self.analyze_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        self.analysis_thread = GPSAnalysisThread(self.current_file)
        self.analysis_thread.progress_update.connect(self.update_progress)
        self.analysis_thread.analysis_complete.connect(self.analysis_finished)
        self.analysis_thread.start()
        
        self.results_text.setPlainText("Rozpoczynam analizę...")
        
    def update_progress(self, value):
        """Aktualizuje pasek postępu"""
        self.progress_bar.setValue(value)
        
    def analysis_finished(self, points):
        """Wywoływane po zakończeniu analizy"""
        self.analyze_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        if not points:
            self.results_text.setPlainText("Nie znaleziono punktów zakłóceń lub błąd analizy.")
            return
            
        # Dodaj punkty na mapę
        for point in points:
            js_code = f"""
            addJammingPoint({point['lat']}, {point['lng']}, {point['strength']}, {point['frequency']});
            """
            self.web_view.page().runJavaScript(js_code)
            
        # Podsumowanie w tekście
        high_strength = [p for p in points if p['strength'] > 80]
        medium_strength = [p for p in points if 50 <= p['strength'] <= 80]
        low_strength = [p for p in points if p['strength'] < 50]
        
        summary = f"""ANALIZA ZAKOŃCZONA:
Znaleziono {len(points)} punktów zakłóceń GPS

Wysokie zakłócenia (>80%): {len(high_strength)} punktów
Średnie zakłócenia (50-80%): {len(medium_strength)} punktów  
Niskie zakłócenia (<50%): {len(low_strength)} punktów

Najsilniejsze zakłócenie: {max(points, key=lambda x: x['strength'])['strength']}%
Średnia siła zakłóceń: {sum(p['strength'] for p in points) / len(points):.1f}%

Parametry analizy:
- Częstotliwość: {self.freq_spin.value()} MHz
- Próg wykrywania: {self.threshold_spin.value()}%
"""
        self.results_text.setPlainText(summary)
        
    def clear_markers(self):
        """Czyści wszystkie markery z mapy"""
        self.web_view.page().runJavaScript("clearSignalMarkers();")
        self.results_text.setPlainText("Markery zostały wyczyszczone.")
        
    def add_test_points(self):
        """Dodaje testowe punkty zakłóceń"""
        import random
        
        test_points = [
            {'lat': LAT + 0.005, 'lng': LNG + 0.005, 'strength': 85, 'frequency': 1575.42},
            {'lat': LAT - 0.003, 'lng': LNG + 0.008, 'strength': 92, 'frequency': 1575.38},
            {'lat': LAT + 0.002, 'lng': LNG - 0.006, 'strength': 67, 'frequency': 1575.45},
            {'lat': LAT - 0.007, 'lng': LNG - 0.002, 'strength': 43, 'frequency': 1575.40},
            {'lat': LAT + 0.008, 'lng': LNG + 0.001, 'strength': 78, 'frequency': 1575.44},
        ]
        
        for point in test_points:
            js_code = f"""
            addJammingPoint({point['lat']}, {point['lng']}, {point['strength']}, {point['frequency']});
            """
            self.web_view.page().runJavaScript(js_code)
            
        self.results_text.setPlainText(f"Dodano {len(test_points)} testowych punktów zakłóceń GPS.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())
