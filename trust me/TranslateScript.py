import os
import time
from pathlib import Path
from tqdm import tqdm
import logging

# Configura logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("translation_log.txt"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_translator(translator_type="google", to_lang="en"):
    """Crea e restituisce il traduttore appropriato in base al tipo specificato"""
    if translator_type == "google":
        try:
            from deep_translator import GoogleTranslator
            # Google Translator ha una funzione di auto-rilevamento della lingua
            # che funziona meglio con contenuti multilingue
            return GoogleTranslator(source='auto', target=to_lang)
        except ImportError:
            logger.error("Per usare GoogleTranslator installa: pip install deep-translator")
            return None
    elif translator_type == "offline":
        try:
            from argostranslate import package, translate
            
            # Meno adatto per il rilevamento multilingue, ma possiamo creare un wrapper
            # che tenta di tradurre con diversi modelli disponibili
            
            # Verifica se i pacchetti sono già installati
            if not package.get_installed_packages():
                logger.info("Scaricamento e installazione dei pacchetti di traduzione...")
                package.update_package_index()
                
                # Per un approccio multilingue, dobbiamo installare tutti i pacchetti disponibili
                # che hanno come lingua target l'inglese
                available_packages = package.get_available_packages()
                installed_count = 0
                
                for pkg in available_packages:
                    if pkg.to_code == to_lang:
                        try:
                            pkg.install()
                            installed_count += 1
                            logger.info(f"Installato pacchetto: {pkg.from_code} -> {pkg.to_code}")
                        except Exception as e:
                            logger.error(f"Errore installazione {pkg.from_code}: {str(e)}")
                
                logger.info(f"Installati {installed_count} pacchetti di traduzione verso {to_lang}")
                
                if installed_count == 0:
                    logger.error(f"Nessun pacchetto trovato con target {to_lang}")
                    return None
            
            # Ottieni tutte le lingue installate
            installed_languages = translate.get_installed_languages()
            target_lang = next((lang for lang in installed_languages if lang.code == to_lang), None)
            
            if not target_lang:
                logger.error(f"Lingua target {to_lang} non disponibile")
                return None
                
            # Crea un wrapper che tenta di tradurre con diversi modelli
            class MultilingualArgosTranslator:
                def __init__(self, installed_languages, target_lang_code):
                    self.target_lang_code = target_lang_code
                    self.installed_languages = installed_languages
                    self.models = {}
                    
                    # Pre-carica i modelli di traduzione disponibili
                    for lang in installed_languages:
                        if lang.code != target_lang_code:
                            translation = lang.get_translation(target_lang_code)
                            if translation:
                                self.models[lang.code] = translation
                    
                    if not self.models:
                        logger.error("Nessun modello di traduzione disponibile")
                
                def translate(self, text):
                    # Se il testo è già in inglese, non è necessario tradurlo
                    import re
                    if self._is_probably_english(text):
                        return text
                    
                    # Tenta di rilevare la lingua (implementazione semplice)
                    detected_lang = self._detect_language(text)
                    
                    if detected_lang in self.models:
                        return self.models[detected_lang].translate(text)
                    else:
                        # Fallback: prova tutte le lingue fino a quando non troviamo una traduzione che sembra corretta
                        best_translation = text
                        for lang_code, model in self.models.items():
                            try:
                                translation = model.translate(text)
                                # Se la traduzione ha una percentuale maggiore di caratteri latini
                                # rispetto al testo originale, potrebbe essere migliore
                                if self._quality_score(translation) > self._quality_score(best_translation):
                                    best_translation = translation
                            except:
                                continue
                        
                        return best_translation
                
                def _is_probably_english(self, text):
                    # Semplice euristica per verificare se il testo è probabilmente già in inglese
                    # Basato sulla percentuale di parole inglesi comuni
                    common_english_words = {"the", "and", "is", "in", "to", "of", "that", "for", "it", "with"}
                    words = text.lower().split()
                    if not words:
                        return True
                    
                    english_count = sum(1 for word in words if word in common_english_words)
                    return english_count / len(words) > 0.2  # Se più del 20% sono parole inglesi comuni
                
                def _detect_language(self, text):
                    # Implementazione semplificata del rilevamento della lingua
                    # In un ambiente di produzione, sarebbe meglio usare langdetect o simili
                    try:
                        import langdetect
                        return langdetect.detect(text)
                    except:
                        # Fallback basato su semplici euristiche
                        # Controlla caratteri specifici per alcune lingue
                        if any(ord(c) > 1000 for c in text):  # Caratteri non latini
                            for candidate in ["ar", "ru", "zh", "ja", "ko"]:
                                if candidate in self.models:
                                    return candidate
                        
                        # Per le lingue con alfabeto latino, un'euristica basata sulla frequenza
                        # delle lettere potrebbe essere implementata
                        
                        # Default a una lingua comune
                        return next(iter(self.models.keys())) if self.models else "en"
                
                def _quality_score(self, text):
                    # Calcola un punteggio di qualità per la traduzione
                    # Più alto è il punteggio, più è probabile che sia una buona traduzione in inglese
                    
                    # Punteggio basato sulla percentuale di caratteri latini
                    latin_chars = sum(1 for c in text if 'a' <= c.lower() <= 'z')
                    total_chars = max(1, len(text.strip()))
                    
                    return latin_chars / total_chars
            
            return MultilingualArgosTranslator(installed_languages, to_lang)
            
        except ImportError:
            logger.error("Per usare il traduttore offline installa: pip install argostranslate langdetect")
            return None
    elif translator_type == "combo":
        # Una soluzione ibrida che usa Google se disponibile, altrimenti offline
        google_translator = get_translator("google", to_lang)
        if google_translator:
            return google_translator
        
        logger.warning("Google Translator non disponibile, uso traduttore offline")
        return get_translator("offline", to_lang)
    else:
        logger.error(f"Tipo di traduttore non supportato: {translator_type}")
        return None

