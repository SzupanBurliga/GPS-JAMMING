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
        self.main_layout = QHBoxLayout(main_widget)

        self.control_panel = self.create_control_panel()
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
            print("BŁĄD: Nie można załadować pliku z mapa!")
            self.web_view.setHtml("<h1>Błąd: Nie znaleziono pliku map_template.html</h1>")

        self.main_layout.addWidget(self.control_panel, 0)
        self.main_layout.addWidget(self.web_view, 0)

        self.update_layout_proportions()
 
        self.analysis_thread = None
        self.is_map_centered = False
        self.selected_satellite_system = 'GPS'  # domyslny system
        self.jammer_shown = False
        
        # Parametry dla różnych systemów satelitarnych
        self.satellite_params = {
            'GPS': {
                'frequency': 1575.42,
                'sample_rate': 2.048,
                'band': 'GPS L1'
            },
            'GLONASS': {
                'frequency': 1602.00,
                'sample_rate': 10.00,
                'band': 'GLONASS G1'
            },
            'Galileo': {
                'frequency': 1575.42,
                'sample_rate': 2.048,
                'band': 'Galileo E1'
            }
        }
        
        # domyslne ustawienia
        self.current_settings = {
            'antenna_positions': {
                'antenna1': [0.0, 0.0],   
                'antenna2': [0.5, 0.0],   
                'antenna3': [0.0, 0.5]    
            },
            'antenna_distances': {
                '1_to_2': 0.5,
                '1_to_3': 0.5,
                '2_to_3': 0.707
            },
            'analysis_params': {
                'frequency': 1575.42,
                'threshold': 120,
                'sample_rate': 2.048
            }
        }
        
        # Ustaw początkowy komunikat dla domyślnego systemu GPS
        self.update_satellite_system_display()
        
    def update_satellite_system_display(self):
        """Aktualizuje wyświetlanie informacji o wybranym systemie satelitarnym."""
        params = self.satellite_params[self.selected_satellite_system]
        message = (
            f"🛰️ Wybrano system satelitarny: {self.selected_satellite_system}\n"
            f"   Ustawienia dla {params['band']}\n"
            f"   Częstotliwość: {params['frequency']:.2f} MHz\n"
            f"   Częstotliwość próbkowania: {params['sample_rate']:.3f} MHz"
        )
        self.results_text.setPlainText(message)
        
    def create_control_panel(self):
        control_panel = QWidget()
        control_panel.setMaximumWidth(600)
        control_panel.setMinimumWidth(450)
        control_panel.setStyleSheet("""
        QWidget {
            background-color: #f8f9fa;
            border-right: 2px solid #dee2e6;
        }
        """)  

        button_style = """
        QPushButton {
            background-color: #2c3e50;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 12px 16px;
            font-size: 14px;
            font-weight: bold;
            margin: 3px;
            min-height: 20px;
        }
        QPushButton:hover {
            background-color: #34495e;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            transform: translateY(-1px);
        }
        QPushButton:pressed {
            background-color: #1a252f;
            transform: translateY(0px);
        }
        QPushButton:disabled {
            background-color: #7f8c8d;
            color: #bdc3c7;
        }
        """

        osm_button_style = """
        QPushButton {
            background-color: #3498db;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 10px;
            font-size: 13px;
            font-weight: bold;
            margin: 2px;
        }
        QPushButton:hover {
            background-color: #2980b9;
            box-shadow: 0 3px 6px rgba(0,0,0,0.2);
        }
        QPushButton:pressed, QPushButton:checked {
            background-color: #21618c;
            box-shadow: inset 0 3px 5px rgba(0,0,0,0.3);
        }
        """

        satellite_button_style = """
        QPushButton {
            background-color: #9b59b6;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 10px;
            font-size: 13px;
            font-weight: bold;
            margin: 2px;
        }
        QPushButton:hover {
            background-color: #8e44ad;
            box-shadow: 0 3px 6px rgba(0,0,0,0.2);
        }
        QPushButton:pressed, QPushButton:checked {
            background-color: #71368a;
            box-shadow: inset 0 3px 5px rgba(0,0,0,0.3);
        }
        """

        topo_button_style = """
        QPushButton {
            background-color: #16a085;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 10px;
            font-size: 13px;
            font-weight: bold;
            margin: 2px;
        }
        QPushButton:hover {
            background-color: #138d75;
            box-shadow: 0 3px 6px rgba(0,0,0,0.2);
        }
        QPushButton:pressed, QPushButton:checked {
            background-color: #117a65;
            box-shadow: inset 0 3px 5px rgba(0,0,0,0.3);
        }
        """

        gps_button_style = """
        QPushButton {
            background-color: #27ae60;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 10px;
            font-size: 13px;
            font-weight: bold;
            margin: 2px;
        }
        QPushButton:hover {
            background-color: #229954;
            box-shadow: 0 3px 6px rgba(0,0,0,0.2);
        }
        QPushButton:pressed, QPushButton:checked {
            background-color: #1e8449;
            box-shadow: inset 0 3px 5px rgba(0,0,0,0.3);
        }
        """
        glonass_button_style = """
        QPushButton {
            background-color: #3498db;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 10px;
            font-size: 13px;
            font-weight: bold;
            margin: 2px;
        }
        QPushButton:hover {
            background-color: #2980b9;
            box-shadow: 0 3px 6px rgba(0,0,0,0.2);
        }
        QPushButton:pressed, QPushButton:checked {
            background-color: #21618c;
            box-shadow: inset 0 3px 5px rgba(0,0,0,0.3);
        }
        """

        galileo_button_style = """
        QPushButton {
            background-color: #9b59b6;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 10px;
            font-size: 13px;
            font-weight: bold;
            margin: 2px;
        }
        QPushButton:hover {
            background-color: #8e44ad;
            box-shadow: 0 3px 6px rgba(0,0,0,0.2);
        }
        QPushButton:pressed, QPushButton:checked {
            background-color: #71368a;
            box-shadow: inset 0 3px 5px rgba(0,0,0,0.3);
        }
        """

        action_button_style = """
        QPushButton {
            background-color: #27ae60;
            color: white;
            border: none;
            border-radius: 10px;
            padding: 15px 20px;
            font-size: 15px;
            font-weight: bold;
            margin: 4px;
            min-height: 25px;
        }
        QPushButton:hover {
            background-color: #2ecc71;
            box-shadow: 0 4px 8px rgba(0,0,0,0.25);
            transform: translateY(-2px);
        }
        QPushButton:pressed {
            background-color: #229954;
            transform: translateY(0px);
        }
        """

        danger_button_style = """
        QPushButton {
            background-color: #e74c3c;
            color: white;
            border: none;
            border-radius: 10px;
            padding: 12px 16px;
            font-size: 14px;
            font-weight: bold;
            margin: 3px;
            min-height: 20px;
        }
        QPushButton:hover {
            background-color: #c0392b;
            box-shadow: 0 3px 6px rgba(0,0,0,0.2);
            transform: translateY(-1px);
        }
        QPushButton:pressed {
            background-color: #a93226;
            transform: translateY(0px);
        }
        """

        test_button_style = """
        QPushButton {
            background-color: #f39c12;
            color: white;
            border: none;
            border-radius: 10px;
            padding: 12px 16px;
            font-size: 14px;
            font-weight: bold;
            margin: 3px;
            min-height: 20px;
        }
        QPushButton:hover {
            background-color: #e67e22;
            box-shadow: 0 3px 6px rgba(0,0,0,0.2);
            transform: translateY(-1px);
        }
        QPushButton:pressed {
            background-color: #d68910;
            transform: translateY(0px);
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
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        map_group = QGroupBox("Typ Mapy")
        map_group.setStyleSheet(group_style)
        map_layout = QHBoxLayout(map_group) 
        
        self.osm_btn = QPushButton("🗺️ OSM")
        self.osm_btn.setCheckable(True)
        self.osm_btn.setChecked(True)
        self.osm_btn.clicked.connect(lambda: self.change_map_layer('osm'))
        self.osm_btn.setStyleSheet(osm_button_style)
        map_layout.addWidget(self.osm_btn)
        
        self.satellite_btn = QPushButton("🛰️ Satelita")
        self.satellite_btn.setCheckable(True)
        self.satellite_btn.clicked.connect(lambda: self.change_map_layer('satellite'))
        self.satellite_btn.setStyleSheet(satellite_button_style)
        map_layout.addWidget(self.satellite_btn)
        
        self.topo_btn = QPushButton("🏔️ Topo")
        self.topo_btn.setCheckable(True)
        self.topo_btn.clicked.connect(lambda: self.change_map_layer('topo'))
        self.topo_btn.setStyleSheet(topo_button_style)
        map_layout.addWidget(self.topo_btn)
        layout.addWidget(map_group)

        satellite_system_group = QGroupBox("System Satelitarny")
        satellite_system_group.setStyleSheet(group_style)
        satellite_system_layout = QHBoxLayout(satellite_system_group)
        
        self.gps_btn = QPushButton("🇺🇸 GPS")
        self.gps_btn.setCheckable(True)
        self.gps_btn.setChecked(True)
        self.gps_btn.clicked.connect(lambda: self.select_satellite_system('GPS'))
        self.gps_btn.setStyleSheet(gps_button_style)
        satellite_system_layout.addWidget(self.gps_btn)

        self.glonass_btn = QPushButton("🇷🇺 GLONASS")
        self.glonass_btn.setCheckable(True)
        self.glonass_btn.clicked.connect(lambda: self.select_satellite_system('GLONASS'))
        self.glonass_btn.setStyleSheet(glonass_button_style)
        satellite_system_layout.addWidget(self.glonass_btn)
        
        self.galileo_btn = QPushButton("🇪🇺 Galileo")
        self.galileo_btn.setCheckable(True)
        self.galileo_btn.clicked.connect(lambda: self.select_satellite_system('Galileo'))
        self.galileo_btn.setStyleSheet(galileo_button_style)
        satellite_system_layout.addWidget(self.galileo_btn)
        
        layout.addWidget(satellite_system_group)

        analysis_group = QGroupBox("Analiza Sygnałów")
        analysis_group.setStyleSheet(group_style)
        analysis_layout = QVBoxLayout(analysis_group)

        self.file_display = QTextEdit()
        self.file_display.setReadOnly(True)
        self.file_display.setPlaceholderText("Brak wybranych plików...")
        self.file_display.setMaximumHeight(90)
        self.file_display.setStyleSheet("""
        QTextEdit {
            border: 2px solid #bdc3c7;
            border-radius: 10px;
            padding: 12px;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            background-color: white;
            color: #2c3e50;
            margin: 2px;
        }
        QTextEdit:focus {
            border-color: #3498db;
        }
        """)
        analysis_layout.addWidget(self.file_display)
        
        self.browse_btn = QPushButton("📁 Wybierz pliki (maks. 3)") 
        self.browse_btn.clicked.connect(self.browse_files) 
        self.browse_btn.setStyleSheet(button_style)
        analysis_layout.addWidget(self.browse_btn)
        self.settings_btn = QPushButton("⚙️ Ustawienia")
        self.settings_btn.clicked.connect(self.open_settings)
        self.settings_btn.setStyleSheet(button_style)
        analysis_layout.addWidget(self.settings_btn)

        self.analyze_btn = QPushButton("🔍 Rozpocznij Analizę")
        self.analyze_btn.clicked.connect(self.start_analysis)
        self.analyze_btn.setStyleSheet(action_button_style)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFormat("Gotowy do analizy")
        self.progress_bar.setStyleSheet("""
        QProgressBar {
            border: 2px solid #bdc3c7;
            border-radius: 8px;
            text-align: center;
            font-weight: bold;
            background-color: #ecf0f1;
            color: #2c3e50;
            font-size: 13px;
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
        
        layout.addWidget(action_group)

        results_group = QGroupBox("Wyniki Analizy")
        results_group.setStyleSheet(group_style)
        results_layout = QVBoxLayout(results_group)
        
        self.results_text = QTextEdit()
        self.results_text.setMaximumHeight(300)
        self.results_text.setPlainText("Brak danych do analizy...")
        self.results_text.setStyleSheet("""
        QTextEdit {
            border: 2px solid #bdc3c7;
            border-radius: 10px;
            padding: 12px;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            background-color: #2c3e50;
            color: #ecf0f1;
            margin: 2px;
        }
        QTextEdit:focus {
            border-color: #3498db;
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
        
        return control_panel

    def update_layout_proportions(self):
        window_width = self.width()
        
        if window_width < 1000:
            self.main_layout.setStretch(0, 45)
            self.main_layout.setStretch(1, 55)
            self.control_panel.setMaximumWidth(500)
            self.control_panel.setMinimumWidth(400)
        elif window_width < 1300:
            self.main_layout.setStretch(0, 42)
            self.main_layout.setStretch(1, 58) 
            self.control_panel.setMaximumWidth(550)
            self.control_panel.setMinimumWidth(420)
        else:
            self.main_layout.setStretch(0, 40)  
            self.main_layout.setStretch(1, 60)  
            self.control_panel.setMaximumWidth(600)
            self.control_panel.setMinimumWidth(450)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_layout_proportions()
        
    def change_map_layer(self, layer_type):
        # Odznacz wszystkie przyciski map
        self.osm_btn.setChecked(False)
        self.satellite_btn.setChecked(False)
        self.topo_btn.setChecked(False)
        
        # Zaznacz aktywny przycisk
        if layer_type == 'osm':
            self.osm_btn.setChecked(True)
        elif layer_type == 'satellite':
            self.satellite_btn.setChecked(True)
        elif layer_type == 'topo':
            self.topo_btn.setChecked(True)
        
        self.web_view.page().runJavaScript(f"changeMapLayer('{layer_type}');")
    
    def select_satellite_system(self, system):
        self.gps_btn.setChecked(False)
        self.glonass_btn.setChecked(False)
        self.galileo_btn.setChecked(False)

        if system == 'GPS':
            self.gps_btn.setChecked(True)
            self.selected_satellite_system = 'GPS'
        elif system == 'GLONASS':
            self.glonass_btn.setChecked(True)
            self.selected_satellite_system = 'GLONASS'
        elif system == 'Galileo':
            self.galileo_btn.setChecked(True)
            self.selected_satellite_system = 'Galileo'
        
        # Aktualizuj parametry analizy w ustawieniach
        params = self.satellite_params[self.selected_satellite_system]
        self.current_settings['analysis_params']['frequency'] = params['frequency']
        self.current_settings['analysis_params']['sample_rate'] = params['sample_rate']
        
        print(f"Wybrany system satelitarny: {self.selected_satellite_system}")
        
        # Wyświetl szczegółowy komunikat w panelu wyników
        self.update_satellite_system_display()
    
    def open_settings(self):
        try:
            from .settings_dialog import SettingsDialog
            num_files = len(self.current_files) if hasattr(self, 'current_files') else 0
            file_paths = self.current_files if hasattr(self, 'current_files') else []
            dialog = SettingsDialog(self, num_files=num_files, file_paths=file_paths)

            dialog.set_settings(self.current_settings)
            
            if dialog.exec():
                settings = dialog.get_settings()
                self.apply_settings(settings)
                print(f"Nowe ustawienia: {settings}")

                positions = settings['antenna_positions']
                distances = settings['antenna_distances']
                
                info_text = (
                    f"⚙️ USTAWIENIA ZAKTUALIZOWANE:\n"
                    f"Pozycje anten:\n"
                    f"   Antena 1: (0.0, 0.0) m [ref]\n"
                    f"   Antena 2: ({positions['antenna2'][0]:.3f}, {positions['antenna2'][1]:.3f}) m\n"
                    f"   Antena 3: ({positions['antenna3'][0]:.3f}, {positions['antenna3'][1]:.3f}) m\n"
                    f"Parametry: {settings['analysis_params']['frequency']:.2f} MHz, próg {settings['analysis_params']['threshold']}"
                )
                
                self.results_text.setPlainText(info_text)
        except ImportError as e:
            self.results_text.setPlainText(f"Błąd importu okna ustawień: {e}")
    
    def apply_settings(self, settings):
        self.current_settings = settings
        print(f"Zastosowano ustawienia: {settings}")
        
    def browse_files(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, 
            "Wybierz pliki z danymi GPS (maks. 3)", 
            "../data/", 
            "Pliki binarne (*.bin);;Wszystkie pliki (*.*)"
        )
        
        if file_paths:
            if len(file_paths) > 3:
                self.results_text.setPlainText("BŁĄD: Możesz wybrać maksymalnie 3 pliki.")
                if hasattr(self, 'current_files'):
                    self.current_files.clear()
                self.file_display.setPlainText("Wybierz maksymalnie 3 pliki.")
                return 
            file_paths_sorted = sorted(file_paths, key=lambda x: os.path.basename(x).lower())
            self.current_files = file_paths_sorted
            basenames = [os.path.basename(p) for p in file_paths_sorted]
            self.file_display.setPlainText("\n".join(basenames))
        
    def start_analysis(self):
        if not hasattr(self, 'current_files') or not self.current_files:
            self.results_text.setPlainText("Najpierw wybierz plik(i) do analizy!")
            return
            
        if self.analysis_thread and self.analysis_thread.isRunning():
            self.results_text.setPlainText("Analiza już trwa...")
            return

        self.clear_markers_silently()
        self.jammer_shown = False
        self.analyze_btn.setEnabled(False) 
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.results_text.setPlainText(f"Rozpoczynam analizę {len(self.current_files)} plik(ów)...\n🛰️ System satelitarny: {self.selected_satellite_system}\n")
        self.analysis_thread = GPSAnalysisThread(
            self.current_files, 
            power_threshold=self.current_settings['analysis_params'].get('threshold', 120.0),
            antenna_positions=self.current_settings.get('antenna_positions'),
            satellite_system=self.selected_satellite_system
        )
        self.analysis_thread.progress_update.connect(self.update_progress)
        self.analysis_thread.analysis_complete.connect(self.analysis_finished)
        self.analysis_thread.new_position_data.connect(self.update_map_position)
        self.analysis_thread.new_analysis_text.connect(self.update_analysis_text)
        self.analysis_thread.triangulation_complete.connect(self.on_triangulation_result)
        
        self.analysis_thread.start()
    
    def update_analysis_text(self, text):
        current_text = self.results_text.toPlainText()
        updated_text = current_text + "\n" + text
        lines = updated_text.split('\n')
        if len(lines) > 50:
            lines = lines[-50:]
            updated_text = '\n'.join(lines)
        
        self.results_text.setPlainText(updated_text)
        scrollbar = self.results_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
 
 # Ustawienia progress baru
    def update_progress(self, value, state="normal"):
        self.progress_bar.setValue(value)

        if state == "jamming":
            self.progress_bar.setFormat("🚨 Znaleziono jamming, analizowanie...")
        elif state == "triangulating":
            self.progress_bar.setFormat("📐 Triangulacja - obliczanie lokalizacji jammera...")
        elif state == "completed":
            self.progress_bar.setFormat("Analiza zakończona - 100%")

            try:
                if hasattr(self, 'analysis_thread') and self.analysis_thread:
                    tri = self.analysis_thread.get_triangulation_result()
                    if tri and tri.get('success') and not getattr(self, 'jammer_shown', False):
                        self.on_triangulation_result(tri)
                        self.jammer_shown = True
            except Exception as e:
                print(f"[UI] Błąd przy próbie pokazania pozycji jammera po zakończeniu analizy: {e}")

        elif value > 0:
            self.progress_bar.setFormat(f"Analiza: {value}%")
        else:
            self.progress_bar.setFormat("Przygotowanie analizy...")
        
    def update_map_position(self, lat, lon):
        if not self.is_map_centered:
            js_pan_code = f"map.setView([{lat:.8f}, {lon:.8f}], 19);"
            self.web_view.page().runJavaScript(js_pan_code)
            self.is_map_centered = True 

        js_draw_code = f"updateLivePosition({lat:.8f}, {lon:.8f});"
        self.web_view.page().runJavaScript(js_draw_code)

    def on_triangulation_result(self, result):
        if result['success']:
            geo = result['location_geographic']
            distances = result['distances']
            ref_pos = result.get('reference_position')
            
            if ref_pos:
                ref_lat = ref_pos['lat']
                ref_lon = ref_pos['lon']
                print(f"[UI] Używam pozycji referencyjnej: {ref_lat:.6f}, {ref_lon:.6f}")
            else:
                ref_lat = geo['lat']
                ref_lon = geo['lon']
                print(f"[UI] Fallback do pozycji geo: {ref_lat:.6f}, {ref_lon:.6f}")
            
            js_add_jammer = f"""
            var jammerMarker = L.marker([{geo['lat']}, {geo['lon']}], {{
                icon: L.icon({{
                    iconUrl: 'data:image/svg+xml;charset=UTF-8,<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24"><circle cx="12" cy="12" r="10" fill="red" stroke="darkred" stroke-width="2"/><text x="12" y="16" text-anchor="middle" fill="white" font-size="10" font-weight="bold">JAM</text></svg>', 
                    iconSize: [20, 20],
                    iconAnchor: [8, 8]
                }})
            }}).addTo(map);
            jammerMarker.bindPopup('POZYCJA JAMMERA<br/>Lat: {geo['lat']:.8f}N<br/>Lon: {geo['lon']:.8f}E<br/>Wykryty triangulacja');
            
            // Wyśrodkuj mapę na pozycji jammera
            map.setView([{geo['lat']}, {geo['lon']}], 18);
            """
            self.web_view.page().runJavaScript(js_add_jammer)
            if hasattr(self, 'current_files') and len(self.current_files) >= 2:
                # Pozycje anten względem punktu referencyjnego (w metrach) - pobierz z ustawień
                settings_positions = self.current_settings.get('antenna_positions', {})
                antenna_positions = [
                    settings_positions.get('antenna1', [0.0, 0.0]),
                    settings_positions.get('antenna2', [0.5, 0.0]),
                    settings_positions.get('antenna3', [0.0, 0.5]) if len(self.current_files) == 3 else None
                ]

                for i, (ant_pos, distance) in enumerate(zip(antenna_positions, distances)):
                    if ant_pos is not None and distance is not None:
                        lat_offset = ant_pos[1] / 111320.0  
                        lon_offset = ant_pos[0] / (111320.0 * abs(ref_lat / 90.0)) 
                        antenna_lat = ref_lat + lat_offset
                        antenna_lon = ref_lon + lon_offset

                        js_add_circle = f"""
                        var circle{i} = L.circle([{antenna_lat}, {antenna_lon}], {{
                            color: 'red',
                            fillColor: 'rgba(255, 0, 0, 0.1)',
                            fillOpacity: 0.4,
                            radius: {distance}
                        }}).addTo(map);
                        circle{i}.bindPopup('Antena {i+1}<br/>Szacowana odległość {distance:.1f}m');
                        """
                        self.web_view.page().runJavaScript(js_add_circle)

            triangulation_text = (
                f"\n TRIANGULACJA ZAKOŃCZONA:\n"
                f"  Pozycja jammera: {geo['lat']:.8f}, {geo['lon']:.8f}\n"
                f"  Odległości od anten: {[f'{d:.1f}m' for d in distances if d is not None]}\n"
                f"  Metoda: {result['num_antennas']}-antenna triangulation"
            )
            
            current_text = self.results_text.toPlainText()
            self.results_text.setPlainText(current_text + triangulation_text)

            scrollbar = self.results_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
        else:
            # gdy błąd triangulacji
            error_text = f"\n TRIANGULACJA NIEUDANA: {result['message']}"
            current_text = self.results_text.toPlainText()
            self.results_text.setPlainText(current_text + error_text)

    def analysis_finished(self, points):
        self.analyze_btn.setEnabled(True) 

        if points and len(points) > 0:
            result = points[0]
            if result.get('type') == 'jamming':
                start_sample = result.get('start_sample')
                end_sample = result.get('end_sample')
                
                if end_sample is not None:
                    jamming_text = f"Znaleziono jamming"
                else:
                    jamming_text = f"Znaleziono jamming [{start_sample}, koniec pliku]"
                    
                self.results_text.setPlainText(jamming_text)
                triangulation = result.get('triangulation')
                if triangulation:
                    self.display_final_triangulation_result(triangulation)
                
                return
            
            elif result.get('type') == 'no_jamming':
                self.results_text.setPlainText("Nie znaleziono punktów zakłóceń lub błąd analizy.")
                triangulation = result.get('triangulation')
                if triangulation:
                    self.display_final_triangulation_result(triangulation)
                return
        
    def display_final_triangulation_result(self, triangulation):
        if triangulation and triangulation['success']:
            geo = triangulation['location_geographic']
            distances = triangulation['distances']
            final_text = (
                f"Lokalizacja jammera została określona\n"
                f"Współrzędne: {geo['lat']:.8f}, {geo['lon']:.8f}\n"
                f"Metoda: {triangulation['num_antennas']}-antenna triangulation\n"
                f"Dokładność: ±{max(distances) - min([d for d in distances if d]):.1f}m\n"
            )
            
            current_text = self.results_text.toPlainText()
            self.results_text.setPlainText(current_text + final_text)
        elif triangulation:
            error_text = f"\n\n TRIANGULACJA: {triangulation['message']}"
            current_text = self.results_text.toPlainText()
            self.results_text.setPlainText(current_text + error_text)

    def clear_markers_silently(self):
        self.web_view.page().runJavaScript("clearSignalMarkers();")
        js_clear_all = """
        map.eachLayer(function(layer) {
            if (layer instanceof L.Marker || layer instanceof L.Circle) {
                if (layer.options && !layer.options.attribution) {
                    map.removeLayer(layer);
                }
            }
        });
        """
        self.web_view.page().runJavaScript(js_clear_all)
        self.is_map_centered = False
  
    def run_simulation_script(self):
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
    