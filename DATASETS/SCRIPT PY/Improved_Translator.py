import os
import time
import json
from pathlib import Path
from tqdm import tqdm
import logging
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("json_translation_log.txt"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_translator(translator_type="google", to_lang="en"):
    """Creates and returns the appropriate translator based on the specified type"""
    if translator_type == "google":
        try:
            from deep_translator import GoogleTranslator
            # Google Translator has auto-detection which works better with multilingual content
            return GoogleTranslator(source='auto', target=to_lang)
        except ImportError:
            logger.error("To use GoogleTranslator install: pip install deep-translator")
            return None
    elif translator_type == "offline":
        try:
            from argostranslate import package, translate
            
            # Check if packages are already installed
            if not package.get_installed_packages():
                logger.info("Downloading and installing translation packages...")
                package.update_package_index()
                
                # For a multilingual approach, we need to install all available packages
                # that have English as the target language
                available_packages = package.get_available_packages()
                installed_count = 0
                
                for pkg in available_packages:
                    if pkg.to_code == to_lang:
                        try:
                            pkg.install()
                            installed_count += 1
                            logger.info(f"Installed package: {pkg.from_code} -> {pkg.to_code}")
                        except Exception as e:
                            logger.error(f"Error installing {pkg.from_code}: {str(e)}")
                
                logger.info(f"Installed {installed_count} translation packages to {to_lang}")
                
                if installed_count == 0:
                    logger.error(f"No packages found with target {to_lang}")
                    return None
            
            # Get all installed languages
            installed_languages = translate.get_installed_languages()
            target_lang = next((lang for lang in installed_languages if lang.code == to_lang), None)
            
            if not target_lang:
                logger.error(f"Target language {to_lang} not available")
                return None
                
            # Create a wrapper that attempts to translate with different models
            class MultilingualArgosTranslator:
                def __init__(self, installed_languages, target_lang_code):
                    self.target_lang_code = target_lang_code
                    self.installed_languages = installed_languages
                    self.models = {}
                    
                    # Pre-load available translation models
                    for lang in installed_languages:
                        if lang.code != target_lang_code:
                            translation = lang.get_translation(target_lang_code)
                            if translation:
                                self.models[lang.code] = translation
                    
                    if not self.models:
                        logger.error("No translation models available")
                
                def translate(self, text):
                    # If text is already in English, no need to translate
                    if self._is_probably_english(text):
                        return text
                    
                    # Try to detect the language (simple implementation)
                    detected_lang = self._detect_language(text)
                    
                    if detected_lang in self.models:
                        return self.models[detected_lang].translate(text)
                    else:
                        # Fallback: try all languages until we find a translation that looks correct
                        best_translation = text
                        for lang_code, model in self.models.items():
                            try:
                                translation = model.translate(text)
                                # If the translation has a higher percentage of Latin characters
                                # than the original text, it might be better
                                if self._quality_score(translation) > self._quality_score(best_translation):
                                    best_translation = translation
                            except:
                                continue
                        
                        return best_translation
                
                def _is_probably_english(self, text):
                    # Simple heuristic to check if the text is probably already in English
                    # Based on the percentage of common English words
                    common_english_words = {"the", "and", "is", "in", "to", "of", "that", "for", "it", "with"}
                    words = text.lower().split()
                    if not words:
                        return True
                    
                    english_count = sum(1 for word in words if word in common_english_words)
                    return english_count / len(words) > 0.2  # If more than 20% are common English words
                
                def _detect_language(self, text):
                    # Simplified implementation of language detection
                    # In a production environment, it would be better to use langdetect or similar
                    try:
                        import langdetect
                        return langdetect.detect(text)
                    except:
                        # Fallback based on simple heuristics
                        # Check specific characters for some languages
                        if any(ord(c) > 1000 for c in text):  # Non-Latin characters
                            for candidate in ["ar", "ru", "zh", "ja", "ko"]:
                                if candidate in self.models:
                                    return candidate
                        
                        # Default to a common language
                        return next(iter(self.models.keys())) if self.models else "en"
                
                def _quality_score(self, text):
                    # Calculate a quality score for the translation
                    # Higher score means it's more likely to be a good translation in English
                    
                    # Score based on percentage of Latin characters
                    latin_chars = sum(1 for c in text if 'a' <= c.lower() <= 'z')
                    total_chars = max(1, len(text.strip()))
                    
                    return latin_chars / total_chars
            
            return MultilingualArgosTranslator(installed_languages, to_lang)
            
        except ImportError:
            logger.error("To use the offline translator install: pip install argostranslate langdetect")
            return None
    elif translator_type == "combo":
        # A hybrid solution that uses Google if available, otherwise offline
        google_translator = get_translator("google", to_lang)
        if google_translator:
            return google_translator
        
        logger.warning("Google Translator not available, using offline translator")
        return get_translator("offline", to_lang)
    else:
        logger.error(f"Unsupported translator type: {translator_type}")
        return None

def segment_text(text, threshold=0.2):
    """
    Split text into English and non-English segments for more efficient translation
    Returns a list of (text, is_english) tuples
    """
    if not text:
        return []
    
    # Simple sentence splitting
    sentences = re.split(r'([.!?]\s+)', text)
    result = []
    current_segment = ""
    current_is_english = is_probably_english(sentences[0] if sentences else "")
    
    for i in range(0, len(sentences), 2):
        sentence = sentences[i]
        ending = sentences[i+1] if i+1 < len(sentences) else ""
        full_sentence = sentence + ending
        
        sentence_is_english = is_probably_english(full_sentence)
        
        # If we have a change in language or segment is getting large
        if sentence_is_english != current_is_english or len(current_segment) > 4000:
            if current_segment:
                result.append((current_segment, current_is_english))
            current_segment = full_sentence
            current_is_english = sentence_is_english
        else:
            current_segment += full_sentence
    
    # Add the last segment
    if current_segment:
        result.append((current_segment, current_is_english))
    
    return result

def is_probably_english(text):
    """Determines if the text is probably already in English"""
    # Simple heuristic to check if the text is probably already in English
    # Based on the percentage of common English words and character frequency
    common_english_words = {"the", "and", "is", "in", "to", "of", "that", "for", "it", "with", 
                           "this", "on", "are", "as", "was", "by", "be", "have", "you", "not"}
    
    # If text has significant amount of non-Latin characters, it's probably not English
    non_latin_count = sum(1 for c in text if ord(c) > 127)
    if non_latin_count / max(1, len(text)) > 0.2:
        return False
    
    words = text.lower().split()
    if not words:
        return True
    
    if len(words) < 5:  # Too short to determine with certainty
        # Check if it looks like English based on character frequency
        english_chars = sum(1 for c in text.lower() if 'a' <= c <= 'z')
        return english_chars / max(1, len(text)) > 0.6
    
    english_count = sum(1 for word in words if word in common_english_words)
    return english_count / len(words) > 0.15  # If more than 15% are common English words

def translate_json_file(input_file, output_file, translator_type="google", to_lang="en", 
                         chunk_size=4500, delay=2, fields_to_translate=None):
    """
    Translates a JSON file containing multilingual text fields to English
    
    Parameters:
    - input_file: path to the input JSON file
    - output_file: path to the output JSON file
    - translator_type: "google", "offline" or "combo"
    - to_lang: target language (default "en" for English)
    - chunk_size: maximum size in characters for each translation request
    - delay: delay in seconds between translations
    - fields_to_translate: list of field names to translate (default: ["response"])
    """
    # Default field to translate
    if fields_to_translate is None:
        fields_to_translate = ["response"]
    
    # Backup file names for progress
    backup_file = f"{output_file}.progress"
    temp_output = f"{output_file}.temp"
    
    # Initialize the translator
    translator = get_translator(translator_type, to_lang)
    if not translator:
        logger.error("Failed to initialize translator")
        return
    
    # Check if a progress file exists
    last_translated_idx = -1
    translated_data = []
    
    if os.path.exists(backup_file):
        try:
            with open(backup_file, 'r', encoding='utf-8') as f:
                last_translated_idx = int(f.read().strip())
            
            # Load already translated data if temp file exists
            if os.path.exists(temp_output):
                with open(temp_output, 'r', encoding='utf-8') as f:
                    translated_data = json.load(f)
            
            logger.info(f"Resuming translation: found {len(translated_data)} already translated items")
        except Exception as e:
            logger.error(f"Error loading progress: {e}")
            last_translated_idx = -1
            translated_data = []
    
    # Load the JSON file
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            # Check if file starts as an array or if items are comma-separated objects
            content = f.read().strip()
            if content.startswith('['):
                data = json.loads(content)
            else:
                # Handle case where each line might be a JSON object
                data = []
                try:
                    # Try to parse the file as JSON Lines
                    lines = content.split('\n')
                    for line in lines:
                        line = line.strip()
                        if line and not line.isspace():
                            if line.endswith(','):
                                line = line[:-1]
                            try:
                                obj = json.loads(line)
                                data.append(obj)
                            except json.JSONDecodeError:
                                # Skip invalid lines
                                logger.warning(f"Skipping invalid JSON line: {line[:50]}...")
                except Exception as e:
                    logger.error(f"Error parsing JSON Lines: {e}")
                    # Try wrapping with brackets and parsing as array
                    try:
                        data = json.loads(f"[{content}]")
                    except:
                        logger.error("Failed to parse JSON file in any format")
                        return
        
        logger.info(f"Loaded {len(data)} JSON items")
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        return
    except UnicodeDecodeError:
        # Try with different encodings if UTF-8 fails
        encodings = ['latin-1', 'iso-8859-1', 'cp1252']
        for enc in encodings:
            try:
                with open(input_file, 'r', encoding=enc) as f:
                    data = json.loads(f.read())
                logger.info(f"File opened with encoding: {enc}")
                break
            except:
                continue
        else:
            logger.error("Unable to open file with supported encodings")
            return
    
    # If we're starting fresh, initialize translated_data
    if last_translated_idx == -1:
        translated_data = []
    
    # Start translating items
    for i, item in enumerate(tqdm(data[last_translated_idx+1:], 
                                desc="Translating JSON items")):
        idx = i + last_translated_idx + 1
        
        try:
            # Create a copy of the item
            translated_item = item.copy()
            
            # Translate each specified field
            for field in fields_to_translate:
                if field in item and item[field]:
                    text = item[field]
                    
                    # Skip if already in English
                    if is_probably_english(text):
                        logger.info(f"  Item {idx+1}/{len(data)}: Field '{field}' already in English, skipping")
                        translated_item[field] = text
                        continue
                    
                    # Segment the text to handle mixed language content
                    segments = segment_text(text)
                    translated_segments = []
                    
                    for segment_text, is_english in segments:
                        if is_english:
                            # Keep English segments as is
                            translated_segments.append(segment_text)
                        else:
                            # Translate non-English segments
                            if len(segment_text) > chunk_size:
                                # Break into smaller chunks if needed
                                chunks = []
                                start = 0
                                while start < len(segment_text):
                                    # Try to break at sentence boundaries
                                    end = min(start + chunk_size, len(segment_text))
                                    if end < len(segment_text):
                                        # Look for sentence ending
                                        sentence_end = max(segment_text.rfind('. ', start, end),
                                                        segment_text.rfind('! ', start, end),
                                                        segment_text.rfind('? ', start, end))
                                        if sentence_end > start:
                                            end = sentence_end + 2  # Include the punctuation and space
                                    
                                    chunks.append(segment_text[start:end])
                                    start = end
                                
                                # Translate each chunk
                                translated_chunks = []
                                for j, chunk in enumerate(chunks):
                                    try:
                                        translated_chunk = translator.translate(chunk)
                                        translated_chunks.append(translated_chunk)
                                        logger.info(f"  Item {idx+1}/{len(data)}: Chunk {j+1}/{len(chunks)} translated")
                                        time.sleep(delay)
                                    except Exception as e:
                                        logger.error(f"Error translating chunk {j+1}: {e}")
                                        translated_chunks.append(chunk)  # Keep original on error
                                
                                translated_segments.append(''.join(translated_chunks))
                            else:
                                # Translate the segment
                                try:
                                    translated_segment = translator.translate(segment_text)
                                    translated_segments.append(translated_segment)
                                    time.sleep(delay)
                                except Exception as e:
                                    logger.error(f"Error translating segment: {e}")
                                    translated_segments.append(segment_text)  # Keep original on error
                    
                    # Join all segments back together
                    translated_item[field] = ''.join(translated_segments)
            
            # Add to translated data
            translated_data.append(translated_item)
            
            # Save progress
            with open(backup_file, 'w', encoding='utf-8') as f:
                f.write(str(idx))
            
            # Save temporary output
            with open(temp_output, 'w', encoding='utf-8') as f:
                json.dump(translated_data, f, ensure_ascii=False, indent=2)
            
        except Exception as e:
            logger.error(f"Error processing item {idx+1}: {e}")
            translated_data.append(item)  # Keep original item on error
            
            # Save progress anyway
            with open(backup_file, 'w', encoding='utf-8') as f:
                f.write(str(idx))
            
            with open(temp_output, 'w', encoding='utf-8') as f:
                json.dump(translated_data, f, ensure_ascii=False, indent=2)
    
    # Save the final file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(translated_data, f, ensure_ascii=False, indent=2)
    
    # Remove temporary files if translation completed successfully
    if len(translated_data) == len(data):
        try:
            if os.path.exists(backup_file):
                os.remove(backup_file)
            if os.path.exists(temp_output):
                os.remove(temp_output)
        except Exception as e:
            logger.warning(f"Warning: unable to remove temporary files: {e}")
    
    logger.info(f"{len(translated_data)} items translated and saved to '{output_file}'")

# Example usage
if __name__ == "__main__":
    translate_json_file(
        'merged_responses.json', # Input file
        'translated_merged_responses.json',  # Output file
        translator_type="google",  # "google", "offline" or "combo"
        to_lang="en",  # Target language
        chunk_size=4500,  # Maximum chunk size in characters
        delay=2,  # Delay between translations in seconds
        fields_to_translate=["response"]  # Fields to translate in each JSON object
    )