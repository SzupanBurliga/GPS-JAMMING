from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, 
                             QLabel, QDoubleSpinBox, QSpinBox, 
                             QPushButton, QGroupBox, QGridLayout, QMessageBox)
from PySide6.QtCore import Qt
import os

class SettingsDialog(QDialog):
    def __init__(self, parent=None, num_files=0, file_paths=None):
        super().__init__(parent)
        self.setWindowTitle("Ustawienia Analizy GPS")
        self.setModal(True)
        self.resize(400, 350)
        self.num_files = num_files
        self.file_paths = file_paths if file_paths else []
        
        self.setStyleSheet("""
        QDialog {
            background-color: #ecf0f1;
        }
        QLabel {
            color: #2c3e50;
            font-size: 12px;
            font-weight: bold;
        }
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
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        antenna_group = QGroupBox("Pozycje anten względem Anteny 1 [metry]")
        antenna_layout = QGridLayout(antenna_group)
        
        antenna_layout.addWidget(QLabel("<b>Antena</b>"), 0, 0)
        antenna_layout.addWidget(QLabel("<b>X [m]</b>"), 0, 1)
        antenna_layout.addWidget(QLabel("<b>Y [m]</b>"), 0, 2)

        self.antenna1_label = QLabel("Antena 1 (ref):")
        antenna_layout.addWidget(self.antenna1_label, 1, 0)
        self.antenna1_x_label = QLabel("0.0")
        antenna_layout.addWidget(self.antenna1_x_label, 1, 1)
        self.antenna1_y_label = QLabel("0.0")
        antenna_layout.addWidget(self.antenna1_y_label, 1, 2)
        self.antenna2_label = QLabel("Antena 2:")
        antenna_layout.addWidget(self.antenna2_label, 2, 0)
        self.antenna2_x = QDoubleSpinBox()
        self.antenna2_x.setRange(-50.0, 50.0)
        self.antenna2_x.setValue(0.5)
        self.antenna2_x.setDecimals(3)
        self.antenna2_x.setSuffix(" m")
        self.antenna2_x.setStyleSheet(self.get_spinbox_style())
        antenna_layout.addWidget(self.antenna2_x, 2, 1)
        self.antenna2_y = QDoubleSpinBox()
        self.antenna2_y.setRange(-50.0, 50.0)
        self.antenna2_y.setValue(0.0)
        self.antenna2_y.setDecimals(3)
        self.antenna2_y.setSuffix(" m")
        self.antenna2_y.setStyleSheet(self.get_spinbox_style())
        antenna_layout.addWidget(self.antenna2_y, 2, 2)
        
        self.antenna3_label = QLabel("Antena 3:")
        antenna_layout.addWidget(self.antenna3_label, 3, 0)
        self.antenna3_x = QDoubleSpinBox()
        self.antenna3_x.setRange(-50.0, 50.0)
        self.antenna3_x.setValue(0.0)  
        self.antenna3_x.setDecimals(3)
        self.antenna3_x.setSuffix(" m")
        self.antenna3_x.setStyleSheet(self.get_spinbox_style())
        antenna_layout.addWidget(self.antenna3_x, 3, 1)
        
        self.antenna3_y = QDoubleSpinBox()
        self.antenna3_y.setRange(-50.0, 50.0)
        self.antenna3_y.setValue(0.5)
        self.antenna3_y.setDecimals(3)
        self.antenna3_y.setSuffix(" m")
        self.antenna3_y.setStyleSheet(self.get_spinbox_style())
        antenna_layout.addWidget(self.antenna3_y, 3, 2)
        
        self.update_antenna_state()
        
        layout.addWidget(antenna_group)

        analysis_group = QGroupBox("Parametry Analizy")
        analysis_layout = QGridLayout(analysis_group)
        analysis_layout.setVerticalSpacing(15)

        analysis_layout.addWidget(QLabel("Częstotliwość:"), 0, 0)
        analysis_layout.addWidget(QLabel("1575.42 MHz"), 0, 1)

        analysis_layout.addWidget(QLabel("Częstotliwość próbkowania:"), 1, 0)
        analysis_layout.addWidget(QLabel("2.048 MHz"), 1, 1)

        analysis_layout.addWidget(QLabel("Próg Detekcji (względny):"), 2, 0)
        self.threshold = QDoubleSpinBox()
        self.threshold.setRange(1.0, 5000.0)
        self.threshold.setValue(120.0)
        self.threshold.setDecimals(1)
        self.threshold.setSingleStep(1.0)
        self.threshold.setStyleSheet(self.get_spinbox_style())
        analysis_layout.addWidget(self.threshold, 2, 1)
        
        self.calibrate_btn = QPushButton("Oblicz próg")
        self.calibrate_btn.clicked.connect(self.on_calibrate_clicked)
        self.calibrate_btn.setStyleSheet("""
        QPushButton {
            background-color: #3498db;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 10px 20px;
            font-size: 13px;
            font-weight: bold;
            margin-top: 10px;
        }
        QPushButton:hover {
            background-color: #2980b9;
            box-shadow: 0 3px 6px rgba(0,0,0,0.2);
        }
        QPushButton:pressed {
            background-color: #21618c;
        }
        """)
        analysis_layout.addWidget(self.calibrate_btn, 3, 0, 1, 2)
        
        layout.addWidget(analysis_group)
        
        button_layout = QHBoxLayout()
        
        self.ok_btn = QPushButton("Zapisz")
        self.ok_btn.clicked.connect(self.accept)
        self.ok_btn.setStyleSheet("""
        QPushButton {
            background-color: #27ae60;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 12px 20px;
            font-size: 14px;
            font-weight: bold;
            margin: 5px;
        }
        QPushButton:hover {
            background-color: #2ecc71;
            box-shadow: 0 3px 6px rgba(0,0,0,0.2);
        }
        QPushButton:pressed {
            background-color: #229954;
        }
        """)
        
        self.cancel_btn = QPushButton("Anuluj")
        self.cancel_btn.clicked.connect(self.reject)
        self.cancel_btn.setStyleSheet("""
        QPushButton {
            background-color: #e74c3c;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 12px 20px;
            font-size: 14px;
            font-weight: bold;
            margin: 5px;
        }
        QPushButton:hover {
            background-color: #c0392b;
            box-shadow: 0 3px 6px rgba(0,0,0,0.2);
        }
        QPushButton:pressed {
            background-color: #a93226;
        }
        """)
        
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.ok_btn)
        
        layout.addLayout(button_layout)
    
    def on_calibrate_clicked(self):
        """Obsługa kliknięcia przycisku Kalibruj."""
        if self.num_files == 0:
            QMessageBox.warning(self, "Brak plików", "Brak plików do kalibracji")
        elif self.num_files >= 1:
            import subprocess
            import re
            
            first_file = self.file_paths[0]
            script_path = os.path.join(os.path.dirname(__file__), 'checkIfJamming.py')
            
            try:
                result = subprocess.run(
                    ['python', script_path, first_file, '--kalibruj'],
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                
                output = result.stdout
                print(output)
                
                match = re.search(r'Sugerowany <próg_mocy> \(Mediana \* 4\.8\):\s*([\d.]+)', output)
                
                if match:
                    suggested_threshold = float(match.group(1))
                    self.threshold.setValue(suggested_threshold)
                    QMessageBox.information(
                        self, 
                        "Kalibracja zakończona", 
                        f"Obliczony próg detekcji: {suggested_threshold:.2f}\n\n"
                        f"Wartość została automatycznie wpisana."
                    )
                else:
                    QMessageBox.warning(
                        self, 
                        "Błąd kalibracji", 
                        "Nie udało się odczytać wartości progu z wyniku kalibracji."
                    )
                    
            except subprocess.TimeoutExpired:
                QMessageBox.critical(self, "Błąd", "Kalibracja przekroczyła limit czasu (120s)")
            except Exception as e:
                QMessageBox.critical(self, "Błąd", f"Błąd podczas kalibracji:\n{str(e)}")
    
    def update_antenna_state(self):
        disabled_label_style = "color: #95a5a6;"
        enabled_label_style = "color: #2c3e50; font-weight: bold;"
        
        if self.num_files == 0:
            self.antenna1_label.setStyleSheet(disabled_label_style)
            self.antenna1_x_label.setStyleSheet(disabled_label_style)
            self.antenna1_y_label.setStyleSheet(disabled_label_style)
            self.antenna2_label.setStyleSheet(disabled_label_style)
            self.antenna3_label.setStyleSheet(disabled_label_style)
            self.antenna2_x.setEnabled(False)
            self.antenna2_y.setEnabled(False)
            self.antenna3_x.setEnabled(False)
            self.antenna3_y.setEnabled(False)
        elif self.num_files == 1:
            self.antenna1_label.setStyleSheet(enabled_label_style)
            self.antenna1_x_label.setStyleSheet(enabled_label_style)
            self.antenna1_y_label.setStyleSheet(enabled_label_style)
            self.antenna2_label.setStyleSheet(disabled_label_style)
            self.antenna3_label.setStyleSheet(disabled_label_style)
            self.antenna2_x.setEnabled(False)
            self.antenna2_y.setEnabled(False)
            self.antenna3_x.setEnabled(False)
            self.antenna3_y.setEnabled(False)
        elif self.num_files == 2:
            self.antenna1_label.setStyleSheet(enabled_label_style)
            self.antenna1_x_label.setStyleSheet(enabled_label_style)
            self.antenna1_y_label.setStyleSheet(enabled_label_style)
            self.antenna2_label.setStyleSheet(enabled_label_style)
            self.antenna3_label.setStyleSheet(disabled_label_style)
            self.antenna2_x.setEnabled(True)
            self.antenna2_y.setEnabled(True)
            self.antenna3_x.setEnabled(False)
            self.antenna3_y.setEnabled(False)
        else:
            self.antenna1_label.setStyleSheet(enabled_label_style)
            self.antenna1_x_label.setStyleSheet(enabled_label_style)
            self.antenna1_y_label.setStyleSheet(enabled_label_style)
            self.antenna2_label.setStyleSheet(enabled_label_style)
            self.antenna3_label.setStyleSheet(enabled_label_style)
            self.antenna2_x.setEnabled(True)
            self.antenna2_y.setEnabled(True)
            self.antenna3_x.setEnabled(True)
            self.antenna3_y.setEnabled(True)
    
    def get_spinbox_style(self):
        return """
        QDoubleSpinBox, QSpinBox {
            border: 2px solid #bdc3c7;
            border-radius: 5px;
            padding: 8px;
            font-size: 13px;
            background-color: white;
            color: #2c3e50;
            min-width: 100px;
        }
        QDoubleSpinBox:focus, QSpinBox:focus {
            border-color: #3498db;
        }
        QDoubleSpinBox:disabled, QSpinBox:disabled {
            background-color: #ecf0f1;
            color: #95a5a6;
            border-color: #bdc3c7;
        }
        """
    
    def get_settings(self):
        import math

        antenna_positions = {
            'antenna1': [0.0, 0.0],
            'antenna2': [self.antenna2_x.value(), self.antenna2_y.value()],
            'antenna3': [self.antenna3_x.value(), self.antenna3_y.value()]
        }
        
        def calculate_distance(pos1, pos2):
            return math.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)
        
        distance_12 = calculate_distance(antenna_positions['antenna1'], antenna_positions['antenna2'])
        distance_13 = calculate_distance(antenna_positions['antenna1'], antenna_positions['antenna3'])
        distance_23 = calculate_distance(antenna_positions['antenna2'], antenna_positions['antenna3'])
        
        return {
            'antenna_positions': antenna_positions,
            'antenna_distances': {
                '1_to_2': distance_12,
                '1_to_3': distance_13,
                '2_to_3': distance_23
            },
            'analysis_params': {
                'frequency': 1575.42,
                'threshold': int(self.threshold.value()),
                'sample_rate': 2.048
            }
        }
    
    def set_settings(self, settings):
        if 'antenna_positions' in settings:
            positions = settings['antenna_positions']
            antenna2_pos = positions.get('antenna2', [0.5, 0.0])
            antenna3_pos = positions.get('antenna3', [0.0, 0.5])
            
            self.antenna2_x.setValue(antenna2_pos[0])
            self.antenna2_y.setValue(antenna2_pos[1])
            self.antenna3_x.setValue(antenna3_pos[0])
            self.antenna3_y.setValue(antenna3_pos[1])
        
        if 'analysis_params' in settings:
            params = settings['analysis_params']
            threshold_value = params.get('threshold', 120)
            self.threshold.setValue(float(threshold_value))