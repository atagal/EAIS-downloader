import os
import requests
import json
import urllib.parse
import threading
from tqdm import tqdm  # Importuojame tqdm biblioteką

# Konfigūracijos nustatymai
MAX_CONCURRENT_DOWNLOADS = 4  # Kiek failų atsisiųsti vienu metu
MAX_RETRY_COUNT = 10  # Maksimalus bandymų skaičius

DOWNLOAD_DIR = r"C:\Temp"  # Atsisiuntimo aplankas

def download_file(url, folder, filename, retry_count=0):
    """Atsisiunčia failą į nurodytą aplanką su nurodytu pavadinimu, su klaidų bandymu."""
    while retry_count < MAX_RETRY_COUNT:
        try:
            response = requests.get(url)
            if response.status_code != 200:
                print(f"Klaida atsisiunčiant failą {filename}. Bandymas {retry_count + 1}.")
                retry_count += 1
                continue
            
            file_path = os.path.join(folder, f"{filename}.jpg")
            with open(file_path, 'wb') as file:
                file.write(response.content)
            print(f"Atsisiųsta {filename} ({retry_count + 1} bandymas)")
            return True
        
        except requests.exceptions.RequestException as e:
            print(f"Klaida atsisiunčiant {filename}: {e}. Bandymas {retry_count + 1}.")
            retry_count += 1
    
    print(f"Nepavyko atsisiųsti {filename} po {MAX_RETRY_COUNT} bandymų.")
    return False

def process_url_or_number(input_value):
    """Apdoroja URL arba skaičių ir atlieka atsisiuntimus."""
    if input_value.startswith("https://"):
        # Ištraukia skaičių iš URL
        url_parts = input_value.split('/')
        number = url_parts[-1]
    else:
        number = input_value
    
    api_url = f"https://eais.archyvai.lt/repo-ext-api/inventories/{number}"
    
    json_data = fetch_json(api_url)
    if json_data is None:
        print("Klaida gavus JSON duomenis. Nutraukiame.")
        return

    if "artifact" not in json_data:
        print("Neišgauta reikalinga informacija apie artefaktą. Nutraukiame.")
        return
    
    folder_name = json_data["title"] + " " + json_data.get("chronRangeNotes", "")
    folder_path = os.path.join(DOWNLOAD_DIR, folder_name)
    os.makedirs(folder_path, exist_ok=True)

    artifact = json_data["artifact"]
    parts = artifact["content"]["parts"]

    total_files = len(parts)
    with tqdm(total=total_files, desc="Failų atsisiuntimas", ncols=100) as pbar:
        # Skirstome failus į grupes po MAX_CONCURRENT_DOWNLOADS ir siunčiame asinchroniškai
        for i in range(0, len(parts), MAX_CONCURRENT_DOWNLOADS):
            threads = []
            for part in parts[i:i+MAX_CONCURRENT_DOWNLOADS]:
                resource_uri = part["resource"]["uri"]
                encoded_uri = urllib.parse.quote(resource_uri, safe='')  # Užkoduojame URI

                file_url = f"https://eais.archyvai.lt/iiif/2/{encoded_uri}/full/max/0/default.jpg?download=true"
                
                # Atsisiųsti failą asinchroniškai
                thread = threading.Thread(target=download_file, args=(file_url, folder_path, part["name"]))
                threads.append(thread)
                thread.start()
            
            # Laukiame, kol visi failai bus atsisiųsti
            for thread in threads:
                thread.join()
                pbar.update(1)  # Atlieka progreso juostos atnaujinimą

def fetch_json(url):
    """Išsikviečia JSON duomenis iš pateikto URL ir tikrina, ar atsakymas sėkmingas."""
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Klaida: gauta {response.status_code} klaida užklausoje {url}")
        return None
    return response.json()

def main():
    input_value = input("Įveskite URL arba skaičių (pvz., 355857): ")
    process_url_or_number(input_value)

if __name__ == "__main__":
    main()
