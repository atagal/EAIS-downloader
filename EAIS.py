import os
import requests
import json
import urllib.parse
import threading
import re
import sys
import time
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

def sanitize_folder_name(folder_name):
    """Pašalina neleistinus simbolius iš aplanko pavadinimo."""
    # Leistinų simbolių sąrašas: alphanumeric, space, ir kai kurie kiti simboliai
    return re.sub(r'[\\/*?:"<>|]', '_', folder_name)

def load_config(config_file):
    """Perskaito konfigūracijos failą ir grąžina reikšmes kaip žodyną."""
    config = {}
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            for line in f:
                line = line.strip()
                if '=' in line:
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip()
    return config

# Nustatykite konfigūracijos failą
config_file = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), 'eais.conf')

# Bandome perskaityti konfigūraciją iš failo, jei jis yra
config = load_config(config_file)

# Jei konfigūracijos failas nerastas arba jis tuščias, naudojame numatytas reikšmes
MAX_CONCURRENT_DOWNLOADS = int(config.get('MAX_CONCURRENT_DOWNLOADS', 4))
MAX_RETRY_COUNT = int(config.get('MAX_RETRY_COUNT', 10))

# Numatytas atsisiuntimo katalogas
DOWNLOAD_DIR = config.get('DOWNLOAD_DIR', r"C:\Temp")  # Jei nėra, naudojame numatytą katalogą

# Jei DOWNLOAD_DIR nėra nurodytas, nustatyti jį į direktoriją, kurioje yra skriptas arba .exe failas
if 'DOWNLOAD_DIR' not in globals():
    DOWNLOAD_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))  # Nustato direktoriją, kurioje randasi skriptas arba exe

# Sukuriame "EAIS" aplanką pagal nurodytą DOWNLOAD_DIR
DOWNLOAD_DIR = os.path.join(DOWNLOAD_DIR, "EAIS")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)  # Sukuria aplanką, jei jo dar nėra

print(f"Failai bus atsisiųsti į: {DOWNLOAD_DIR}")

def download_file(url, folder, filename):
    """Atsisiunčia failą ir prideda .tmp, pašalina jį tik po sėkmingo atsisiuntimo."""
    tmp_path = os.path.join(folder, f"{filename}.jpg.tmp")
    final_path = os.path.join(folder, f"{filename}.jpg")

    for retry in range(MAX_RETRY_COUNT):  # Bandymai vykdomi per MAX_RETRY_COUNT kartų
        try:
            response = requests.get(url, timeout=30)  # Padidinta timeout reikšmė (30 sek.)
            if response.status_code != 200:
                print(f"⚠️ Klaida ({response.status_code}) atsisiunčiant {filename}, bandymas {retry + 1}")
                time.sleep(5)  # Pauzė tarp bandymų
                continue  # Tęsti kitą bandymą

            # Jei atsakymas geras, įrašome failą
            with open(tmp_path, 'wb') as file:
                file.write(response.content)

            os.rename(tmp_path, final_path)  # Pervadinti failą tik jei sėkmingai atsisiųsta
            return filename  # Sėkmingai atsisiųsta

        except requests.exceptions.RequestException as e:
            print(f"⚠️ Klaida atsisiunčiant {filename}: {e}. Bandymas {retry + 1}")
            time.sleep(5)  # Pauzė tarp bandymų

    # Jei visi bandymai nepavyko
    print(f"❌ Nepavyko atsisiųsti {filename} net po {MAX_RETRY_COUNT} bandymų.")
    return None  # Jei nepavyko atsisiųsti po visų bandymų


