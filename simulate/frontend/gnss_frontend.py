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
            "Nazwa pliku (.bin):",                 # 0
            "Czas próbki (s):",                    # 1
            "Długość geograficzna:",               # 2
            "Szerokość geograficzna:",             # 3
            "Wysokość (m n.p.m.):",                # 4
            "Długość geograficzna (końcowa):",     # 5
            "Szerokość geograficzna (końcowa):",   # 6
            "Wysokość (m n.p.m.) – końcowa:",      # 7
        ]

        self.entries = []
        self.row_widgets = []  # (label_widget, entry_widget)
        self.v_lat_key = (self.register(self._validate_lat_key), "%P")
        self.v_lon_key = (self.register(self._validate_lon_key), "%P")
        self.v_sec_key = (self.register(self._validate_seconds_key), "%P")
        self.v_file_focusout = (self.register(self._validate_filename_focusout), "%P")
        self.v_alt_key = (self.register(self._validate_alt_key), "%P")
        self.v_range_key = (self.register(self._validate_range_key), "%P")

        for r, name in enumerate(self.label_names):
            lbl = tk.Label(self.form, text=name, width=28, anchor="e")

            if r == 0: # Nazwa pliku
                ent = tk.Entry(self.form, width=40, validate="focusout", validatecommand=self.v_file_focusout)
            elif r == 1:  # Czas próbki (s)
                ent = tk.Entry(self.form, width=40, validate="key", validatecommand=self.v_sec_key)
            elif r in (3, 6):  # LAT (szerokość geograficzna)
                ent = tk.Entry(self.form, width=40, validate="key", validatecommand=self.v_lat_key)
            elif r in (2, 5):  # LON (długość geograficzna)
                ent = tk.Entry(self.form, width=40, validate="key", validatecommand=self.v_lon_key)
            elif r in (4, 7):  # ALT
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

        # ===== SEKCJA JAMMERA =====
        self.jammer_frame = tk.Frame(self.root_frame)
        self.jammer_frame.grid(row=4, column=0, pady=(16,8), sticky="w")
        self.jammer_frame.columnconfigure(0, weight=0)
        self.jammer_frame.columnconfigure(1, weight=1)

        # Pola jammera
        self.jammer_labels = [
            "Długość geograficzna jammera:",
            "Szerokość geograficzna jammera:",
            "Zasięg jammera (m):"
        ]
        
        self.jammer_entries = []
        self.jammer_widgets = []

        for r, name in enumerate(self.jammer_labels):
            lbl = tk.Label(self.jammer_frame, text=name, width=28, anchor="e")
            
            if r == 0:  # LON jammera
                ent = tk.Entry(self.jammer_frame, width=40, validate="key", validatecommand=self.v_lon_key)
            elif r == 1:  # LAT jammera
                ent = tk.Entry(self.jammer_frame, width=40, validate="key", validatecommand=self.v_lat_key)
            elif r == 2:  # Zasięg jammera
                ent = tk.Entry(self.jammer_frame, width=40, validate="key", validatecommand=self.v_range_key)
            
            lbl.grid(row=r, column=0, padx=(0,10), pady=5, sticky="e")
            ent.grid(row=r, column=1, pady=5, sticky="we")
            self.jammer_entries.append(ent)
            self.jammer_widgets.append((lbl, ent))

        # Początkowo ukrywamy sekcję jammera
        self.jammer_frame.grid_remove()

        tk.Button(self.root_frame, text="START", bg="#4CAF50", fg="white",
                  font=("Arial", 11, "bold"), width=15,
                  command=self.on_start).grid(row=5, column=0, pady=24, sticky="w")

        # ---- KONFIG: zakresy 
        self.ALT_MIN = -500.0
        self.ALT_MAX = 20000.0
        
        # ---- KONFIG: ścieżki
        base_dir = os.path.dirname(os.path.abspath(__file__))          # → simulate/frontend
        root_dir = os.path.abspath(os.path.join(base_dir, os.pardir))  # → simulate
        gps_dir  = os.path.join(root_dir, "gps-sdr-sim")               # → simulate/gps-sdr-sim
        self.GPS_SDR_SIM_PATH  = os.path.join(gps_dir, "gps-sdr-sim")   # plik binarny
        self.EPHERIS_FILE_PATH = os.path.join(gps_dir, "brdc2830.25n")  # plik efemeryd
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

        if self.mode_var.get() == "B":  # Jammer
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
            "test.bin",     # Nazwa pliku (.bin)
            "120",          # Czas próbki (s)
            "50.0263760",   # Długość geograficzna (start)
            "19.944750",    # Szerokość geograficzna (start)
            "350.0",        # Wysokość (start)
            "50.0863760",   # Długość geograficzna (koniec) - używane gdy "Ruchomy"
            "19.444750",    # Szerokość geograficzna (koniec)
            "420.0",       # Wysokość (koniec)
        ]
        for i, val in enumerate(defaults):
            # wstaw tylko do istniejących, widoczność nie ma znaczenia
            if i < len(self.entries):
                self.entries[i].delete(0, tk.END)
                self.entries[i].insert(0, val)

        # domyślne dla jammera (jeśli tryb B)
        jammer_defaults = [
            "50.0263760",  # Długość geograficzna jammera
            "19.644750",   # Szerokość geograficzna jammera
            "10"           # Zasięg jammera [m]
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
        # ---- USTAWIENIA EDYTOWALNE (1 miejsce do zmiany) ----
        EPHEMERIS_FILE = self.EPHERIS_FILE_PATH         # -e
        T_STATIONARY   = "2025/10/10,00:00:00"          # -T dla nieruchomego
        T_MOBILE       = "2025/10/10,00:00:00"          # -T dla ruchomego
        BITS           = "8"                            # -b
        SAMPLERATE     = "2048000"                      # -s
        TRAJ_FILE      = "traj.csv"                     # nazwa tworzonej trajektorii przy ruchomym
        # -----------------------------------------------------

        # --- Walidacje jak u Ciebie (skrócone tylko do potrzeb tego scenariusza) ---
        base_count = 8 if self.is_ruchomy.get() else 5
        values = [self.entries[i].get().strip() for i in range(base_count)]
        mode = self.mode_var.get()

        idx_filename   = 0
        idx_seconds    = 1
        idx_lon_start  = 2
        idx_lat_start  = 3
        idx_alt_start  = 4
        idx_lon_end    = 5
        idx_lat_end    = 6
        idx_alt_end    = 7

        # podstawowe sprawdzenia
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

        # tylko tryb A uruchamia gps-sdr-sim
        if mode != "A":
            messagebox.showwarning("Uwaga", "gps-sdr-sim uruchamiany jest tylko w trybie 'Bez zakłóceń'.")
            return

        # prosta walidacja -T (YYYY/MM/DD,hh:mm:ss)
        TIMEREG = re.compile(r"^\d{4}/\d{2}/\d{2},\d{2}:\d{2}:\d{2}$")
        t_stationary = T_STATIONARY if TIMEREG.match(T_STATIONARY) else "2025/10/10,00:00:00"
        t_mobile     = T_MOBILE     if TIMEREG.match(T_MOBILE)     else "2025/10/10,00:00:00"

        # budujemy komendę zależnie od ruchomy/nie
        if not self.is_ruchomy.get():
            # NIERUCHOMY → -l lat,lon,alt
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
            return
        else:
            # RUCHOMY → wygeneruj traj.csv, następnie -u traj.csv
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
                return  # błąd pokazany w run_generate_trajectory

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
            return


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
        """Zasięg jammera: musi byc 0-100m"""
        try:
            if text.strip() == "":
                return False
            val = float(text)
            return 0.0 < val <= 100.0
        except ValueError:
            return False

    def run_mode_script(self,mode, args):
        # odpala skrypty na podstawie wybranego trybu
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

        cmd = [sys.executable, script_path] + args
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Błąd", f"Błąd podczas uruchamiania skryptu: {e}")

    def run_generate_trajectory(self, start_lat, start_lon, start_alt,
                                end_lat, end_lon, end_alt,
                                duration_s, step_s=1, out_file="traj.csv"):
        """
        Odpala generate_trajectory.py z parametrami z GUI.
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
            messagebox.showinfo("Trajektoria OK", f"Wygenerowano {out_file}")
            return out_file
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Błąd trajektorii", f"generate_trajectory.py zwrócił błąd:\n{e.stderr}")
            return None


if __name__ == "__main__":
    app = App()
    app.mainloop()
