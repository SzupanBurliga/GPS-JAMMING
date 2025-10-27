import tkinter as tk
from tkinter import messagebox
import re
import subprocess
import sys
import os
import time
import threading

class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Generowanie próbek GNSS")
        self.update_idletasks()
        self.resizable(True, True)
        self.minsize(600, 400)
        self.maxsize(1920, 1080)

        self.root_frame = tk.Frame(self, padx=20, pady=20)
        self.root_frame.pack(fill="both", expand=True, anchor="nw")

        self.is_ruchomy = tk.BooleanVar(value=False)
        top_frame = tk.Frame(self.root_frame)
        top_frame.grid(row=0, column=0, sticky="w")
        tk.Label(top_frame, text="Ruchomy:", font=("Arial", 10, "bold")).grid(row=0, column=0, padx=(0,8))
        self.ruchomy_button = tk.Button(
            top_frame, text="Nie", width=8, bg="#f44336", fg="white",
            command=self.toggle_ruchomy
        )
        self.ruchomy_button.grid(row=0, column=1)

        self.form = tk.Frame(self.root_frame)
        self.form.grid(row=1, column=0, pady=(16,8), sticky="w")
        self.form.columnconfigure(0, weight=0)
        self.form.columnconfigure(1, weight=1)

        self.label_names = [
            "Nazwa pliku (.bin):",
            "Czas próbki (s):",
            "Szerokość geograficzna:",
            "Długość geograficzna:",
            "Wysokość (m n.p.m.):",
            "Szerokość geograficzna (końcowa):",
            "Długość geograficzna (końcowa):",
            "Wysokość (m n.p.m.) – końcowa:",
        ]

        self.entries = []
        self.row_widgets = []
        self.v_lat_key = (self.register(self._validate_lat_key), "%P")
        self.v_lon_key = (self.register(self._validate_lon_key), "%P")
        self.v_sec_key = (self.register(self._validate_seconds_key), "%P")
        self.v_file_focusout = (self.register(self._validate_filename_focusout), "%P")
        self.v_alt_key = (self.register(self._validate_alt_key), "%P")
        self.v_range_key = (self.register(self._validate_range_key), "%P")

        for r, name in enumerate(self.label_names):
            lbl = tk.Label(self.form, text=name, width=28, anchor="e")

            if r == 0: 
                ent = tk.Entry(self.form, width=40, validate="focusout", validatecommand=self.v_file_focusout)
            elif r == 1:
                ent = tk.Entry(self.form, width=40, validate="key", validatecommand=self.v_sec_key)
            elif r in (2, 5): 
                ent = tk.Entry(self.form, width=40, validate="key", validatecommand=self.v_lat_key)
            elif r in (3, 6): 
                ent = tk.Entry(self.form, width=40, validate="key", validatecommand=self.v_lon_key)
            elif r in (4, 7): 
                ent = tk.Entry(self.form, width=40, validate="key", validatecommand=self.v_alt_key)
            else:
                ent = tk.Entry(self.form, width=40)

            lbl.grid(row=r, column=0, padx=(0,10), pady=5, sticky="e")
            ent.grid(row=r, column=1, pady=5, sticky="we")
            self.entries.append(ent)
            self.row_widgets.append((lbl, ent))

        self.update_input_visibility(5)

        tk.Label(self.root_frame, text="Wybierz tryb:", font=("Arial", 10, "bold"))\
            .grid(row=2, column=0, pady=(12,4), sticky="w")

        self.mode_var = tk.StringVar(value="")
        self.mode_var.trace_add("write", self.on_mode_change)
        modes = [("Bez zakłóceń", "A"), ("Jammer", "B"), ("Spoofer", "C")]
        radios = tk.Frame(self.root_frame)
        radios.grid(row=3, column=0, sticky="w")
        for i, (text, value) in enumerate(modes):
            tk.Radiobutton(radios, text=text, variable=self.mode_var, value=value)\
                .grid(row=0, column=i, padx=(0 if i == 0 else 16, 0), sticky="w")

        # panel jammera
        self.jammer_frame = tk.Frame(self.root_frame)
        self.jammer_frame.grid(row=4, column=0, pady=(16,8), sticky="w")
        self.jammer_frame.columnconfigure(0, weight=0)
        self.jammer_frame.columnconfigure(1, weight=1)

        # Pola jammera (tak jak były)
        self.jammer_labels = [           
            "Szerokość geograficzna jammera:",
            "Długość geograficzna jammera:",
            "Zasięg jammera (m):"
        ]
        
        self.jammer_entries = []
        self.jammer_widgets = []

        for r, name in enumerate(self.jammer_labels):
            lbl = tk.Label(self.jammer_frame, text=name, width=28, anchor="e")
            
            if r == 0:
                ent = tk.Entry(self.jammer_frame, width=40, validate="key", validatecommand=self.v_lat_key)
            elif r == 1:
                ent = tk.Entry(self.jammer_frame, width=40, validate="key", validatecommand=self.v_lon_key)
            elif r == 2:
                ent = tk.Entry(self.jammer_frame, width=40, validate="key", validatecommand=self.v_range_key)
            
            lbl.grid(row=r, column=0, padx=(0,10), pady=5, sticky="e")
            ent.grid(row=r, column=1, pady=5, sticky="we")
            self.jammer_entries.append(ent)
            self.jammer_widgets.append((lbl, ent))

        self.jammer_type_var = tk.StringVar(value="BB") 

        jammer_types = [
            ("Szum szerokopasmowy (Broadband Noise)", "BB"),
            ("Sygnał o stałej fali (Continuous Wave - CW)", "CW"),
            ("Jammer przemiatany (Swept / Chirp Jammer)", "SWEEP"),
            ("Jammer impulsowy (Pulsed Jammer)", "PULSED")
        ]

        jammer_radios_frame = tk.Frame(self.jammer_frame)
        jammer_radios_frame.grid(row=3, column=0, columnspan=2, pady=(10,0), sticky="w")

        tk.Label(jammer_radios_frame, text="Typ jammera:", font=("Arial", 10, "bold"))\
            .grid(row=0, column=0, sticky="w", pady=(0, 5))

        for i, (text, value) in enumerate(jammer_types):
            tk.Radiobutton(
                jammer_radios_frame,
                text=text,
                variable=self.jammer_type_var,
                value=value
            ).grid(row=i + 1, column=0, sticky="w", padx=(10, 0))

        self.jammer_frame.grid_remove()
        tk.Button(self.root_frame, text="START", bg="#4CAF50", fg="white",
                  font=("Arial", 11, "bold"), width=15,
                  command=self.on_start).grid(row=5, column=0, pady=24, sticky="w")

        # konfig 
        self.ALT_MIN = -500.0
        self.ALT_MAX = 20000.0
        base_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.abspath(os.path.join(base_dir, os.pardir))
        gps_dir  = os.path.join(root_dir, "gps-sdr-sim")
        self.GPS_SDR_SIM_PATH  = os.path.join(gps_dir, "gps-sdr-sim")
        self.EPHERIS_FILE_PATH = os.path.join(gps_dir, "brdc2830.25n")
        self.set_basic_defaults()

    def _validate_lat_key(self, P: str) -> bool:
        """LAT: dopuszcza -?, do 2 cyfr + opcjonalna . i do 7 miejsc po kropce (format); zakres sprawdzimy później."""
        if P == "":
            return True
        return re.fullmatch(r"^-?\d{0,2}(\.\d{0,7})?$", P) is not None

    def _validate_lon_key(self, P: str) -> bool:
        """LON: dopuszcza -?, do 3 cyfr + opcjonalna . i do 7 miejsc po kropce (format); zakres sprawdzimy później."""
        if P == "":
            return True
        return re.fullmatch(r"^-?\d{0,3}(\.\d{0,7})?$", P) is not None

    def _validate_alt_key(self, P: str) -> bool:
        """ALT: liczba zmiennoprzecinkowa z opcjonalnym minusem; do 3 miejsc po kropce (format)."""
        if P == "":
            return True
        return re.fullmatch(r"^-?\d{0,6}(\.\d{0,3})?$", P) is not None

    def _validate_seconds_key(self, P: str) -> bool:
        return P.isdigit() or P == ""

    def _validate_range_key(self, P: str) -> bool:
        """Zasięg jammera: liczba dodatnia, do 2 miejsc po kropce."""
        if P == "":
            return True
        return re.fullmatch(r"^\d{0,6}(\.\d{0,2})?$", P) is not None

    def _validate_filename_focusout(self, P: str) -> bool:
        if P.strip() == "":
            return True
        return P.lower().endswith(".bin")

    def toggle_ruchomy(self):
        self.is_ruchomy.set(not self.is_ruchomy.get())
        if self.is_ruchomy.get():
            self.ruchomy_button.config(text="Tak", bg="#4CAF50")
        else:
            self.ruchomy_button.config(text="Nie", bg="#f44336")
        self.update_fields_visibility()

    def on_mode_change(self, *args):
        """Wywołuje się gdy zmieni się tryb (A/B/C)"""
        self.update_fields_visibility()

    def update_fields_visibility(self):
        """Aktualizuje widoczność pól w zależności od trybu i stanu ruchomy"""
        base_count = 5  
        
        if self.is_ruchomy.get():
            base_count = 8 

        self.update_input_visibility(base_count)

        if self.mode_var.get() == "B":
            self.jammer_frame.grid()
        else:
            self.jammer_frame.grid_remove()

    def update_input_visibility(self, count):
        for r, (lbl, ent) in enumerate(self.row_widgets):
            if r < count:
                lbl.grid()
                ent.grid()
            else:
                lbl.grid_remove()
                ent.grid_remove()

    def set_basic_defaults(self):
        """Ustawia domyślne wartości w polach formularza"""
        defaults = [
            "test.bin",
            "120",
            "50.0000000",
            "19.9000000",
            "350.0",
            "50.0000000",
            "19.9080000",
            "350.0",
        ]
        for i, val in enumerate(defaults):
            if i < len(self.entries):
                self.entries[i].delete(0, tk.END)
                self.entries[i].insert(0, val)

        jammer_defaults = [
            "50.0263760",
            "19.644750",
            "10"
        ]
        for i, val in enumerate(jammer_defaults):
            if i < len(self.jammer_entries):
                self.jammer_entries[i].delete(0, tk.END)
                self.jammer_entries[i].insert(0, val)

    def start_btn_state(self, enabled: bool):
        for child in self.root_frame.grid_slaves(row=5, column=0):
            if isinstance(child, tk.Button) and child.cget("text") == "START":
                child.config(state=("normal" if enabled else "disabled"))

    def _run_cmd_thread(self, cmd: list[str], output_filename: str = ""):
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            out = []
            for line in iter(proc.stdout.readline, ""):
                if not line and proc.poll() is not None:
                    break
                if line:
                    out.append(line)
                    print(line.rstrip())
            rc = proc.wait()
            if rc == 0:
                msg = f"Plik został wygenerowany pomyślnie!\n\nNazwa pliku: {output_filename}\nLokalizacja: /frontend/"
            else:
                msg = f"Błąd podczas generowania (kod {rc})"
            
            self.after(0, lambda: messagebox.showinfo("gps-sdr-sim", f"{msg}\n\n" ))
        except FileNotFoundError:
            self.after(0, lambda: messagebox.showerror("Error", f"Nie znaleziono gps-sdr-sim w: {self.GPS_SDR_SIM_PATH}"))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Error", f"Wystąpił wyjątek: {e}"))
        finally:
            self.after(0, lambda: self.start_btn_state(True))


    def on_start(self):
        # ustawienia na twardo wpisywane
        EPHEMERIS_FILE = self.EPHERIS_FILE_PATH
        T_STATIONARY   = "2025/10/10,00:00:00"
        T_MOBILE       = "2025/10/10,00:00:00"
        BITS           = "8"
        SAMPLERATE     = "2048000"
        TRAJ_FILE      = "traj.csv"

        base_count = 8 if self.is_ruchomy.get() else 5
        values = [self.entries[i].get().strip() for i in range(base_count)]
        mode = self.mode_var.get()

        if mode == "":
            messagebox.showerror("Błąd", "Wybierz tryb (Bez zakłóceń, Jammer lub Spoofer).")
            return

        idx_filename   = 0
        idx_seconds    = 1
        idx_lat_start  = 2
        idx_lon_start  = 3
        idx_alt_start  = 4
        idx_lat_end    = 5
        idx_lon_end    = 6
        idx_alt_end    = 7

        # Walidacja podstawowych pól (wspólna dla wszystkich trybów)
        filename = values[idx_filename]
        if not filename.lower().endswith(".bin"):
            messagebox.showerror("Błąd", "Nazwa pliku musi kończyć się na .bin")
            self.entries[idx_filename].focus_set(); return

        sec_txt = values[idx_seconds]
        if not sec_txt.isdigit():
            messagebox.showerror("Błąd", "Czas próbki (s) musi być liczbą całkowitą.")
            self.entries[idx_seconds].focus_set(); return
        seconds = int(sec_txt)
        if not (1 <= seconds <= 86400):
            messagebox.showerror("Błąd", "Czas próbki (s) musi być w zakresie 1..86400.")
            self.entries[idx_seconds].focus_set(); return

        if not self._lon_in_range(values[idx_lon_start]):
            messagebox.showerror("Błąd", "Długość geograficzna (start) musi być w zakresie −180..180.")
            self.entries[idx_lon_start].focus_set(); return
        if not self._lat_in_range(values[idx_lat_start]):
            messagebox.showerror("Błąd", "Szerokość geograficzna (start) musi być w zakresie −90..90.")
            self.entries[idx_lat_start].focus_set(); return
        if not self._alt_in_range(values[idx_alt_start]):
            messagebox.showerror("Błąd", f"Wysokość (start) musi być w zakresie {self.ALT_MIN}..{self.ALT_MAX} m.")
            self.entries[idx_alt_start].focus_set(); return
        
        if self.is_ruchomy.get():
            if not self._lon_in_range(values[idx_lon_end]):
                messagebox.showerror("Błąd", "Długość geograficzna (końcowa) musi być w zakresie −180..180.")
                self.entries[idx_lon_end].focus_set(); return
            if not self._lat_in_range(values[idx_lat_end]):
                messagebox.showerror("Błąd", "Szerokość geograficzna (końcowa) musi być w zakresie −90..90.")
                self.entries[idx_lat_end].focus_set(); return
            if not self._alt_in_range(values[idx_alt_end]):
                messagebox.showerror("Błąd", f"Wysokość (końcowa) musi być w zakresie {self.ALT_MIN}..{self.ALT_MAX} m.")
                self.entries[idx_alt_end].focus_set(); return

        TIMEREG = re.compile(r"^\d{4}/\d{2}/\d{2},\d{2}:\d{2}:\d{2}$")
        t_stationary = T_STATIONARY if TIMEREG.match(T_STATIONARY) else "2025/10/10,00:00:00"
        t_mobile     = T_MOBILE     if TIMEREG.match(T_MOBILE)     else "2025/10/10,00:00:00"

        if mode == "A":
            if not self.is_ruchomy.get():
                lat = values[idx_lat_start]
                lon = values[idx_lon_start]
                alt = values[idx_alt_start]
                cmd = [
                    self.GPS_SDR_SIM_PATH,
                    "-e", self.EPHERIS_FILE_PATH,
                    "-l", f"{lat},{lon},{alt}",
                    "-b", BITS,
                    "-d", str(seconds),
                    "-T", t_stationary,
                    "-o", filename,
                    "-s", SAMPLERATE,
                    "-v"
                ]
                self.start_btn_state(False)
                threading.Thread(target=self._run_cmd_thread, args=(cmd, filename), daemon=True).start()
            else:
                traj_path = self.run_generate_trajectory(
                    start_lat=values[idx_lat_start],
                    start_lon=values[idx_lon_start],
                    start_alt=values[idx_alt_start],
                    end_lat=values[idx_lat_end],
                    end_lon=values[idx_lon_end],
                    end_alt=values[idx_alt_end],
                    duration_s=seconds,
                    step_s=0.1,
                    out_file=TRAJ_FILE
                )
                if traj_path is None:
                    return 

                cmd = [
                    self.GPS_SDR_SIM_PATH,
                    "-e", self.EPHERIS_FILE_PATH,
                    "-u", traj_path,
                    "-b", BITS,
                    "-d", str(seconds),
                    "-T", t_mobile,
                    "-o", filename,
                    "-s", SAMPLERATE,
                    "-v"
                ]
                self.start_btn_state(False)
                threading.Thread(target=self._run_cmd_thread, args=(cmd, filename), daemon=True).start()
        
        elif mode == "B":
            # walidacja pól jammera
            try:
                jammer_lat = self.jammer_entries[0].get().strip()
                jammer_lon = self.jammer_entries[1].get().strip()
                jammer_range = self.jammer_entries[2].get().strip()
            except IndexError:
                messagebox.showerror("Błąd", "Nie można odnaleźć pól jammera.")
                return

            if not self._lon_in_range(jammer_lon):
                messagebox.showerror("Błąd", "Długość geograficzna jammera jest nieprawidłowa.")
                self.jammer_entries[0].focus_set(); return
            if not self._lat_in_range(jammer_lat):
                messagebox.showerror("Błąd", "Szerokość geograficzna jammera jest nieprawidłowa.")
                self.jammer_entries[1].focus_set(); return
            if not self._range_in_range(jammer_range): 
                messagebox.showerror("Błąd", "Zasięg jammera jest nieprawidłowy (musi być > 0).")
                self.jammer_entries[2].focus_set(); return
            jammer_type = self.jammer_type_var.get()

            messagebox.showinfo("Start - Tryb Jammer", 
                                f"Plik: {filename}\n"
                                f"Czas: {seconds}s\n"
                                f"Tryb: Jammer\n"
                                f"Typ: {jammer_type}\n"
                                f"Lokalizacja jammera: {jammer_lat}, {jammer_lon}\n"
                                f"Zasięg: {jammer_range}m")
            
            script_map = {
                "Chirp Jammer": "chirp_jammer.py",
                "Pulsed Jammer": "pulsed_jammer.py",
                "Continuous Wave - CW": "cw_jammer.py",
                "Broadband Noise": "broadband_jammer.py"
            }
            
            print(f"Uruchamianie trybu B (Jammer) z typem: {jammer_type}")

        elif mode == "C":
            messagebox.showinfo("Start - Tryb Spoofer", 
                                "Tryb Spoofer nie jest jeszcze zaimplementowany.")

    # pomocnicze
    def _has_max_7_decimals(self, s: str) -> bool:
        if "." in s:
            frac = s.split(".", 1)[1]
            return len(frac) <= 7
        return True

    def _lat_in_range(self, text: str) -> bool:
        """LAT: −90..90 oraz maks. 7 miejsc po przecinku."""
        try:
            if text.strip() == "":
                return False
            if not self._has_max_7_decimals(text):
                return False
            val = float(text)
            return -90.0 <= val <= 90.0
        except ValueError:
            return False

    def _lon_in_range(self, text: str) -> bool:
        """LON: −180..180 oraz maks. 7 miejsc po przecinku."""
        try:
            if text.strip() == "":
                return False
            if not self._has_max_7_decimals(text):
                return False
            val = float(text)
            return -180.0 <= val <= 180.0
        except ValueError:
            return False

    def _alt_in_range(self, text: str) -> bool:
        try:
            if text.strip() == "":
                return False
            val = float(text)
            return self.ALT_MIN <= val <= self.ALT_MAX
        except ValueError:
            return False

    def _range_in_range(self, text: str) -> bool:
        """Zasięg jammera: musi być > 0"""
        try:
            if text.strip() == "":
                return False
            val = float(text)
            return val > 0.0
        except ValueError:
            return False

    def run_mode_script(self,mode, args):
        scripts = {
            "A": "mode_a.py",
            "B": "mode_b.py",
            "C": "mode_c.py"
        }

        script_name = scripts.get(mode)

        if not script_name:
            messagebox.showerror("Błąd", "Nieznany tryb!")
            return

        script_path = os.path.join(os.path.dirname(__file__), script_name)
        if not os.path.isfile(script_path):
            messagebox.showerror("Błąd", f"Nie znaleziono skryptu: {script_name}")
            return

        cmd = [sys. executable, script_path] + args
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Błąd", f"Błąd podczas uruchamiania skryptu: {e}")

    def run_generate_trajectory(self, start_lat, start_lon, start_alt,
                                end_lat, end_lon, end_alt,
                                duration_s, step_s=1, out_file="traj.csv"):
        """
        generate_trajectory.py przyjmuje argumenty:
        --start-lat --start-lon --start-alt --end-lat --end-lon --end-alt
        --duration --step --out
        """
        script_path = os.path.join(os.path.dirname(__file__), "generate_trajectory.py")
        if not os.path.isfile(script_path):
            messagebox.showerror("Błąd", "Nie znaleziono generate_trajectory.py")
            return None

        cmd = [
            sys.executable, script_path,
            "--start-lat", str(start_lat),
            "--start-lon", str(start_lon),
            "--start-alt", str(start_alt),
            "--end-lat",   str(end_lat),
            "--end-lon",   str(end_lon),
            "--end-alt",   str(end_alt),
            "--duration",  str(duration_s),
            "--step",      str(step_s),
            "--out",       out_file
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            print(f"generate_trajectory.py output:\n{res.stdout}")
            if res.stderr:
                print(f"generate_trajectory.py error output:\n{res.stderr}")
            messagebox.showinfo("Trajektoria OK", f"Wygenerowano {out_file}")
            return out_file
        except subprocess.CalledProcessError as e:
            err_msg = f"generate_trajectory.py zwrócił błąd:\n{e.stderr}"
            if e.stdout:
                err_msg += f"\nOutput (stdout):\n{e.stdout}"
            messagebox.showerror("Błąd trajektorii", err_msg)
            print(err_msg)
            return None


if __name__ == "__main__":
    app = App()
    app.mainloop()