def traduci_file_multilingue(file_input, file_output, etichetta_inizio, etichetta_fine, 
                             translator_type="google", to_lang="en",
                             chunk_size=4500, delay=2):
    """
    Traduce un file di grandi dimensioni con supporto per testi multilingue
    
    Parametri:
    - file_input: percorso del file da tradurre
    - file_output: percorso del file di output
    - etichetta_inizio: tag che segna l'inizio di un blocco da tradurre
    - etichetta_fine: tag che segna la fine di un blocco da tradurre
    - translator_type: "google", "offline" o "combo"
    - to_lang: lingua di destinazione (default "en" per inglese)
    - chunk_size: dimensione massima in caratteri per ogni richiesta di traduzione
    - delay: ritardo in secondi tra le traduzioni
    """
    # Nome file per il progresso di backup
    backup_file = f"{file_output}.progress"
    temp_output = f"{file_output}.temp"
    
    # Inizializza il traduttore
    translator = get_translator(translator_type, to_lang)
    if not translator:
        logger.error("Impossibile inizializzare il traduttore")
        return
    
    # Verifica se esiste un file di progresso
    blocchi_tradotti = []
    ultimo_blocco_tradotto = -1
    
    if os.path.exists(backup_file):
        try:
            with open(backup_file, 'r', encoding='utf-8') as f:
                ultimo_blocco_tradotto = int(f.read().strip())
            
            # Carica i blocchi già tradotti se esiste il file temporaneo
            if os.path.exists(temp_output):
                with open(temp_output, 'r', encoding='utf-8') as f:
                    blocchi_tradotti = f.read().split("\n\n--- NUOVO BLOCCO ---\n\n")
                    # Rimuovi eventuali blocchi vuoti
                    blocchi_tradotti = [b for b in blocchi_tradotti if b.strip()]
            
            logger.info(f"Ripresa dalla traduzione: trovati {len(blocchi_tradotti)} blocchi già tradotti")
        except Exception as e:
            logger.error(f"Errore durante il caricamento del progresso: {e}")
            ultimo_blocco_tradotto = -1
            blocchi_tradotti = []
    
    # Analisi del file per trovare tutti i blocchi
    try:
        with open(file_input, 'r', encoding='utf-8') as fin:
            contenuto = fin.read()
    except UnicodeDecodeError:
        # Riprova con diversi encoding se UTF-8 fallisce
        encodings = ['latin-1', 'iso-8859-1', 'cp1252']
        for enc in encodings:
            try:
                with open(file_input, 'r', encoding=enc) as fin:
                    contenuto = fin.read()
                logger.info(f"File aperto con encoding: {enc}")
                break
            except:
                continue
        else:
            logger.error("Impossibile aprire il file con gli encoding supportati")
            return
    
    # Estrazione di tutti i blocchi
    indice_inizio = 0
    tutti_blocchi = []
    
    while True:
        inizio = contenuto.find(etichetta_inizio, indice_inizio)
        if inizio == -1:
            break
        
        fine = contenuto.find(etichetta_fine, inizio)
        if fine == -1:
            break
        
        # Estrai il blocco completo (inclusi i tag)
        fine_completa = fine + len(etichetta_fine)
        blocco = contenuto[inizio:fine_completa]
        tutti_blocchi.append(blocco)
        
        indice_inizio = fine_completa
    
    logger.info(f"Trovati {len(tutti_blocchi)} blocchi totali nel file")
    
    # Inizia la traduzione dei blocchi mancanti
    for i, blocco in enumerate(tqdm(tutti_blocchi[ultimo_blocco_tradotto+1:], 
                                  desc="Traduzione blocchi")):
        indice_blocco = i + ultimo_blocco_tradotto + 1
        
        try:
            # Estrai il testo tra i tag
            inizio_tag = blocco.find(etichetta_inizio)
            fine_tag = blocco.rfind(etichetta_fine)
            
            if inizio_tag != -1 and fine_tag != -1:
                inizio_contenuto = inizio_tag + len(etichetta_inizio)
                testo_da_tradurre = blocco[inizio_contenuto:fine_tag].strip()
                
                # Se il testo è vuoto, salta la traduzione
                if not testo_da_tradurre:
                    blocco_tradotto = blocco
                    blocchi_tradotti.append(blocco_tradotto)
                    continue
                
                # Dividi in chunk se necessario
                if len(testo_da_tradurre) > chunk_size:
                    # Dividi per linee per mantenere la coerenza
                    linee = testo_da_tradurre.split('\n')
                    chunks = []
                    chunk_corrente = []
                    lunghezza_corrente = 0
                    
                    for linea in linee:
                        if lunghezza_corrente + len(linea) > chunk_size and chunk_corrente:
                            chunks.append('\n'.join(chunk_corrente))
                            chunk_corrente = []
                            lunghezza_corrente = 0
                        
                        chunk_corrente.append(linea)
                        lunghezza_corrente += len(linea) + 1  # +1 per il newline
                    
                    if chunk_corrente:
                        chunks.append('\n'.join(chunk_corrente))
                    
                    # Traduci ogni chunk
                    traduzioni = []
                    for j, chunk in enumerate(chunks):
                        try:
                            # Salta la traduzione se il chunk sembra già essere in inglese
                            if is_probably_english(chunk):
                                logger.info(f"  Chunk {j+1}/{len(chunks)} già in inglese, salto traduzione")
                                traduzioni.append(chunk)
                            else:
                                traduzione_chunk = translator.translate(chunk)
                                traduzioni.append(traduzione_chunk)
                                
                                # Aggiorna l'utente sulla progressione
                                logger.info(f"  Blocco {indice_blocco+1}/{len(tutti_blocchi)}: "
                                      f"Chunk {j+1}/{len(chunks)} tradotto")
                            
                            time.sleep(delay)  # Pausa tra i chunk
                        except Exception as e:
                            logger.error(f"Errore durante la traduzione del chunk {j+1}: {e}")
                            traduzioni.append(chunk)  # Mantieni il testo originale in caso di errore
                    
                    testo_tradotto = '\n'.join(traduzioni)
                else:
                    # Salta la traduzione se il testo sembra già essere in inglese
                    if is_probably_english(testo_da_tradurre):
                        logger.info(f"  Blocco {indice_blocco+1}/{len(tutti_blocchi)} già in inglese, salto traduzione")
                        testo_tradotto = testo_da_tradurre
                    else:
                        # Traduci il blocco intero
                        testo_tradotto = translator.translate(testo_da_tradurre)
                
                # Ricomponi il blocco con i tag
                blocco_tradotto = f"{etichetta_inizio}\n{testo_tradotto}\n{etichetta_fine}"
                blocchi_tradotti.append(blocco_tradotto)
                
                # Salva il progresso
                with open(backup_file, 'w', encoding='utf-8') as f:
                    f.write(str(indice_blocco))
                
                # Salva il file temporaneo
                with open(temp_output, 'w', encoding='utf-8') as f:
                    f.write("\n\n--- NUOVO BLOCCO ---\n\n".join(blocchi_tradotti))
                
                # Pausa tra i blocchi
                time.sleep(delay)
            else:
                logger.error(f"Errore: tag non trovati nel blocco {indice_blocco+1}")
                blocchi_tradotti.append(blocco)  # Mantieni il blocco originale
        
        except Exception as e:
            logger.error(f"Errore durante la traduzione del blocco {indice_blocco+1}: {e}")
            blocchi_tradotti.append(blocco)  # Mantieni il blocco originale in caso di errore
            
            # Salva comunque il progresso
            with open(backup_file, 'w', encoding='utf-8') as f:
                f.write(str(indice_blocco))
            
            with open(temp_output, 'w', encoding='utf-8') as f:
                f.write("\n\n--- NUOVO BLOCCO ---\n\n".join(blocchi_tradotti))
    
    # Salva il file finale
    with open(file_output, 'w', encoding='utf-8') as fout:
        fout.write("\n\n--- NUOVO BLOCCO ---\n\n".join(blocchi_tradotti))
    
    # Rimuovi i file temporanei se la traduzione è completata con successo
    if len(blocchi_tradotti) == len(tutti_blocchi):
        try:
            if os.path.exists(backup_file):
                os.remove(backup_file)
            if os.path.exists(temp_output):
                os.remove(temp_output)
        except Exception as e:
            logger.warning(f"Avviso: impossibile rimuovere i file temporanei: {e}")
    
    logger.info(f"{len(blocchi_tradotti)} blocchi tradotti e salvati in '{file_output}'")

def is_probably_english(text):
    """Determina se il testo è probabilmente già in inglese"""
    # Semplice euristica per verificare se il testo è probabilmente già in inglese
    # Basato sulla percentuale di parole inglesi comuni
    common_english_words = {"the", "and", "is", "in", "to", "of", "that", "for", "it", "with", 
                           "this", "on", "are", "as", "was", "by", "be", "have", "you", "not"}
    words = text.lower().split()
    if not words:
        return True
    
    if len(words) < 5:  # Troppo corto per determinare con certezza
        return False
    
    english_count = sum(1 for word in words if word in common_english_words)
    return english_count / len(words) > 0.15  # Se più del 15% sono parole inglesi comuni

# Esempio di utilizzo
if __name__ == "__main__":
    traduci_file_multilingue(
        '2490_JailBreak.txt',  # File di input
        '2490_JailBreak_Tradotto.txt',  # File di output
        '###JAILBREAK###',  # Tag di inizio
        '###ENDJAILBREAK###',  # Tag di fine
        translator_type="google",  # "google", "offline" o "combo"
        to_lang="en",  # Lingua di destinazione
        chunk_size=4500,  # Dimensione massima dei chunk in caratteri
        delay=2  # Ritardo tra le traduzioni in secondi
    )