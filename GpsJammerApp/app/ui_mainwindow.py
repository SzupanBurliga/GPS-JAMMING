import os
import random
import subprocess  
import sys         
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

        self.file_display = QTextEdit()
        self.file_display.setReadOnly(True)
        self.file_display.setPlaceholderText("Brak wybranych plików...")
        self.file_display.setMaximumHeight(80) 
        self.file_display.setStyleSheet("""
        QTextEdit {
            border: 2px solid #bdc3c7;
            border-radius: 8px;
            padding: 8px;
            font-family: 'Courier New', monospace;
            font-size: 11px;
            background-color: white;
            color: #2c3e50;
        }
        """)
        analysis_layout.addWidget(self.file_display)
        
        self.browse_btn = QPushButton("📁 Wybierz pliki (maks. 3)") 
        self.browse_btn.clicked.connect(self.browse_files) 
        self.browse_btn.setStyleSheet(button_style)
        analysis_layout.addWidget(self.browse_btn)

        params_layout = QVBoxLayout()

        params_layout.addWidget(QLabel("Częstotliwość [MHz]:"))
        self.freq_spin = QDoubleSpinBox()
        self.freq_spin.setRange(1500, 1600)
        self.freq_spin.setValue(1575.42) 
        self.freq_spin.setDecimals(2)
        # --- POPRAWKA WIDOCZNOŚCI ---
        self.freq_spin.setStyleSheet("""
        QDoubleSpinBox {
            border: 2px solid #bdc3c7;
            border-radius: 5px;
            padding: 5px;
            font-size: 13px;
            background-color: white;
            color: #2c3e50; 
        }
        QDoubleSpinBox:focus {
            border-color: #3498db;
        }
        """)
        # --- KONIEC POPRAWKI ---
        params_layout.addWidget(self.freq_spin) 

        params_layout.addWidget(QLabel("Próg wykrywania [%]:"))
        self.threshold_spin = QSpinBox()
        self.threshold_spin.setRange(1, 100)
        self.threshold_spin.setValue(30)
        # --- POPRAWKA WIDOCZNOŚCI ---
        self.threshold_spin.setStyleSheet("""
        QSpinBox {
            border: 2px solid #bdc3c7;
            border-radius: 5px;
            padding: 5px;
            font-size: 13px;
            background-color: white;
            color: #2c3e50;
        }
        QSpinBox:focus {
            border-color: #3498db;
        }
        """)
        # --- KONIEC POPRAWKI ---
        params_layout.addWidget(self.threshold_spin) 
        
        analysis_layout.addLayout(params_layout)

        self.analyze_btn = QPushButton("🔍 Rozpocznij Analizę")
        self.analyze_btn.clicked.connect(self.start_analysis)
        self.analyze_btn.setStyleSheet(action_button_style)
        
        self.clear_btn = QPushButton("🗑️ Wyczyść Markery")
        self.clear_btn.clicked.connect(self.clear_markers)
        self.clear_btn.setStyleSheet(danger_button_style)
        
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
        
        action_group = QGroupBox("Działania")
        action_group.setStyleSheet(group_style)
        action_layout = QVBoxLayout(action_group)
        
        action_layout.addWidget(self.analyze_btn) 
        action_layout.addWidget(self.clear_btn)   
        
        layout.addWidget(action_group)

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

        sim_group = QGroupBox("Symulacja")
        sim_group.setStyleSheet(group_style)
        sim_layout = QVBoxLayout(sim_group)
        
        self.run_simulation_btn = QPushButton("⚙️ Wygeneruj pliki symulacyjne")
        self.run_simulation_btn.clicked.connect(self.run_simulation_script) 
        self.run_simulation_btn.setStyleSheet(test_button_style)
        sim_layout.addWidget(self.run_simulation_btn)
        
        layout.addWidget(sim_group)

        layout.addStretch()
        
    def change_map_layer(self, layer_type):
        """Zmienia warstwę mapy"""
        self.web_view.page().runJavaScript(f"changeMapLayer('{layer_type}');")
        
    # --- ZMIANA: Dodano limit 3 plików ---
    def browse_files(self):
        """Otwiera dialog wyboru wielu plików (limit 3)"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, 
            "Wybierz pliki z danymi GPS (maks. 3)", # Zmieniony tytuł
            "../data/", 
            "Pliki binarne (*.bin);;Wszystkie pliki (*.*)"
        )
        
        if file_paths:
            # --- ZMIANA: Sprawdzenie limitu plików ---
            if len(file_paths) > 3:
                self.results_text.setPlainText("BŁĄD: Możesz wybrać maksymalnie 3 pliki.")
                # Wyczyść stary wybór, jeśli jest niepoprawny
                if hasattr(self, 'current_files'):
                    self.current_files.clear()
                self.file_display.setPlainText("Wybierz maksymalnie 3 pliki.")
                return 
            # --- KONIEC ZMIANY ---

            self.current_files = file_paths 
            basenames = [os.path.basename(p) for p in file_paths]
            self.file_display.setPlainText("\n".join(basenames))
    # --- KONIEC ZMIANY ---
        
    def start_analysis(self):
        """Rozpoczyna analizę wybranych plików GPS"""
        if not hasattr(self, 'current_files') or not self.current_files:
            self.results_text.setPlainText("Najpierw wybierz plik(i) do analizy!")
            return
            
        if self.analysis_thread and self.analysis_thread.isRunning():
            self.results_text.setPlainText("Analiza już trwa...")
            return
            
        self.analyze_btn.setEnabled(False)
        self.clear_btn.setEnabled(False) 
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        self.analysis_thread = GPSAnalysisThread(self.current_files)
        
        self.analysis_thread.progress_update.connect(self.update_progress)
        self.analysis_thread.analysis_complete.connect(self.analysis_finished)
        self.analysis_thread.start()
        
        self.results_text.setPlainText(f"Rozpoczynam analizę {len(self.current_files)} plik(ów)...")
        
    def update_progress(self, value):
        """Aktualizuje pasek postępu"""
        self.progress_bar.setValue(value)
        
    def analysis_finished(self, points):
        """Wywoływane po zakończeniu analizy"""
        self.analyze_btn.setEnabled(True)
        self.clear_btn.setEnabled(True) 
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
Przeanalizowano plików: {len(self.current_files)}
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
        self.results_text.setPlainText("Markery i ślad zostały wyczyszczone.")
        

    def run_simulation_script(self):
            """Uruchamia zewnętrzny skrypt Pythona do generowania symulacji."""
            python_executable = sys.executable
            
            try:
                current_dir = os.path.dirname(__file__)
            except NameError:
                current_dir = os.getcwd() 
                
            script_path = os.path.normpath(
                os.path.join(current_dir, "..", "..", "simulate", "frontend", "gnss_frontend.py")
            )
            command = [python_executable, script_path]
            self.results_text.setPlainText(f"Uruchamianie skryptu symulacyjnego:\n{script_path}...")
            
            try:
                if not os.path.exists(script_path):
                    raise FileNotFoundError(f"Plik skryptu nie istnieje: {script_path}")
                
                subprocess.Popen(command)
                self.results_text.append("\nSkrypt został pomyślnie uruchomiony.")
                
            except FileNotFoundError as fnf_error:
                self.results_text.setPlainText(f"BŁĄD: Nie znaleziono skryptu lub interpretera.\n"
                                            f"Błąd: {fnf_error}\n"
                                            f"Sprawdzana ścieżka: {script_path}\n"
                                            f"Interpreter: {python_executable}")
            except Exception as e:
                self.results_text.setPlainText(f"BŁĄD podczas uruchamiania skryptu:\n{e}")