def process_url_or_number(input_value):
    """Apdoroja URL arba skaičių ir atlieka atsisiuntimus."""
    number = extract_number(input_value)
    if not number:
        return

    api_url = f"https://eais.archyvai.lt/repo-ext-api/inventories/{number}"
    json_data = fetch_json(api_url)

    # Jei json_data nėra None, apdorojame reikšmes
    if json_data:
        # Gauti datas
        chron_range_from = json_data.get("chronRangeFrom", "").strip()
        chron_range_to = json_data.get("chronRangeTo", "").strip()

        # Atlikti triminimą ir palikti tik metus
        def trim_to_year(date_str):
            """Pašalina mėnesius ir dienas, paliekant tik metus."""
            if date_str:
                return date_str.split('-')[0]  # Pašalina mėnesius ir dienas, grąžina tik metus
            return ""

        # Jei datos skiriasi, sujungti su brūkšniu
        if chron_range_from and chron_range_to:
            # Trimintume datas ir sujungsime su brūkšniu
            chron_range_from = trim_to_year(chron_range_from)
            chron_range_to = trim_to_year(chron_range_to)

            if chron_range_from == chron_range_to:
                chron_range_notes = chron_range_from
            else:
                chron_range_notes = f"{chron_range_from}--{chron_range_to}"
        else:
            chron_range_notes = trim_to_year(chron_range_from) or trim_to_year(chron_range_to)

        # Aplanko pavadinimas
        folder_name = json_data["title"] + " " + chron_range_notes
        
        # Pridedame papildomą logiką priklausomai nuo frazių pavadinime
        if "gimim" in json_data["title"].lower():
            folder_name += " g"
        elif "mirt" in json_data["title"].lower():
            folder_name += " m"
        elif "sant" in json_data["title"].lower():
            folder_name += " s"

        folder_name = sanitize_folder_name(folder_name)  # Pašaliname neleistinus simbolius iš aplanko pavadinimo

        # Pridedame number prie folder_name
        folder_name = f"{number}_{folder_name}"
        
        # Sanitizuojame aplanko pavadinimą
        folder_name = sanitize_folder_name(folder_name)

        final_folder_path = os.path.join(DOWNLOAD_DIR, folder_name)  # Galutinis aplanko pavadinimas

        # Patikriname, ar aplankas jau egzistuoja
        if os.path.exists(final_folder_path):
            print(f"❌ Aplankas yra: {final_folder_path}")
            return  # Jei aplankas egzistuoja, praleidžiame šį atsisiuntimą

        tmp_folder_path = os.path.join(DOWNLOAD_DIR, folder_name + "~tmp")  # Laikinas aplanko pavadinimas
        os.makedirs(tmp_folder_path, exist_ok=True)  # Sukuriame aplanką

        parts = json_data.get("artifact", {}).get("content", {}).get("parts", [])

        if not parts:
            print(f"❌ Nėra dalių atsisiųsti {final_folder_path}")
            return

        # Naudojame ThreadPoolExecutor atsisiuntimui
        with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_DOWNLOADS) as executor, tqdm(total=len(parts), desc=f"📥 Atsisiunčiamas {number}", ncols=100, position=0, dynamic_ncols=True) as pbar:
            future_to_part = {}
            for part in parts:
                resource_uri = urllib.parse.quote(part["resource"]["uri"], safe='')  # Užkoduojame URI
                file_url = f"https://eais.archyvai.lt/iiif/2/{resource_uri}/full/max/0/default.jpg?download=true"
                future = executor.submit(download_file, file_url, tmp_folder_path, part["name"])
                future_to_part[future] = part["name"]

            for future in as_completed(future_to_part):
                filename = future_to_part[future]
                try:
                    result = future.result()
                    if result:
                        pbar.update(1)  # Atnaujiname progresą tik kai failas atsisiunčiamas
                    else:
                        print(f"❌ Nepavyko atsisiųsti {filename}")
                except Exception as e:
                    print(f"❌ Klaida su {filename}: {e}")

        # Jei visi failai sėkmingai atsisiųsti, pervadiname aplanką
        if all(os.path.exists(os.path.join(tmp_folder_path, f"{part['name']}.jpg")) for part in parts):
            os.rename(tmp_folder_path, final_folder_path)
            print(f"✅ Aplankas pervadintas į: {final_folder_path}")
        else:
            print(f"❌ Kai kurie failai nebuvo atsisiųsti, aplankas paliekamas laikinas: {tmp_folder_path}")

def fetch_json(url):
    """Išsikviečia JSON duomenis iš pateikto URL ir patikrina atsakymą."""
    try:
        response = requests.get(url, timeout=10)  # Timeout apsauga
        return response.json() if response.status_code == 200 else None
    except requests.exceptions.RequestException:
        return None

def extract_number(input_string):
    """Ištraukia pirmą skaičių iš pateikto teksto."""
    match = re.search(r'\d+', input_string)
    return match.group(0) if match else None

def get_input():
    """Leidžia vartotojui įvesti kelias nuorodas arba skaičius su viena Enter ir naujos eilutės su 'return'."""
    if len(sys.argv) > 1:
        # 1. Įvestis kaip argumentai (komandinė eilutė)
        return sys.argv[1:]

    print("Įklijuokite EAIS nuorodas (spauskite Enter, norėdami patvirtinti):")

    lines = []
    while True:
        line = input().strip()
        if line == "":  # Jei paspaudžiamas Enter su tuščia eilute, baigiame
            break
        lines.append(line)

    # Sujungiame visus įrašytus duomenis į vieną eilutę (kad įrašytume nuorodas su new line)
    return " ".join(lines)

def main():
    while True:  # Sukuriame begalinį ciklą, kad vartotojas galėtų įvesti daugiau nuorodų
        input_text = get_input()
        numbers = re.findall(r'\d+', input_text)
        
        if numbers:
            print(f"🔍 Rasti EAIS identifikatoriai: {numbers}")
            for number in numbers:
                process_url_or_number(number)
        else:
            print("❌ Nerasta jokių EAIS identifikatorių!")

        # Paprašykite vartotojo, ar nori įvesti naują nuorodą ar užbaigti programą
        continue_input = input("Ar norite įvesti kitą nuorodą? Paspauskite Enter, kad tęstumėte, arba įveskite 'exit', kad uždarytumėte: ").strip().lower()

        if continue_input == 'exit':
            break  # Nutraukiame ciklą, jei vartotojas įveda 'exit'

if __name__ == "__main__":
    main()
