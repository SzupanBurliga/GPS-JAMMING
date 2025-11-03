import os
import random
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QGroupBox, 
                             QTextEdit, QFileDialog, QProgressBar, 
                             QSpinBox, QDoubleSpinBox)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import Qt, QTimer

from . import config
from .worker import GPSAnalysisThread

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GPS Jamming - Mapa i Analiza Sygnałów")
        self.resize(1400, 800)
        
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
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        self.create_control_panel(main_layout)
        self.web_view = QWebEngineView()
        
        try:
            with open("resources/map_template.html", "r", encoding="utf-8") as f:
                html_template = f.read()
            # Wstrzyknij stałe z config.py do szablonu HTML
            self.web_view.setHtml(html_template.format(
                LAT=config.LAT, 
                LNG=config.LNG, 
                ZOOM=config.ZOOM
            ))
        except FileNotFoundError:
            print("BŁĄD: Nie można załadować pliku map_template.html!")
            self.web_view.setHtml("<h1>Błąd: Nie znaleziono pliku map_template.html</h1>")

        main_layout.addWidget(self.web_view, 3)
 
        self.analysis_thread = None

        self.live_track_timer = QTimer(self)
        self.live_track_timer.timeout.connect(self.update_live_position)
        self.current_live_lat = config.LAT
        self.current_live_lng = config.LNG
        
    def create_control_panel(self, main_layout):
        """Tworzy panel kontrolny po lewej stronie"""
        control_panel = QWidget()
        control_panel.setMaximumWidth(350)
        control_panel.setMinimumWidth(300)
        main_layout.addWidget(control_panel, 1)  

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

        analysis_group = QGroupBox("Analiza Sygnałów GPS")
        analysis_group.setStyleSheet(group_style)
        analysis_layout = QVBoxLayout(analysis_group)

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

        params_layout = QVBoxLayout()

        freq_layout = QHBoxLayout()
        freq_layout.addWidget(QLabel("Częstotliwość [MHz]:"))
        self.freq_spin = QDoubleSpinBox()
        self.freq_spin.setRange(1500, 1600)
        self.freq_spin.setValue(1575.42) 
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

        self.analyze_btn = QPushButton("🔍 Rozpocznij Analizę")
        self.analyze_btn.clicked.connect(self.start_analysis)
        self.analyze_btn.setStyleSheet(action_button_style)
        analysis_layout.addWidget(self.analyze_btn)
        
        self.clear_btn = QPushButton("🗑️ Wyczyść Markery")
        self.clear_btn.clicked.connect(self.clear_markers)
        self.clear_btn.setStyleSheet(danger_button_style)
        analysis_layout.addWidget(self.clear_btn)

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

        live_group = QGroupBox("Śledzenie na żywo")
        live_group.setStyleSheet(group_style)
        live_layout = QHBoxLayout(live_group)
        
        self.start_live_btn = QPushButton("▶️ Start")
        self.start_live_btn.clicked.connect(self.start_live_tracking)
        self.start_live_btn.setStyleSheet(action_button_style) 
        live_layout.addWidget(self.start_live_btn)
        
        self.stop_live_btn = QPushButton("⏹️ Stop")
        self.stop_live_btn.clicked.connect(self.stop_live_tracking)
        self.stop_live_btn.setStyleSheet(danger_button_style) 
        self.stop_live_btn.setEnabled(False) 
        live_layout.addWidget(self.stop_live_btn)
        
        layout.addWidget(live_group)

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

        test_group = QGroupBox("Dane Testowe")
        test_group.setStyleSheet(group_style)
        test_layout = QVBoxLayout(test_group)
        
        self.add_test_btn = QPushButton("🧪 Dodaj Testowe Punkty")
        self.add_test_btn.clicked.connect(self.add_test_points)
        self.add_test_btn.setStyleSheet(test_button_style)
        test_layout.addWidget(self.add_test_btn)
        
        layout.addWidget(test_group)

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

        for point in points:
            js_code = f"""
            addJammingPoint({point['lat']}, {point['lng']}, {point['strength']}, {point['frequency']});
            """
            self.web_view.page().runJavaScript(js_code)
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
        """Czyści wszystkie markery z mapy (w tym ślad na żywo)"""
        self.web_view.page().runJavaScript("clearSignalMarkers();")
        self.results_text.setPlainText("Markery i ślad zostały wyczyszczone.")
        
    def add_test_points(self):
        """Dodaje testowe punkty zakłóceń"""
        test_points = [
            {'lat': config.LAT + 0.005, 'lng': config.LNG + 0.005, 'strength': 85, 'frequency': 1575.42},
            {'lat': config.LAT - 0.003, 'lng': config.LNG + 0.008, 'strength': 92, 'frequency': 1575.38},
            {'lat': config.LAT + 0.002, 'lng': config.LNG - 0.006, 'strength': 67, 'frequency': 1575.45},
            {'lat': config.LAT - 0.007, 'lng': config.LNG - 0.002, 'strength': 43, 'frequency': 1575.40},
            {'lat': config.LAT + 0.008, 'lng': config.LNG + 0.001, 'strength': 78, 'frequency': 1575.44},
        ]
        
        for point in test_points:
            js_code = f"""
            addJammingPoint({point['lat']}, {point['lng']}, {point['strength']}, {point['frequency']});
            """
            self.web_view.page().runJavaScript(js_code)
            
        self.results_text.setPlainText(f"Dodano {len(test_points)} testowych punktów zakłóceń GPS.")

    def start_live_tracking(self):
        """Rozpoczyna symulację śledzenia na żywo co 3 sekundy"""
        self.start_live_btn.setEnabled(False)
        self.stop_live_btn.setEnabled(True)

        self.current_live_lat = config.LAT + random.uniform(-0.01, 0.01)
        self.current_live_lng = config.LNG + random.uniform(-0.01, 0.01)

        self.update_live_position() 
        
        # Ustaw timer na 1000 ms )
        self.live_track_timer.start(1000)
        self.results_text.setPlainText("Rozpoczęto śledzenie na żywo (co 1 sek.).")
        
    def stop_live_tracking(self):
        """Zatrzymuje śledzenie na żywo"""
        self.live_track_timer.stop()
        self.start_live_btn.setEnabled(True)
        self.stop_live_btn.setEnabled(False)
        self.results_text.setPlainText("Zatrzymano śledzenie na żywo.")


# tu skrypt kuby !!!!!!!!!!!!!!!!!!!!!!1
    def update_live_position(self):
        self.current_live_lat += random.uniform(-0.0005, 0.0005)
        self.current_live_lng += random.uniform(0.0003, 0.001) # Symulacja ruchu na wschód
        
        js_code = f"window.updateLivePosition({self.current_live_lat}, {self.current_live_lng});"
        self.web_view.page().runJavaScript(js_code)
        
        print(f"Nowa pozycja: {self.current_live_lat}, {self.current_live_lng}")