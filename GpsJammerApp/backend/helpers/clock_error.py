import json
import sys
import math

def extract_and_calculate(filename):
    """
    Czyta plik, wypisuje wartości na bieżąco i na końcu podaje statystyki.
    """
    clk_bias_values = []
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            buffer = ""
            brace_count = 0
            in_json = False

            for line in f:
                if '{' in line:
                    in_json = True
                
                if in_json:
                    buffer += line
                    brace_count += line.count('{')
                    brace_count -= line.count('}')

                    if brace_count == 0 and buffer.strip():
                        try:
                            json_start_index = buffer.find('{')
                            if json_start_index != -1:
                                clean_json = buffer[json_start_index:]
                                data = json.loads(clean_json)

                                if 'elapsed_time' in data and 'position' in data:
                                    etime = data['elapsed_time']
                                    clk_bias = data['position'].get('clk_bias')
                                    
                                    if clk_bias is not None:
                                        # 1. Wypisz bieżącą linię
                                        print(f"{etime}: {clk_bias}")
                                        # 2. Dodaj do listy do statystyk
                                        clk_bias_values.append(clk_bias)

                        except json.JSONDecodeError:
                            pass
                        
                        buffer = ""
                        brace_count = 0
                        in_json = False

        # --- Sekcja obliczeń statystycznych ---
        if clk_bias_values:
            count = len(clk_bias_values)
            average = sum(clk_bias_values) / count
            
            # Obliczanie największego odchylenia (max |wartość - średnia|)
            max_deviation = max(abs(x - average) for x in clk_bias_values)
            
            print("-" * 30)
            print(f"Liczba próbek: {count}")
            print(f"Średnia (Mean):             {average:.9f}")
            print(f"Max odchylenie od średniej: {max_deviation:.9f}")
        else:
            print("Nie znaleziono żadnych wartości clk_bias do obliczeń.")

    except FileNotFoundError:
        print(f"Błąd: Nie znaleziono pliku '{filename}'.")

if __name__ == "__main__":
    input_file = "/home/szymon/Downloads/GPS_JAMMING/GPS-JAMMING/GpsJammerApp/backend/helpers/wyniki/static/capture31.txt"
    if len(sys.argv) > 1:
        input_file = sys.argv[1]

    extract_and_calculate(input_file)