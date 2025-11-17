from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, 
                             QLabel, QDoubleSpinBox, QSpinBox, 
                             QPushButton, QGroupBox, QGridLayout, QTextEdit, QCheckBox, QLineEdit)
from PySide6.QtCore import Qt, QTimer, Signal, QObject
import subprocess
import threading
import time

class RecordingDialog(QDialog):
    log_signal = Signal(str)
    warmup_complete = Signal()
    update_timer = Signal(int) 
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nagrywanie Sygnałów SDR")
        self.setModal(True)
        self.resize(600, 700)
        
        self.recording_process = None
        self.recording_processes = []
        self.is_recording = False
        self.warmup_timer = None
        self.recording_start_time = None
        
        self.log_signal.connect(self._log_message_safe)
        self.warmup_complete.connect(self._warmup_finished)
        self.update_timer.connect(self._update_timer_display)
        
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

        params_group = QGroupBox("Parametry Nagrywania")
        params_layout = QGridLayout(params_group)
        params_layout.setVerticalSpacing(15)
        params_layout.addWidget(QLabel("Częstotliwość:"), 0, 0)
        self.frequency_spin = QDoubleSpinBox()
        self.frequency_spin.setRange(1000.0, 2000.0)
        self.frequency_spin.setValue(1575.42)
        self.frequency_spin.setDecimals(2)
        self.frequency_spin.setSuffix(" MHz")
        self.frequency_spin.setStyleSheet(self.get_spinbox_style())
        params_layout.addWidget(self.frequency_spin, 0, 1)
        
        params_layout.addWidget(QLabel("Częstotliwość próbkowania:"), 1, 0)
        self.sample_rate_spin = QDoubleSpinBox()
        self.sample_rate_spin.setRange(0.1, 20.0)
        self.sample_rate_spin.setDecimals(3)
        self.sample_rate_spin.setSingleStep(0.001)
        self.sample_rate_spin.setValue(round(2048.0 / 1000.0, 3))
        self.sample_rate_spin.setSuffix(" MHz")
        self.sample_rate_spin.setStyleSheet(self.get_spinbox_style())
        params_layout.addWidget(self.sample_rate_spin, 1, 1)
        
        params_layout.addWidget(QLabel("Ilość SDRów:"), 2, 0)
        self.num_sdrs_spin = QSpinBox()
        self.num_sdrs_spin.setRange(1, 3)
        self.num_sdrs_spin.setValue(1)
        self.num_sdrs_spin.setStyleSheet(self.get_spinbox_style())
        params_layout.addWidget(self.num_sdrs_spin, 2, 1)
        
        params_layout.addWidget(QLabel("Nazwa pliku:"), 3, 0)
        self.filename_edit = QLineEdit()
        self.filename_edit.setText("capture.bin")
        self.filename_edit.setStyleSheet("""
        QLineEdit {
            border: 2px solid #bdc3c7;
            border-radius: 5px;
            padding: 8px;
            font-size: 13px;
            background-color: white;
            color: #2c3e50;
            min-width: 120px;
        }
        QLineEdit:focus {
            border-color: #3498db;
        }
        QLineEdit:disabled {
            background-color: #ecf0f1;
            color: #95a5a6;
            border-color: #bdc3c7;
        }
        """)
        params_layout.addWidget(self.filename_edit, 3, 1)
        
        layout.addWidget(params_group)
        control_group = QGroupBox("Kontrola SDR")
        control_layout = QVBoxLayout(control_group)
        biast_layout = QHBoxLayout()
        biast_layout.addWidget(QLabel("BiasT:"))
        self.biast_checkbox = QCheckBox()
        self.biast_checkbox.setChecked(False)
        self.biast_checkbox.stateChanged.connect(self.toggle_biast)
        self.biast_checkbox.setStyleSheet("""
        QCheckBox {
            font-size: 13px;
            color: #2c3e50;
        }
        QCheckBox::indicator {
            width: 20px;
            height: 20px;
            border: 2px solid #bdc3c7;
            border-radius: 5px;
            background-color: white;
        }
        QCheckBox::indicator:checked {
            background-color: #3498db;
            border-color: #3498db;
        }
        """)
        biast_layout.addWidget(self.biast_checkbox)
        biast_layout.addWidget(QLabel(""))
        biast_layout.addStretch()
        control_layout.addLayout(biast_layout)

        self.warmup_btn = QPushButton("🔥 Nagrzej odbiornik(i) (60s)")
        self.warmup_btn.clicked.connect(self.warmup_receiver)
        self.warmup_btn.setStyleSheet("""
        QPushButton {
            background-color: #f39c12;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 12px 20px;
            font-size: 13px;
            font-weight: bold;
            margin: 5px;
        }
        QPushButton:hover {
            background-color: #e67e22;
            box-shadow: 0 3px 6px rgba(0,0,0,0.2);
        }
        QPushButton:pressed {
            background-color: #d68910;
        }
        QPushButton:disabled {
            background-color: #95a5a6;
            color: #bdc3c7;
        }
        """)
        control_layout.addWidget(self.warmup_btn)
        
        layout.addWidget(control_group)
        logs_group = QGroupBox("Logi Nagrywania")
        logs_layout = QVBoxLayout(logs_group)
        
        self.logs_text = QTextEdit()
        self.logs_text.setReadOnly(True)
        self.logs_text.setMaximumHeight(250)
        self.logs_text.setPlainText("Gotowy do nagrywania...\n")
        self.logs_text.setStyleSheet("""
        QTextEdit {
            border: 2px solid #bdc3c7;
            border-radius: 10px;
            padding: 12px;
            font-family: 'Courier New', monospace;
            font-size: 11px;
            background-color: #2c3e50;
            color: #ecf0f1;
            margin: 2px;
        }
        """)
        logs_layout.addWidget(self.logs_text)
        
        layout.addWidget(logs_group)
        
        button_layout = QVBoxLayout()
        
        self.record_toggle_btn = QPushButton("▶️ Włącz nagrywanie")
        self.record_toggle_btn.clicked.connect(self.toggle_recording)
        self.record_toggle_btn.setStyleSheet("""
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
        button_layout.addWidget(self.record_toggle_btn)
        
        self.timer_label = QLabel("⏱️ Czas nagrywania: 00:00")
        self.timer_label.setStyleSheet("""
        QLabel {
            color: #2c3e50;
            font-size: 16px;
            font-weight: bold;
            font-family: 'Courier New', monospace;
            padding: 10px;
            background-color: #ecf0f1;
            border: 2px solid #bdc3c7;
            border-radius: 8px;
            margin: 5px;
        }
        """)
        self.timer_label.setAlignment(Qt.AlignCenter)
        button_layout.addWidget(self.timer_label)
        
        buttons_row = QHBoxLayout()
        self.close_btn = QPushButton("Zamknij")
        self.close_btn.clicked.connect(self.close_dialog)
        self.close_btn.setStyleSheet("""
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
        
        buttons_row.addWidget(self.close_btn)
        button_layout.addLayout(buttons_row)
        
        layout.addLayout(button_layout)
    
    def get_spinbox_style(self):
        return """
        QDoubleSpinBox, QSpinBox {
            border: 2px solid #bdc3c7;
            border-radius: 5px;
            padding: 8px;
            font-size: 13px;
            background-color: white;
            color: #2c3e50;
            min-width: 120px;
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
    
    def log_message(self, message):
        self.log_signal.emit(message)
    
    def _log_message_safe(self, message):
        current_text = self.logs_text.toPlainText()
        self.logs_text.setPlainText(current_text + message + "\n")
        scrollbar = self.logs_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def toggle_biast(self, state):
        if state == Qt.CheckState.Checked.value:
            self.log_message("🔧 Uruchamiam: rtl_biast -b 1")
            try:
                result = subprocess.run(['rtl_biast', '-b', '1'], 
                                      capture_output=True, 
                                      text=True,
                                      timeout=5)
                if result.returncode == 0:
                    self.log_message("BiasT włączony")
                    if result.stdout.strip():
                        for line in result.stdout.strip().split('\n'):
                            self.log_message(f"📄 {line}")
                else:
                    self.log_message(f"BŁĄD: Nie udało się włączyć BiasT (kod: {result.returncode})")
                    if result.stderr.strip():
                        self.log_message(f"📄 {result.stderr.strip()}")
                    self.biast_checkbox.setChecked(False) 
            except FileNotFoundError:
                self.log_message("BŁĄD: Nie znaleziono komendy rtl_biast")
                self.log_message("Zainstaluj: sudo apt install rtl-sdr")
                self.biast_checkbox.setChecked(False)
            except subprocess.TimeoutExpired:
                self.log_message("BŁĄD: Timeout podczas włączania BiasT")
                self.biast_checkbox.setChecked(False)
            except Exception as e:
                self.log_message(f"BŁĄD: {str(e)}")
                self.biast_checkbox.setChecked(False)
        else:
            self.log_message("Uruchamiam: rtl_biast -b 0")
            try:
                result = subprocess.run(['rtl_biast', '-b', '0'], 
                                      capture_output=True, 
                                      text=True,
                                      timeout=5)
                if result.returncode == 0:
                    self.log_message("BiasT wyłączony")
                    if result.stdout.strip():
                        for line in result.stdout.strip().split('\n'):
                            self.log_message(f"📄 {line}")
                else:
                    self.log_message(f"BŁĄD: Nie udało się wyłączyć BiasT (kod: {result.returncode})")
                    if result.stderr.strip():
                        self.log_message(f"📄 {result.stderr.strip()}")
            except FileNotFoundError:
                self.log_message("BŁĄD: Nie znaleziono komendy rtl_biast")
                self.log_message("Zainstaluj: sudo apt install rtl-sdr")
            except subprocess.TimeoutExpired:
                self.log_message("BŁĄD: Timeout podczas wyłączania BiasT")
            except Exception as e:
                self.log_message(f"BŁĄD: {str(e)}")
    
    def warmup_receiver(self):
        self.warmup_btn.setEnabled(False)
        self.record_toggle_btn.setEnabled(False)
        self.frequency_spin.setEnabled(False)
        self.sample_rate_spin.setEnabled(False)
        self.num_sdrs_spin.setEnabled(False)
        self.filename_edit.setEnabled(False)
        
        self.log_message("🔥 Rozpoczynam nagrzewanie odbiornika...")
        self.log_message("Uruchamiam: rtl_test -p")
        
        def warmup_thread():
            device_error = {'found': False}
            
            try:
                process = subprocess.Popen(['rtl_test', '-p'], 
                                         stdout=subprocess.PIPE, 
                                         stderr=subprocess.STDOUT,
                                         text=True,
                                         bufsize=1, 
                                         universal_newlines=True)
                self.log_signal.emit("Proces rtl_test uruchomiony")
                
                def read_output():
                    try:
                        for line in process.stdout:
                            line = line.strip()
                            if line:
                                self.log_signal.emit(f"📄 {line}")
                                if "No supported devices found" in line:
                                    device_error['found'] = True
                                    self.log_signal.emit("BŁĄD: Nie znaleziono urządzenia RTL-SDR!")
                                    self.log_signal.emit("Upewnij się, że urządzenie jest podłączone")
                    except:
                        pass
                
                reader_thread = threading.Thread(target=read_output)
                reader_thread.daemon = True
                reader_thread.start()
                for i in range(60, 0, -1):
                    if device_error['found']:
                        self.log_signal.emit("⚠️  Przerwano nagrzewanie z powodu błędu")
                        break
                    if i % 10 == 0:
                        self.log_signal.emit(f"⏱️  Pozostało {i} sekund...")
                    time.sleep(1)
                
                self.log_signal.emit(" Zatrzymuję rtl_test...")
                process.terminate()
                
                try:
                    process.wait(timeout=3)
                    self.log_signal.emit("Proces rtl_test zakończony")
                except subprocess.TimeoutExpired:
                    self.log_signal.emit("Wymuszam zakończenie rtl_test...")
                    process.kill()
                    process.wait()
                
                self.log_signal.emit("✅ Nagrzewanie zakończone!")
                
            except FileNotFoundError:
                self.log_signal.emit("BŁĄD: Nie znaleziono komendy rtl_test")
                self.log_signal.emit("Zainstaluj rtl-sdr: sudo apt install rtl-sdr")
            except Exception as e:
                self.log_signal.emit(f"❌ BŁĄD podczas nagrzewania: {str(e)}")
            
            self.warmup_complete.emit()
        
        thread = threading.Thread(target=warmup_thread)
        thread.daemon = True
        thread.start()
    
    def _warmup_finished(self):
        self.warmup_btn.setEnabled(True)
        self.record_toggle_btn.setEnabled(True)
        self.frequency_spin.setEnabled(True)
        self.sample_rate_spin.setEnabled(True)
        self.num_sdrs_spin.setEnabled(True)
        self.filename_edit.setEnabled(True)
    
    def toggle_recording(self):
        if not self.is_recording:
            self.start_recording()
        else:
            self.stop_recording()
    
    def _update_timer_display(self, elapsed_seconds):
        minutes = elapsed_seconds // 60
        seconds = elapsed_seconds % 60
        self.timer_label.setText(f"⏱️ Czas nagrywania: {minutes:02d}:{seconds:02d}")
    
    def start_recording(self):
        frequency_hz = int(self.frequency_spin.value() * 1000000)
        sample_rate_hz = int(self.sample_rate_spin.value() * 1000000)
        num_sdrs = self.num_sdrs_spin.value()
        filename = self.filename_edit.text()
        
        self.log_message(f"Rozpoczynam nagrywanie...")
        self.log_message(f"Częstotliwość: {frequency_hz} Hz")
        self.log_message(f"Częstotliwość próbkowania: {sample_rate_hz} Hz")
        self.log_message(f"Liczba SDRów: {num_sdrs}")
        self.log_message(f"Nazwa pliku: {filename}")
        
        self.frequency_spin.setEnabled(False)
        self.sample_rate_spin.setEnabled(False)
        self.num_sdrs_spin.setEnabled(False)
        self.filename_edit.setEnabled(False)
        self.biast_checkbox.setEnabled(False)
        self.warmup_btn.setEnabled(False)
        
        self.record_toggle_btn.setText("⏹️ Wyłącz nagrywanie")
        self.record_toggle_btn.setStyleSheet("""
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
        
        self.is_recording = True
        self.recording_start_time = time.time()
        self.recording_processes = []
        
        for i in range(num_sdrs):
            base_name = filename.rsplit('.', 1)[0] if '.' in filename else filename
            output_file = f"{i}_{base_name}.bin"
            
            cmd = ['rtl_sdr', '-f', str(frequency_hz), '-s', str(sample_rate_hz), 
                   '-g', 'list', '-d', str(i), output_file]
            self.log_message(f"SDR {i+1}: {' '.join(cmd)}")
            
            try:
                process = subprocess.Popen(cmd, 
                                         stdout=subprocess.PIPE, 
                                         stderr=subprocess.STDOUT,
                                         text=True,
                                         bufsize=1,
                                         universal_newlines=True)
                self.recording_processes.append(process)
                self.log_message(f"✅ SDR {i+1} uruchomiony (PID: {process.pid})")
                
                def read_sdr_output(proc, sdr_num):
                    try:
                        for line in proc.stdout:
                            line = line.strip()
                            if line:
                                self.log_signal.emit(f"SDR {sdr_num}: {line}")
                    except:
                        pass
                
                reader_thread = threading.Thread(target=read_sdr_output, args=(process, i+1))
                reader_thread.daemon = True
                reader_thread.start()
                
            except FileNotFoundError:
                self.log_message(f"❌ BŁĄD: Nie znaleziono komendy rtl_sdr")
                self.log_message("💡 Zainstaluj: sudo apt install rtl-sdr")
                self.stop_recording()
                return
            except Exception as e:
                self.log_message(f"❌ BŁĄD podczas uruchamiania SDR {i+1}: {str(e)}")

        def timer_thread():
            while self.is_recording:
                elapsed = int(time.time() - self.recording_start_time)
                self.update_timer.emit(elapsed)
                time.sleep(1)
        
        timer_t = threading.Thread(target=timer_thread)
        timer_t.daemon = True
        timer_t.start()
        
        self.log_message("✅ Nagrywanie aktywne!")
    
    def stop_recording(self):
        self.log_message("⏹️  Zatrzymuję nagrywanie...")
        
        self.is_recording = False
        
        for i, process in enumerate(self.recording_processes):
            try:
                self.log_message(f"⏹️  Zatrzymuję SDR {i+1}...")
                process.terminate()
                
                try:
                    process.wait(timeout=3)
                    self.log_message(f"✅ SDR {i+1} zakończony")
                except subprocess.TimeoutExpired:
                    self.log_message(f"⚠️  Wymuszam zakończenie SDR {i+1}...")
                    process.kill()
                    process.wait()
            except Exception as e:
                self.log_message(f"❌ Błąd podczas zatrzymywania SDR {i+1}: {str(e)}")
        
        self.recording_processes = []
        self.frequency_spin.setEnabled(True)
        self.sample_rate_spin.setEnabled(True)
        self.num_sdrs_spin.setEnabled(True)
        self.filename_edit.setEnabled(True)
        self.biast_checkbox.setEnabled(True)
        self.warmup_btn.setEnabled(True)

        self.record_toggle_btn.setText("▶️ Włącz nagrywanie")
        self.record_toggle_btn.setStyleSheet("""
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
        self.timer_label.setText("⏱️ Czas nagrywania: 00:00")
        
        self.log_message("✅ Nagrywanie zatrzymane!")
    
    def close_dialog(self):
        if self.is_recording:
            self.stop_recording()
        self.accept()
