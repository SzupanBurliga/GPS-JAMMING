import tkinter as tk
from tkinter import messagebox
import re
import subprocess
import sys
import os
import time
import threading
import shutil

class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Generowanie próbek GNSS")
        self.update_idletasks()
        self.resizable(True, True)
        self.minsize(600, 400)
        self.maxsize(1920, 1080)

        # Make the main area scrollable so START remains reachable on small/ fullscreen windows
        self._outer_container = tk.Frame(self)
        self._outer_container.pack(fill="both", expand=True)

        self._canvas = tk.Canvas(self._outer_container)
        self._vscroll = tk.Scrollbar(self._outer_container, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=self._vscroll.set)

        self._vscroll.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)

        # The actual root_frame holds the UI; it is placed inside the canvas so it can scroll.
        self.root_frame = tk.Frame(self._canvas, padx=20, pady=20)
        self._canvas_window = self._canvas.create_window((0, 0), window=self.root_frame, anchor="nw")

        # Keep canvas scrollregion synced to the inner frame size
        def _on_frame_config(event):
            self._canvas.configure(scrollregion=self._canvas.bbox("all"))
        self.root_frame.bind("<Configure>", _on_frame_config)

        # Ensure the inner window width follows the canvas width (so widgets wrap nicely)
        def _on_canvas_config(event):
            try:
                self._canvas.itemconfig(self._canvas_window, width=event.width)
            except Exception:
                pass
        self._canvas.bind('<Configure>', _on_canvas_config)

        # Mouse wheel support (Windows/Mac & Linux wheel/button events)
        def _on_mousewheel(event):
            # Delta normalization
            if event.num == 4:   # Linux scroll up
                delta = -1
            elif event.num == 5: # Linux scroll down
                delta = 1
            else:
                delta = -1 * int(event.delta / 120)
            self._canvas.yview_scroll(delta, "units")

        # Bind several common events for different platforms
        self._canvas.bind_all('<MouseWheel>', _on_mousewheel)
        self._canvas.bind_all('<Button-4>', _on_mousewheel)
        self._canvas.bind_all('<Button-5>', _on_mousewheel)

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
        self.form.columnconfigure(2, weight=0)
        self.form.columnconfigure(3, weight=1)

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
        self.v_float_key = (self.register(self._validate_float_key), "%P")

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
        self.arrange_receiver_rows()

        env_frame = tk.Frame(self.root_frame)
        env_frame.grid(row=2, column=0, pady=(8,4), sticky="w")
        tk.Label(env_frame, text="Parametry środowiskowe:", font=("Arial", 10, "bold"))\
            .grid(row=0, column=0, columnspan=2, sticky="w")
        env_labels = ["Temperature:", "Ciśnienie:", "Wilgotność:"]
        self.env_entries = []
        for idx, name in enumerate(env_labels, start=1):
            lbl = tk.Label(env_frame, text=name, width=28, anchor="e")
            ent = tk.Entry(env_frame, width=40, validate="key", validatecommand=self.v_float_key)
            lbl.grid(row=idx, column=0, padx=(0,10), pady=5, sticky="e")
            ent.grid(row=idx, column=1, pady=5, sticky="we")
            self.env_entries.append(ent)

        tk.Label(self.root_frame, text="Wybierz tryb:", font=("Arial", 10, "bold"))\
            .grid(row=3, column=0, pady=(12,4), sticky="w")

        self.mode_var = tk.StringVar(value="")
        self.mode_var.trace_add("write", self.on_mode_change)
        modes = [("Bez zakłóceń", "A"), ("Jammer", "B"), ("Spoofer", "C")]
        radios = tk.Frame(self.root_frame)
        radios.grid(row=4, column=0, sticky="w")
        for i, (text, value) in enumerate(modes):
            tk.Radiobutton(radios, text=text, variable=self.mode_var, value=value)\
                .grid(row=0, column=i, padx=(0 if i == 0 else 16, 0), sticky="w")


        self.jammer_frame = tk.Frame(self.root_frame)
        self.jammer_frame.grid(row=5, column=0, pady=(16,8), sticky="w")
        self.jammer_frame.columnconfigure(0, weight=0)
        self.jammer_frame.columnconfigure(1, weight=1)

        self.jammer_labels = [           
            "Szerokość geograficzna jammera:",
            "Długość geograficzna jammera:",
            "Wysokość (m n.p.m.) jammera:",
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
                ent = tk.Entry(self.jammer_frame, width=40, validate="key", validatecommand=self.v_alt_key)
            elif r == 3: 
                ent = tk.Entry(self.jammer_frame, width=40, validate="key", validatecommand=self.v_range_key)
            
            lbl.grid(row=r, column=0, padx=(0,10), pady=5, sticky="e")
            ent.grid(row=r, column=1, pady=5, sticky="we")
            self.jammer_entries.append(ent)
            self.jammer_widgets.append((lbl, ent))
        
        self.jammer_delay_lbl = tk.Label(self.jammer_frame, text="Opóźnienie jammera (s):", width=28, anchor="e")
        self.jammer_delay_ent = tk.Entry(self.jammer_frame, width=40, validate="key", validatecommand=self.v_sec_key)
        
        self.jammer_duration_lbl = tk.Label(self.jammer_frame, text="Czas trwania jammera (s):", width=28, anchor="e")
        self.jammer_duration_ent = tk.Entry(self.jammer_frame, width=40, validate="key", validatecommand=self.v_sec_key)

        self.jammer_delay_lbl.grid(row=4, column=0, padx=(0,10), pady=5, sticky="e")
        self.jammer_delay_ent.grid(row=4, column=1, pady=5, sticky="we")
        self.jammer_duration_lbl.grid(row=5, column=0, padx=(0,10), pady=5, sticky="e")
        self.jammer_duration_ent.grid(row=5, column=1, pady=5, sticky="we")

        self.jammer_type_var = tk.StringVar(value="BB") 

        jammer_types = [
            ("Szum szerokopasmowy (Broadband Noise)", "BB"),
            ("Sygnał o stałej fali (Continuous Wave - CW)", "CW"),
            ("Jammer przemiatany (Swept / Chirp Jammer)", "SWEEP"),
            ("Jammer impulsowy (Pulsed Jammer)", "PULSED")
        ]

        jammer_radios_frame = tk.Frame(self.jammer_frame)
        jammer_radios_frame.grid(row=6, column=0, columnspan=2, pady=(10,0), sticky="w")

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

        self.spoofer_frame = tk.Frame(self.root_frame)
        self.spoofer_frame.grid(row=6, column=0, pady=(16,8), sticky="w")
        self.spoofer_frame.columnconfigure(0, weight=1)

        warning_text = "Generowanie sygnału spoofera działa tylko na odbiorniku statycznym"
        self.spoofer_warning_lbl = tk.Label(
            self.spoofer_frame,
            text=warning_text,
            fg="#c62828",
            font=("Arial", 10, "bold"),
            wraplength=420,
            justify="left"
        )

        self.spoofer_config_frame = tk.Frame(self.spoofer_frame)
        self.spoofer_config_frame.grid(row=1, column=0, sticky="we")
        self.spoofer_config_frame.columnconfigure(1, weight=1)

        # Tryb ataku
        self.spoofer_attack_var = tk.StringVar(value="jump")
        attack_frame = tk.Frame(self.spoofer_config_frame)
        attack_frame.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0,10))
        attack_frame.columnconfigure(1, weight=1)
        tk.Label(attack_frame, text="Tryb ataku spoofującego:", font=("Arial", 10, "bold"))\
            .grid(row=0, column=0, columnspan=2, sticky="w")
        tk.Radiobutton(attack_frame, text="Position Jump Attack (Overt Spoofing)",
                       variable=self.spoofer_attack_var, value="jump")\
            .grid(row=1, column=0, sticky="w", padx=(10,0))
        tk.Radiobutton(attack_frame, text="Constellation Inconsistency (Ghosting)",
                       variable=self.spoofer_attack_var, value="ghost")\
            .grid(row=1, column=1, sticky="w", padx=(24,0))

        # Lokalizacja nadajnika
        tk.Label(self.spoofer_config_frame, text="Lokalizacja nadajnika:", font=("Arial", 10, "bold"))\
            .grid(row=1, column=0, columnspan=2, sticky="w", pady=(0,4))
        emitter_labels = [
            "Szerokość geograficzna spoofera:",
            "Długość geograficzna spoofera:",
            "Wysokość (m n.p.m.):",
            "Zasięg nadajnika (m):"
        ]
        validators = [self.v_lat_key, self.v_lon_key, self.v_alt_key, self.v_range_key]
        self.spoofer_emitter_entries = []
        for idx, label in enumerate(emitter_labels, start=2):
            lbl = tk.Label(self.spoofer_config_frame, text=label, width=32, anchor="e")
            ent = tk.Entry(self.spoofer_config_frame, width=40, validate="key", validatecommand=validators[idx-2])
            lbl.grid(row=idx, column=0, padx=(0,10), pady=4, sticky="e")
            ent.grid(row=idx, column=1, pady=4, sticky="we")
            self.spoofer_emitter_entries.append(ent)

        # Ustawienia czasu
        timing_frame = tk.Frame(self.spoofer_config_frame)
        timing_frame.grid(row=6, column=0, columnspan=2, sticky="we", pady=(8,4))
        timing_frame.columnconfigure(1, weight=1)
        tk.Label(timing_frame, text="Ustawienia czasu spoofera:", font=("Arial", 10, "bold"))\
            .grid(row=0, column=0, columnspan=2, sticky="w", pady=(0,4))
        tk.Label(timing_frame, text="Opóźnienie startu (s, potem do końca):", width=32, anchor="e")\
            .grid(row=1, column=0, padx=(0,10), pady=3, sticky="e")
        self.spoofer_delay_ent = tk.Entry(timing_frame, width=20, validate="key", validatecommand=self.v_sec_key)
        self.spoofer_delay_ent.grid(row=1, column=1, pady=3, sticky="we")

        # Tryb sygnału spoofowanego
        self.spoof_signal_mode_var = tk.StringVar(value="static")
        signal_mode_frame = tk.Frame(self.spoofer_config_frame)
        signal_mode_frame.grid(row=7, column=0, columnspan=2, sticky="w", pady=(10,4))
        signal_mode_frame.columnconfigure(1, weight=1)
        tk.Label(signal_mode_frame, text="Tryb sygnału spoofowanego:", font=("Arial", 10, "bold"))\
            .grid(row=0, column=0, columnspan=2, sticky="w")
        tk.Radiobutton(signal_mode_frame, text="Statyczny", variable=self.spoof_signal_mode_var,
                       value="static", command=self.update_spoof_signal_mode)\
            .grid(row=1, column=0, sticky="w", padx=(10,0))
        tk.Radiobutton(signal_mode_frame, text="Ruchomy", variable=self.spoof_signal_mode_var,
                       value="mobile", command=self.update_spoof_signal_mode)\
            .grid(row=1, column=1, sticky="w", padx=(24,0))

        # Statyczna lokalizacja fikcyjna
        self.spoof_static_frame = tk.Frame(self.spoofer_config_frame)
        self.spoof_static_frame.grid(row=8, column=0, columnspan=2, sticky="we")
        tk.Label(self.spoof_static_frame, text="Lokalizacja fikcyjna (statyczna):",
                 font=("Arial", 10, "bold"))\
            .grid(row=0, column=0, columnspan=2, sticky="w", pady=(0,4))
        static_labels = [
            "Szerokość geograficzna fikcyjnej lokalizacji:",
            "Długość geograficzna fikcyjnej lokalizacji:",
            "Wysokość (m n.p.m.) fikcyjnej lokalizacji:"
        ]
        static_validators = [self.v_lat_key, self.v_lon_key, self.v_alt_key]
        self.spoof_static_entries = []
        for idx, label in enumerate(static_labels, start=1):
            lbl = tk.Label(self.spoof_static_frame, text=label, width=40, anchor="e")
            ent = tk.Entry(self.spoof_static_frame, width=40, validate="key", validatecommand=static_validators[idx-1])
            lbl.grid(row=idx, column=0, padx=(0,10), pady=3, sticky="e")
            ent.grid(row=idx, column=1, pady=3, sticky="we")
            self.spoof_static_entries.append(ent)

        # Ruchoma lokalizacja fikcyjna
        self.spoof_mobile_frame = tk.Frame(self.spoofer_config_frame)
        self.spoof_mobile_frame.grid(row=9, column=0, columnspan=2, sticky="we", pady=(8,0))
        self.spoof_mobile_frame.columnconfigure(1, weight=1)
        self.spoof_mobile_frame.columnconfigure(3, weight=1)
        tk.Label(self.spoof_mobile_frame, text="Lokalizacja fikcyjna (ruchoma):",
                 font=("Arial", 10, "bold"))\
            .grid(row=0, column=0, columnspan=4, sticky="w", pady=(0,4))

        mobile_pairs = [
            ("Początkowa szerokość geograficzna:", self.v_lat_key,
             "Końcowa szerokość geograficzna:", self.v_lat_key),
            ("Początkowa długość geograficzna:", self.v_lon_key,
             "Końcowa długość geograficzna:", self.v_lon_key),
            ("Początkowa wysokość (m n.p.m.):", self.v_alt_key,
             "Końcowa wysokość (m n.p.m.):", self.v_alt_key)
        ]

        start_entries = []
        end_entries = []
        row_offset = 1
        for row_idx, (start_label, start_validator, end_label, end_validator) in enumerate(mobile_pairs):
            grid_row = row_offset + row_idx
            start_lbl = tk.Label(self.spoof_mobile_frame, text=start_label, width=32, anchor="e")
            start_ent = tk.Entry(self.spoof_mobile_frame, width=32, validate="key", validatecommand=start_validator)
            end_lbl = tk.Label(self.spoof_mobile_frame, text=end_label, width=32, anchor="e")
            end_ent = tk.Entry(self.spoof_mobile_frame, width=32, validate="key", validatecommand=end_validator)

            start_lbl.grid(row=grid_row, column=0, padx=(0,10), pady=3, sticky="e")
            start_ent.grid(row=grid_row, column=1, pady=3, sticky="we")
            end_lbl.grid(row=grid_row, column=2, padx=(24,10), pady=3, sticky="e")
            end_ent.grid(row=grid_row, column=3, pady=3, sticky="we")

            start_entries.append(start_ent)
            end_entries.append(end_ent)

        self.spoof_mobile_entries = start_entries + end_entries

        self.update_spoof_signal_mode()
        self.spoofer_frame.grid_remove()

        tk.Button(self.root_frame, text="START", bg="#4CAF50", fg="white",
                  font=("Arial", 11, "bold"), width=15,
                  command=self.on_start).grid(row=7, column=0, pady=24, sticky="w")

        # konfig 
        self.ALT_MIN = -500.0
        self.ALT_MAX = 20000.0
        base_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.abspath(os.path.join(base_dir, os.pardir))
        gps_dir  = os.path.join(root_dir, "gps-sdr-sim")
        self.GPS_SDR_SIM_PATH  = os.path.join(gps_dir, "gps-sdr-sim")
        self.EPHERIS_FILE_PATH = os.path.join(gps_dir, "brdc2830.25n")
        self.JAMMERS_DIR_PATH = os.path.join(base_dir, "jammers")
        self.MIXER_SCRIPT_PATH = os.path.join(base_dir, "add_jammer_and_mix.py")
        self.WEAKEN_SCRIPT_PATH = os.path.join(base_dir, "weaken_gps.py")
        self.SPOOFER_MIXER_PATH = os.path.join(base_dir, "spoofer_mixer.py")
        self.set_basic_defaults()

    def _validate_lat_key(self, P: str) -> bool:
        if P == "":
            return True
        return re.fullmatch(r"^-?\d{0,2}(\.\d{0,7})?$", P) is not None

    def _validate_lon_key(self, P: str) -> bool:
        if P == "":
            return True
        return re.fullmatch(r"^-?\d{0,3}(\.\d{0,7})?$", P) is not None

    def _validate_alt_key(self, P: str) -> bool:
        if P == "":
            return True
        return re.fullmatch(r"^-?\d{0,6}(\.\d{0,3})?$", P) is not None

    def _validate_seconds_key(self, P: str) -> bool:
        return P.isdigit() or P == ""

    def _validate_range_key(self, P: str) -> bool:
        if P == "":
            return True
        return re.fullmatch(r"^\d{0,6}(\.\d{0,2})?$", P) is not None

    def _validate_filename_focusout(self, P: str) -> bool:
        if P.strip() == "":
            return True
        return P.lower().endswith(".bin")

    def _validate_float_key(self, P: str) -> bool:
        if P == "":
            return True
        return re.fullmatch(r"^-?\d{0,5}(\.\d{0,4})?$", P) is not None

    def toggle_ruchomy(self):
        self.is_ruchomy.set(not self.is_ruchomy.get())
        if self.is_ruchomy.get():
            self.ruchomy_button.config(text="Tak", bg="#4CAF50")
        else:
            self.ruchomy_button.config(text="Nie", bg="#f44336")
        self.update_fields_visibility()

    def on_mode_change(self, *args):
        self.update_fields_visibility()

    def update_fields_visibility(self):
        base_count = 8 if self.is_ruchomy.get() else 5  
        self.update_input_visibility(base_count)
        self.arrange_receiver_rows()

        if self.mode_var.get() == "B":
            self.jammer_frame.grid()

            if self.is_ruchomy.get():
                self.jammer_delay_lbl.grid_remove()
                self.jammer_delay_ent.grid_remove()
                self.jammer_duration_lbl.grid_remove()
                self.jammer_duration_ent.grid_remove()
            else:
                self.jammer_delay_lbl.grid()
                self.jammer_delay_ent.grid()
                self.jammer_duration_lbl.grid()
                self.jammer_duration_ent.grid()
        else:
            self.jammer_frame.grid_remove()

        if self.mode_var.get() == "C":
            self.spoofer_frame.grid()
            self.update_spoof_signal_mode()
            self.update_spoofer_accessibility()
        else:
            self.spoofer_frame.grid_remove()

    def update_input_visibility(self, count):
        for r, (lbl, ent) in enumerate(self.row_widgets):
            if r < count:
                lbl.grid()
                ent.grid()
            else:
                lbl.grid_remove()
                ent.grid_remove()

    def arrange_receiver_rows(self):
        if not hasattr(self, "row_widgets"):
            return

        if not self.is_ruchomy.get():
            self.form.columnconfigure(2, weight=0, minsize=0)
            self.form.columnconfigure(3, weight=0, minsize=0)
            return

        self.form.columnconfigure(2, weight=0, minsize=40)
        self.form.columnconfigure(3, weight=1)

        coordinate_pairs = [
            (2, 5),  # lat
            (3, 6),  # lon
            (4, 7)   # alt
        ]
        for row_idx, (start_idx, end_idx) in enumerate(coordinate_pairs, start=2):
            start_lbl, start_ent = self.row_widgets[start_idx]
            end_lbl, end_ent = self.row_widgets[end_idx]

            start_lbl.grid_configure(row=row_idx, column=0, padx=(0, 10), pady=5, sticky="e")
            start_ent.grid_configure(row=row_idx, column=1, pady=5, sticky="we")

            end_lbl.grid(row=row_idx, column=2, padx=(24, 10), pady=5, sticky="e")
            end_ent.grid(row=row_idx, column=3, pady=5, sticky="we")

    def update_spoof_signal_mode(self):
        if not hasattr(self, "spoof_static_frame"):
            return
        is_mobile = getattr(self, "spoof_signal_mode_var", tk.StringVar(value="static")).get() == "mobile"
        if is_mobile:
            self.spoof_static_frame.grid_remove()
            self.spoof_mobile_frame.grid()
        else:
            self.spoof_mobile_frame.grid_remove()
            self.spoof_static_frame.grid()

    def update_spoofer_accessibility(self):
        if not hasattr(self, "spoofer_config_frame"):
            return
        receiver_mobile = self.is_ruchomy.get()
        if receiver_mobile and self.mode_var.get() == "C":
            self.spoofer_warning_lbl.grid(row=0, column=0, sticky="w", pady=(0,8))
            self.spoofer_config_frame.grid_remove()
        else:
            self.spoofer_warning_lbl.grid_remove()
            self.spoofer_config_frame.grid(row=1, column=0, sticky="we")

    def set_basic_defaults(self):
        # domysle wartosci
        defaults = [
            "test.bin",
            "250",
            "50.0000000",
            "19.9000000",
            "225.0",
            "50.0000000",
            "19.9080000",
            "225.0",
        ]
        for i, val in enumerate(defaults):
            if i < len(self.entries):
                self.entries[i].delete(0, tk.END)
                self.entries[i].insert(0, val)

        jammer_defaults = [
            "50.0000000",
            "19.9040000",
            "225.0",
            "20"
        ]
        for i, val in enumerate(jammer_defaults):
            if i < len(self.jammer_entries):
                self.jammer_entries[i].delete(0, tk.END)
                self.jammer_entries[i].insert(0, val)
        self.jammer_delay_ent.delete(0, tk.END)
        self.jammer_delay_ent.insert(0, "60") 
        self.jammer_duration_ent.delete(0, tk.END)
        self.jammer_duration_ent.insert(0, "30")

        spoofer_emitter_defaults = [
            "50.0000500",
            "19.9050500",
            "225.0",
            "500"
        ]
        for entry, val in zip(self.spoofer_emitter_entries, spoofer_emitter_defaults):
            entry.delete(0, tk.END)
            entry.insert(0, val)

        self.spoofer_delay_ent.delete(0, tk.END)
        self.spoofer_delay_ent.insert(0, "70")

        spoof_static_defaults = [
            "50.0500000",
            "19.9500000",
            "225.0"
        ]
        for entry, val in zip(self.spoof_static_entries, spoof_static_defaults):
            entry.delete(0, tk.END)
            entry.insert(0, val)

        spoof_mobile_defaults = [
            "50.0500000",
            "19.9500000",
            "225.0",
            "50.0900000",
            "19.9600000",
            "225.0"
        ]
        for entry, val in zip(self.spoof_mobile_entries, spoof_mobile_defaults):
            entry.delete(0, tk.END)
            entry.insert(0, val)

        self.spoof_signal_mode_var.set("static")
        self.update_spoof_signal_mode()
        env_defaults = ["21.0", "1013.0", "50.0"]
        for i, val in enumerate(env_defaults):
            self.env_entries[i].delete(0, tk.END)
            self.env_entries[i].insert(0, val)

    def start_btn_state(self, enabled: bool):
        for child in self.root_frame.grid_slaves(row=6, column=0):
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
                msg = f"Plik został wygenerowany pomyślnie!\n\nNazwa pliku: {output_filename}\nLokalizacja: /GPS-JAMMING/GpsJammerApp"
            else:
                msg = f"Błąd podczas generowania (kod {rc})"
            
            self.after(0, lambda: messagebox.showinfo("gps-sdr-sim", f"{msg}\n\n" ))
        except FileNotFoundError:
            self.after(0, lambda: messagebox.showerror("Error", f"Nie znaleziono gps-sdr-sim w: {self.GPS_SDR_SIM_PATH}"))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Error", f"Wystąpił wyjątek: {e}"))
        finally:
            self.after(0, lambda: self.start_btn_state(True))

    def _run_weaken_sequence_thread(self, gps_cmd, weaken_cmd, final_filename):
        """Sekwencja dla trybu A: Generowanie GPS -> Osłabianie sygnału"""
        try:
            print("--- ROZPOCZĘCIE SEKWENCJI OSŁABIANIA GPS ---")
            print(f"Polecenie: {' '.join(gps_cmd)}")
            result_gps = subprocess.run(gps_cmd, capture_output=True, text=True, check=True, encoding='utf-8')
            print(result_gps.stderr)
            print("Krok 1/2: Sygnał GPS wygenerowany.")

            print(f"Krok 2/2: Osłabianie sygnału GPS...")
            print(f"Polecenie: {' '.join(weaken_cmd)}")
            result_weaken = subprocess.run(weaken_cmd, capture_output=True, text=True, check=True, encoding='utf-8')
            print(result_weaken.stdout)
            if result_weaken.stderr:
                print(result_weaken.stderr)
            print("Krok 2/2: Osłabianie zakończone.")
            
            traj_file = 'traj.csv'
            if os.path.exists(traj_file):
                try:
                    os.remove(traj_file)
                    print(f"Plik {traj_file} został pomyślnie usunięty.")
                except OSError as e:
                    print(f"Ostrzeżenie: Nie można usunąć pliku {traj_file}. Błąd: {e}")
            
            msg = (f"Symulacja z osłabionym sygnałem GPS zakończona pomyślnie!\n\n"
                   f"Plik wyjściowy: {final_filename}\n"
                   f"(Oryginalny plik GPS został nadpisany)")
            self.after(0, lambda: messagebox.showinfo("Sukces", msg))

        except subprocess.CalledProcessError as e:
            error_msg = (f"Błąd podczas wykonywania polecenia:\n{' '.join(e.cmd)}\n\n"
                         f"Błąd (stderr):\n{e.stderr}\n\n"
                         f"Output (stdout):\n{e.stdout}")
            print(f"BŁĄD SEKWENCJI: {error_msg}")
            self.after(0, lambda: messagebox.showerror("Błąd sekwencji", error_msg))
        except FileNotFoundError as e:
            error_msg = f"Nie znaleziono pliku lub skryptu: {e.filename}"
            print(f"BŁĄD SEKWENCJI: {error_msg}")
            self.after(0, lambda: messagebox.showerror("Błąd - brak pliku", error_msg))
        except Exception as e:
            error_msg = f"Wystąpił nieoczekiwany błąd: {e}"
            print(f"BŁĄD SEKWENCJI: {error_msg}")
            self.after(0, lambda: messagebox.showerror("Błąd", error_msg))
        finally:
            print("--- ZAKOŃCZENIE SEKWENCJI OSŁABIANIA GPS ---")
            self.after(0, lambda: self.start_btn_state(True))

    def _run_jammer_sequence_thread(self, gps_cmd, jammer_cmd, mixer_cmd, final_filename):
        try:
            print("--- ROZPOCZĘCIE SEKWENCJI JAMMERA ---")
            print(f"Polecenie: {' '.join(gps_cmd)}")
            result_gps = subprocess.run(gps_cmd, capture_output=True, text=True, check=True, encoding='utf-8')
            print(result_gps.stderr)
            print("Krok 1/3: Sygnał GPS wygenerowany.")

            print(f"Krok 2/3: Uruchamianie skryptu jammera...")
            result_jammer = subprocess.run(jammer_cmd, capture_output=True, text=True, check=True, encoding='utf-8')
            print(result_jammer.stdout)
            if result_jammer.stderr:
                print(result_jammer.stderr)
            print("Krok 2/3: Sygnał jammera wygenerowany.")

            print(f"Polecenie: {' '.join(mixer_cmd)}")
            result_mixer = subprocess.run(mixer_cmd, capture_output=True, text=True, check=True, encoding='utf-8')
            print(result_mixer.stdout)
            if result_mixer.stderr:
                print(result_mixer.stderr)
            print("Krok 3/3: Miksowanie zakończone.")
            
            msg = (f"Symulacja z jammerem zakończona pomyślnie!\n\n"
                   f"Plik wyjściowy: {final_filename}\n"
                   f"(Oryginalny plik GPS został nadpisany)")
            self.after(0, lambda: messagebox.showinfo("Sukces", msg))

        except subprocess.CalledProcessError as e:
            error_msg = (f"Błąd podczas wykonywania polecenia:\n{' '.join(e.cmd)}\n\n"
                         f"Błąd (stderr):\n{e.stderr}\n\n"
                         f"Output (stdout):\n{e.stdout}")
            print(f"BŁĄD SEKWENCJI: {error_msg}")
            self.after(0, lambda: messagebox.showerror("Błąd sekwencji", error_msg))
        except FileNotFoundError as e:
            error_msg = f"Nie znaleziono pliku lub skryptu: {e.filename}"
            print(f"BŁĄD SEKWENCJI: {error_msg}")
            self.after(0, lambda: messagebox.showerror("Błąd - brak pliku", error_msg))
        except Exception as e:
            error_msg = f"Wystąpił nieoczekiwany błąd: {e}"
            print(f"BŁĄD SEKWENCJI: {error_msg}")
            self.after(0, lambda: messagebox.showerror("Błąd", error_msg))
        finally:
            print("--- ZAKOŃCZENIE SEKWENCJI JAMMERA ---")
            self.after(0, lambda: self.start_btn_state(True))

    def _run_spoofer_sequence_thread(self, gps_legit_cmd, gps_spoof_cmd, mixer_cmd,
                                     legit_filename, final_filename, cleanup_paths=None):
        cleanup_paths = cleanup_paths or []
        try:
            print("--- ROZPOCZĘCIE SEKWENCJI SPOOFERA ---")
            print(f"Polecenie (LEGIT): {' '.join(gps_legit_cmd)}")
            result_legit = subprocess.run(gps_legit_cmd, capture_output=True, text=True, check=True, encoding='utf-8')
            if result_legit.stdout:
                print(result_legit.stdout)
            if result_legit.stderr:
                print(result_legit.stderr)
            print("Krok 1/3: Sygnał LEGIT wygenerowany.")

            print(f"Polecenie (SPOOFER): {' '.join(gps_spoof_cmd)}")
            result_spoof = subprocess.run(gps_spoof_cmd, capture_output=True, text=True, check=True, encoding='utf-8')
            if result_spoof.stdout:
                print(result_spoof.stdout)
            if result_spoof.stderr:
                print(result_spoof.stderr)
            print("Krok 2/3: Sygnał fikcyjny wygenerowany.")

            print(f"Polecenie (MIXER): {' '.join(mixer_cmd)}")
            result_mix = subprocess.run(mixer_cmd, capture_output=True, text=True, check=True, encoding='utf-8')
            if result_mix.stdout:
                print(result_mix.stdout)
            if result_mix.stderr:
                print(result_mix.stderr)
            print("Krok 3/3: Miksowanie zakończone.")

            msg = (f"Symulacja ze spooferem zakończona pomyślnie!\n\n"
                   f"Plik LEGIT: {legit_filename}\n"
                   f"Plik docelowy: {final_filename}")
            self.after(0, lambda: messagebox.showinfo("Sukces", msg))

        except subprocess.CalledProcessError as e:
            error_msg = (f"Błąd podczas wykonywania polecenia:\n{' '.join(e.cmd)}\n\n"
                         f"Błąd (stderr):\n{e.stderr}\n\n"
                         f"Output (stdout):\n{e.stdout}")
            print(f"BŁĄD SEKWENCJI: {error_msg}")
            self.after(0, lambda: messagebox.showerror("Błąd sekwencji", error_msg))
        except FileNotFoundError as e:
            error_msg = f"Nie znaleziono pliku lub skryptu: {e.filename}"
            print(f"BŁĄD SEKWENCJI: {error_msg}")
            self.after(0, lambda: messagebox.showerror("Błąd - brak pliku", error_msg))
        except Exception as e:
            error_msg = f"Wystąpił nieoczekiwany błąd: {e}"
            print(f"BŁĄD SEKWENCJI: {error_msg}")
            self.after(0, lambda: messagebox.showerror("Błąd", error_msg))
        finally:
            for artifact in cleanup_paths:
                if artifact in (None, ""):
                    continue
                if artifact == final_filename:
                    continue
                try:
                    if os.path.exists(artifact):
                        os.remove(artifact)
                        print(f"Usunięto plik tymczasowy: {artifact}")
                except OSError as e:
                    print(f"Ostrzeżenie: Nie można usunąć pliku {artifact}: {e}")
            print("--- ZAKOŃCZENIE SEKWENCJI SPOOFERA ---")
            self.after(0, lambda: self.start_btn_state(True))

    def on_start(self):
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

        env_labels = ["Temperature", "Ciśnienie", "Wilgotność"]
        env_values = [entry.get().strip() for entry in self.env_entries]
        env_numeric = []
        for idx, value in enumerate(env_values):
            if value == "":
                messagebox.showerror("Błąd", f"{env_labels[idx]} musi być wypełniona.")
                self.env_entries[idx].focus_set(); return
            try:
                env_numeric.append(float(value))
            except ValueError:
                messagebox.showerror("Błąd", f"{env_labels[idx]} musi być liczbą.")
                self.env_entries[idx].focus_set(); return
        temperature, pressure, humidity = env_numeric
        env_flags = ["-C", f"{temperature}", "-P", f"{pressure}", "-H", f"{humidity}"]

        TIMEREG = re.compile(r"^\d{4}/\d{2}/\d{2},\d{2}:\d{2}:\d{2}$")
        t_stationary = T_STATIONARY if TIMEREG.match(T_STATIONARY) else "2025/10/10,00:00:00"
        t_mobile     = T_MOBILE     if TIMEREG.match(T_MOBILE)     else "2025/10/10,00:00:00"

        if mode == "A":
            # Tryb A: Generowanie GPS -> Osłabianie sygnału (bez jammera)
            gps_cmd = []
            if not self.is_ruchomy.get():
                lat = values[idx_lat_start]
                lon = values[idx_lon_start]
                alt = values[idx_alt_start]
                gps_cmd = [
                    self.GPS_SDR_SIM_PATH,
                    "-e", self.EPHERIS_FILE_PATH,
                    "-l", f"{lat},{lon},{alt}",
                    "-b", BITS,
                    "-d", str(seconds),
                    "-T", t_stationary,
                    "-o", filename,
                    "-s", SAMPLERATE
                ]
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

                gps_cmd = [
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
            gps_cmd.extend(env_flags)
            
            weaken_cmd = [
                sys.executable,
                self.WEAKEN_SCRIPT_PATH,
                "--input-file", filename,
                "--output-file", filename 
            ]
            
            print(f"Rozpoczynanie sekwencji Trybu A (Osłabiony GPS) dla pliku: {filename}")
            self.start_btn_state(False)
            threading.Thread(
                target=self._run_weaken_sequence_thread,
                args=(gps_cmd, weaken_cmd, filename),
                daemon=True
            ).start()
        
        elif mode == "B":
            try:
                jammer_lat = self.jammer_entries[0].get().strip()
                jammer_lon = self.jammer_entries[1].get().strip()
                jammer_alt = self.jammer_entries[2].get().strip() 
                jammer_range = self.jammer_entries[3].get().strip() 
            except IndexError:
                messagebox.showerror("Błąd", "Nie można odnaleźć pól jammera.")
                return

            if not self._lon_in_range(jammer_lon):
                messagebox.showerror("Błąd", "Długość geograficzna jammera jest nieprawidłowa.")
                self.jammer_entries[0].focus_set(); return
            if not self._lat_in_range(jammer_lat):
                messagebox.showerror("Błąd", "Szerokość geograficzna jammera jest nieprawidłowa.")
                self.jammer_entries[1].focus_set(); return
            
            if not self._alt_in_range(jammer_alt):
                messagebox.showerror("Błąd", f"Wysokość jammera musi być w zakresie {self.ALT_MIN}..{self.ALT_MAX} m.")
                self.jammer_entries[2].focus_set(); return
            
            if not self._range_in_range(jammer_range): 
                messagebox.showerror("Błąd", "Zasięg jammera jest nieprawidłowy (musi być > 0).")
                self.jammer_entries[3].focus_set(); return 
            
            jammer_type_key = self.jammer_type_var.get()
            
            gps_cmd = []
            if not self.is_ruchomy.get():
                lat = values[idx_lat_start]
                lon = values[idx_lon_start]
                alt = values[idx_alt_start]
                gps_cmd = [
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

                gps_cmd = [
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
            gps_cmd.extend(env_flags)

            script_map = {
                "SWEEP": "chirpJammer.py",
                "PULSED": "pulsedJammer.py",
                "CW": "cwJammer.py",
                "BB": "broadbandJammer.py"
            }
            
            jammer_script_name = script_map.get(jammer_type_key)
            if not jammer_script_name:
                messagebox.showerror("Błąd", f"Nie znaleziono skryptu dla typu jammera: {jammer_type_key}")
                return
                
            jammer_script_path = os.path.join(self.JAMMERS_DIR_PATH, jammer_script_name)

            jammer_cmd = [
                sys.executable, 
                jammer_script_path
            ]

            gps_input_file = filename 
            final_output_file = filename 
            
            #jammer_alt = "350.0" 

            mixer_cmd = [
                sys.executable,
                self.MIXER_SCRIPT_PATH,
                "--gps-file", gps_input_file,
                "--output-file", final_output_file,
                "--jammer-lat", jammer_lat,
                "--jammer-lon", jammer_lon,
                "--jammer-alt", jammer_alt,
                "--jammer-range", jammer_range,
                "--samplerate", SAMPLERATE
                # --jammer-file, mozna dodac swój plik jammera"
            ]
            if not self.is_ruchomy.get():
                delay_txt = self.jammer_delay_ent.get().strip()
                if not delay_txt.isdigit() or int(delay_txt) < 0:
                    messagebox.showerror("Błąd", "Opóźnienie jammera (s) musi być liczbą całkowitą >= 0.")
                    self.jammer_delay_ent.focus_set(); return
                delay_sec = int(delay_txt)

                duration_txt = self.jammer_duration_ent.get().strip()
                if not duration_txt.isdigit() or int(duration_txt) <= 0:
                    messagebox.showerror("Błąd", "Czas trwania jammera (s) musi być liczbą całkowitą > 0.")
                    self.jammer_duration_ent.focus_set(); return
                
                if delay_sec >= seconds:
                    messagebox.showwarning("Ostrzeżenie", 
                        f"Opóźnienie jammera ({delay_sec}s) jest równe lub dłuższe niż całkowity czas próbki ({seconds}s). "
                        "Jammer nie zostanie uruchomiony.")
                
                static_lat = values[idx_lat_start]
                static_lon = values[idx_lon_start]
                static_alt = values[idx_alt_start]
                
                mixer_cmd.extend([
                    "--delay-seconds", delay_txt,
                    "--duration-seconds", duration_txt,
                    "--static-lat", static_lat,
                    "--static-lon", static_lon,
                    "--static-alt", static_alt
                ])

            print(f"Rozpoczynanie sekwencji Trybu B (Jammer) dla pliku: {filename}")
            self.start_btn_state(False) 
            threading.Thread(
                target=self._run_jammer_sequence_thread, 
                args=(gps_cmd, jammer_cmd, mixer_cmd, final_output_file), 
                daemon=True
            ).start()

        elif mode == "C":
            if self.is_ruchomy.get():
                messagebox.showerror("Błąd", "Generowanie sygnału spoofera działa tylko na odbiorniku statycznym.")
                return

            legit_filename = self._build_variant_filename(filename, "_legit")
            spoofer_filename = self._build_variant_filename(filename, "_spoofer")
            spoofed_filename = self._build_variant_filename(filename, "_spoofed")
            cleanup_paths = [spoofer_filename]

            try:
                spoofer_lat = self.spoofer_emitter_entries[0].get().strip()
                spoofer_lon = self.spoofer_emitter_entries[1].get().strip()
                spoofer_alt = self.spoofer_emitter_entries[2].get().strip()
                spoofer_range = self.spoofer_emitter_entries[3].get().strip()
            except IndexError:
                messagebox.showerror("Błąd", "Nie można odnaleźć pól lokalizacji nadajnika.")
                return

            if not self._lat_in_range(spoofer_lat):
                messagebox.showerror("Błąd", "Szerokość geograficzna spoofera jest nieprawidłowa.")
                self.spoofer_emitter_entries[0].focus_set(); return
            if not self._lon_in_range(spoofer_lon):
                messagebox.showerror("Błąd", "Długość geograficzna spoofera jest nieprawidłowa.")
                self.spoofer_emitter_entries[1].focus_set(); return
            if not self._alt_in_range(spoofer_alt):
                messagebox.showerror("Błąd", f"Wysokość spoofera musi być w zakresie {self.ALT_MIN}..{self.ALT_MAX} m.")
                self.spoofer_emitter_entries[2].focus_set(); return
            if not self._range_in_range(spoofer_range):
                messagebox.showerror("Błąd", "Zasięg nadajnika jest nieprawidłowy (musi być > 0).")
                self.spoofer_emitter_entries[3].focus_set(); return

            attack_type = self.spoofer_attack_var.get()
            signal_mode = self.spoof_signal_mode_var.get()

            delay_txt = self.spoofer_delay_ent.get().strip()
            if not delay_txt.isdigit() or int(delay_txt) < 0:
                messagebox.showerror("Błąd", "Opóźnienie spoofera (s) musi być liczbą całkowitą ≥ 0.")
                self.spoofer_delay_ent.focus_set(); return
            delay_sec = int(delay_txt)
            duration_sec = max(0, seconds - delay_sec)

            if delay_sec >= seconds:
                messagebox.showwarning(
                    "Ostrzeżenie",
                    f"Opóźnienie spoofera ({delay_sec}s) jest równe lub dłuższe niż całkowity czas próbki ({seconds}s).\n"
                    "Spoofer nie zostanie uruchomiony."
                )

            fictitious_static = None
            fictitious_mobile = None
            fake_traj_path = None
            fake_traj_name = None
            if signal_mode == "static":
                fake_lat = self.spoof_static_entries[0].get().strip()
                fake_lon = self.spoof_static_entries[1].get().strip()
                fake_alt = self.spoof_static_entries[2].get().strip()
                if not self._lat_in_range(fake_lat):
                    messagebox.showerror("Błąd", "Szerokość geograficzna fikcyjnej lokalizacji jest nieprawidłowa.")
                    self.spoof_static_entries[0].focus_set(); return
                if not self._lon_in_range(fake_lon):
                    messagebox.showerror("Błąd", "Długość geograficzna fikcyjnej lokalizacji jest nieprawidłowa.")
                    self.spoof_static_entries[1].focus_set(); return
                if not self._alt_in_range(fake_alt):
                    messagebox.showerror("Błąd", "Wysokość fikcyjnej lokalizacji jest nieprawidłowa.")
                    self.spoof_static_entries[2].focus_set(); return
                fictitious_static = {
                    "lat": fake_lat,
                    "lon": fake_lon,
                    "alt": fake_alt
                }
            else:
                mobile_values = [entry.get().strip() for entry in self.spoof_mobile_entries]
                validators = [self._lat_in_range, self._lon_in_range, self._alt_in_range,
                              self._lat_in_range, self._lon_in_range, self._alt_in_range]
                labels = [
                    "Początkowa szerokość geograficzna",
                    "Początkowa długość geograficzna",
                    "Początkowa wysokość",
                    "Końcowa szerokość geograficzna",
                    "Końcowa długość geograficzna",
                    "Końcowa wysokość"
                ]
                for val, validator, label, entry in zip(mobile_values, validators, labels, self.spoof_mobile_entries):
                    if not validator(val):
                        messagebox.showerror("Błąd", f"{label} fikcyjnej lokalizacji jest nieprawidłowa.")
                        entry.focus_set(); return
                fictitious_mobile = {
                    "start": {
                        "lat": mobile_values[0],
                        "lon": mobile_values[1],
                        "alt": mobile_values[2]
                    },
                    "end": {
                        "lat": mobile_values[3],
                        "lon": mobile_values[4],
                        "alt": mobile_values[5]
                    }
                }
                fake_traj_name = f"{os.path.splitext(filename)[0]}_spoof_traj.csv"
                fake_traj_path = self.run_generate_trajectory(
                    start_lat=mobile_values[0],
                    start_lon=mobile_values[1],
                    start_alt=mobile_values[2],
                    end_lat=mobile_values[3],
                    end_lon=mobile_values[4],
                    end_alt=mobile_values[5],
                    duration_s=seconds,
                    step_s=0.1,
                    out_file=fake_traj_name,
                    silent=True
                )
                if fake_traj_path is None:
                    return
                cleanup_paths.append(fake_traj_path)

            legit_lat = values[idx_lat_start]
            legit_lon = values[idx_lon_start]
            legit_alt = values[idx_alt_start]

            gps_cmd_legit = [
                self.GPS_SDR_SIM_PATH,
                "-e", self.EPHERIS_FILE_PATH,
                "-l", f"{legit_lat},{legit_lon},{legit_alt}",
                "-b", BITS,
                "-d", str(seconds),
                "-T", t_stationary,
                "-o", legit_filename,
                "-s", SAMPLERATE,
                "-v"
            ]
            gps_cmd_legit.extend(env_flags)

            gps_cmd_spoofer = [
                self.GPS_SDR_SIM_PATH,
                "-e", self.EPHERIS_FILE_PATH
            ]
            if fake_traj_path:
                gps_cmd_spoofer.extend(["-u", fake_traj_path])
            else:
                gps_cmd_spoofer.extend(["-l", f"{fictitious_static['lat']},{fictitious_static['lon']},{fictitious_static['alt']}" ])
            gps_cmd_spoofer.extend([
                "-b", BITS,
                "-d", str(seconds),
                "-T", t_stationary,
                "-o", spoofer_filename,
                "-s", SAMPLERATE,
                "-v"
            ])
            gps_cmd_spoofer.extend(env_flags)

            self.current_spoof_params = {
                "attack_type": attack_type,
                "signal_mode": signal_mode,
                "timing": {
                    "delay_seconds": delay_sec,
                    "duration_seconds": duration_sec
                },
                "emitter": {
                    "lat": spoofer_lat,
                    "lon": spoofer_lon,
                    "alt": spoofer_alt,
                    "range": spoofer_range
                },
                "fictitious_static": fictitious_static,
                "fictitious_mobile": fictitious_mobile
            }

            spoofer_cmd = [
                sys.executable,
                self.SPOOFER_MIXER_PATH,
                "--legit-file", legit_filename,
                "--spoofer-file", spoofer_filename,
                "--output-file", spoofed_filename,
                "--spoofer-lat", spoofer_lat,
                "--spoofer-lon", spoofer_lon,
                "--spoofer-alt", spoofer_alt,
                "--max-range", spoofer_range,
                "--samplerate", SAMPLERATE,
                "--victim-lat", legit_lat,
                "--victim-lon", legit_lon,
                "--victim-alt", legit_alt,
                "--delay-seconds", delay_txt,
            ]

            print(f"Rozpoczynanie sekwencji Trybu C (Spoofer) dla pliku: {filename}")
            self.start_btn_state(False)
            threading.Thread(
                target=self._run_spoofer_sequence_thread,
                args=(
                    gps_cmd_legit,
                    gps_cmd_spoofer,
                    spoofer_cmd,
                    legit_filename,
                    spoofed_filename,
                    cleanup_paths
                ),
                daemon=True
            ).start()

    # pomocnicze
    def _build_variant_filename(self, base_filename: str, suffix: str) -> str:
        base, ext = os.path.splitext(base_filename)
        if not ext:
            ext = ".bin"
        candidate = f"{base}{suffix}{ext}"
        if candidate == base_filename:
            candidate = f"{base}{suffix}_1{ext}"
        return candidate

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

    def run_generate_trajectory(self, start_lat, start_lon, start_alt,
                                end_lat, end_lon, end_alt,
                                duration_s, step_s=1, out_file="traj.csv", silent=False):
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
            if not silent:
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