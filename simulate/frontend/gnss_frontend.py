import tkinter as tk
from tkinter import messagebox
import re

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

        # --- WALIDATORY NA KLAWISZ ---
        # latitude: do 2 cyfr przed kropką, do 7 po kropce
        self.v_lat_key = (self.register(self._validate_lat_key), "%P")
        # longitude: do 3 cyfr przed kropką, do 7 po kropce
        self.v_lon_key = (self.register(self._validate_lon_key), "%P")
        # seconds tylko cyfry
        self.v_sec_key = (self.register(self._validate_seconds_key), "%P")
        # filename .bin na focusout
        self.v_file_focusout = (self.register(self._validate_filename_focusout), "%P")
        # altitude: liczba z opcjonalnym minusem, do 3 miejsc po kropce
        self.v_alt_key = (self.register(self._validate_alt_key), "%P")
        # zasięg jammera: liczba dodatnia, do 2 miejsc po kropce
        self.v_range_key = (self.register(self._validate_range_key), "%P")

        for r, name in enumerate(self.label_names):
            lbl = tk.Label(self.form, text=name, width=28, anchor="e")

            if r == 0:  # Nazwa pliku
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

        # OFF: nazwa + czas + 3 startowe = 5 pól
        self.update_input_visibility(5)

        # ===== TRYBY =====
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

        # ===== START =====
        tk.Button(self.root_frame, text="START", bg="#4CAF50", fg="white",
                  font=("Arial", 11, "bold"), width=15,
                  command=self.on_start).grid(row=5, column=0, pady=24, sticky="w")

        # ---- KONFIG: zakresy (łatwo zmienisz) ----
        self.ALT_MIN = -500.0
        self.ALT_MAX = 20000.0

    # ---------- WALIDATORY (na klawisz / focusout) ----------

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

    # ---------- LOGIKA UI ----------

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
        base_count = 5  # nazwa + czas + 3 podstawowe pola (lon, lat, alt)
        
        # Dodaj pola końcowe jeśli ruchomy = TAK
        if self.is_ruchomy.get():
            base_count = 8  # + 3 pola końcowe
        
        # Aktualizuj główne pola
        self.update_input_visibility(base_count)
        
        # Pokaż/ukryj sekcję jammera
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

    # ---------- START + WALIDACJA KOŃCOWA ----------

    def on_start(self):
        base_count = 8 if self.is_ruchomy.get() else 5
        values = [self.entries[i].get().strip() for i in range(base_count)]
        mode = self.mode_var.get()

        # indeksy głównych pól
        idx_filename = 0
        idx_seconds  = 1
        idx_lon_start = 2
        idx_lat_start = 3
        idx_alt_start = 4
        idx_lon_end   = 5
        idx_lat_end   = 6
        idx_alt_end   = 7

        # Pobierz wartości jammera jeśli tryb Jammer
        jammer_values = []
        if mode == "B":
            jammer_values = [entry.get().strip() for entry in self.jammer_entries]

        # --- Nazwa pliku ---
        filename = values[idx_filename]
        if not filename or not filename.lower().endswith(".bin"):
            messagebox.showerror("Błąd", "Nazwa pliku musi kończyć się na .bin")
            self.entries[idx_filename].focus_set()
            return

        # --- Czas ---
        sec_txt = values[idx_seconds]
        if not sec_txt.isdigit():
            messagebox.showerror("Błąd", "Czas próbki (s) musi być liczbą całkowitą.")
            self.entries[idx_seconds].focus_set()
            return
        seconds = int(sec_txt)
        if not (1 <= seconds <= 86400):
            messagebox.showerror("Błąd", "Czas próbki (s) musi być w zakresie 1..86400.")
            self.entries[idx_seconds].focus_set()
            return

        # --- LON/LAT/ALT start ---
        if not self._lon_in_range(values[idx_lon_start]):
            messagebox.showerror("Błąd", "Długość geograficzna (start) musi być w zakresie −180..180, max 7 miejsc po przecinku.")
            self.entries[idx_lon_start].focus_set()
            return
        if not self._lat_in_range(values[idx_lat_start]):
            messagebox.showerror("Błąd", "Szerokość geograficzna (start) musi być w zakresie −90..90, max 7 miejsc po przecinku.")
            self.entries[idx_lat_start].focus_set()
            return
        if not self._alt_in_range(values[idx_alt_start]):
            messagebox.showerror("Błąd", f"Wysokość (start) musi być liczbą w zakresie {self.ALT_MIN}..{self.ALT_MAX} m.")
            self.entries[idx_alt_start].focus_set()
            return

        # --- LON/LAT/ALT end (jeśli widoczne) ---
        if self.is_ruchomy.get():
            if not self._lon_in_range(values[idx_lon_end]):
                messagebox.showerror("Błąd", "Długość geograficzna (końcowa) musi być w zakresie −180..180, max 7 miejsc po przecinku.")
                self.entries[idx_lon_end].focus_set()
                return
            if not self._lat_in_range(values[idx_lat_end]):
                messagebox.showerror("Błąd", "Szerokość geograficzna (końcowa) musi być w zakresie −90..90, max 7 miejsc po przecinku.")
                self.entries[idx_lat_end].focus_set()
                return
            if not self._alt_in_range(values[idx_alt_end]):
                messagebox.showerror("Błąd", f"Wysokość (końcowa) musi być liczbą w zakresie {self.ALT_MIN}..{self.ALT_MAX} m.")
                self.entries[idx_alt_end].focus_set()
                return

        # --- Pola jammera (jeśli tryb Jammer) ---
        if mode == "B":  # Jammer
            if not self._lon_in_range(jammer_values[0]):  # Długość geograficzna jammera
                messagebox.showerror("Błąd", "Długość geograficzna jammera musi być w zakresie −180..180, max 7 miejsc po przecinku.")
                self.jammer_entries[0].focus_set()
                return
            if not self._lat_in_range(jammer_values[1]):  # Szerokość geograficzna jammera
                messagebox.showerror("Błąd", "Szerokość geograficzna jammera musi być w zakresie −90..90, max 7 miejsc po przecinku.")
                self.jammer_entries[1].focus_set()
                return
            if not self._range_in_range(jammer_values[2]):  # Zasięg jammera
                messagebox.showerror("Błąd", "Zasięg jammera musi być liczbą dodatnią w zakresie 0-100 metrów.")
                self.jammer_entries[2].focus_set()
                return

        if not mode:
            messagebox.showwarning("Uwaga", "Wybierz tryb!")
            return

        message = f"Startuję z wartościami:\nInputy: {values}\nTryb: {mode}\n"
        if mode == "B" and jammer_values:
            message += f"Jammer: {jammer_values}\n"
        
        messagebox.showinfo("Start", message)

    # ---------- Funkcje pomocnicze (dokładniejsze sprawdzanie) ----------

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
        """Zasięg jammera: liczba dodatnia > 0 i <= 100"""
        try:
            if text.strip() == "":
                return False
            val = float(text)
            return 0.0 < val <= 100.0
        except ValueError:
            return False


if __name__ == "__main__":
    app = App()
    app.mainloop()
