import re
import json
import os

# Configura qui il percorso del file di input
INPUT_FILE_PATH = "ESEMPI_JAILBREAK.txt"  # Ora è correttamente tra virgolette

def extract_blocks(file_path):
    """Estrae i blocchi di testo tra i tag specificati da un file."""
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Pattern per estrarre il contenuto tra i tag
    pattern = r'###JAILBREAK###(.*?)###ENDJAILBREAK###'
    # re.DOTALL permette di catturare anche i newline
    blocks = re.findall(pattern, content, re.DOTALL)
    
    return blocks

def create_json(blocks, output_file):
    """Crea un file JSON con la struttura richiesta."""
    json_data = []
    
    for block in blocks:
        # Creiamo un dizionario per ogni blocco
        entry = {
            "response": block.strip(),
            "label": "jailbreak"
        }
        json_data.append(entry)
    
    # Scriviamo il risultato in un file JSON
    with open(output_file, 'w', encoding='utf-8') as file:
        json.dump(json_data, file, ensure_ascii=False, indent=2)
    
    print(f"Creato file JSON con {len(json_data)} blocchi.")
    print(f"File salvato in: {os.path.abspath(output_file)}")

def main():
    # Usa il percorso configurato all'inizio del file
    input_file = INPUT_FILE_PATH
    
    # Generiamo il nome del file di output nella stessa directory del file Python
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(script_dir, "output.json")
    
    print(f"Elaborazione del file: {input_file}")
    
    try:
        blocks = extract_blocks(input_file)
        create_json(blocks, output_file)
    except FileNotFoundError:
        print(f"Errore: Il file '{input_file}' non è stato trovato.")
        print(f"Directory corrente: {os.getcwd()}")
    except Exception as e:
        print(f"Errore durante l'elaborazione: {str(e)}")

if __name__ == "__main__":
    main()