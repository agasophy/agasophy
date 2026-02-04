#!/usr/bin/env python3
"""
Fetch etymology data for dictionary entries from Wiktionary.

Usage:
    python etymology.py WORD              # Process a single word
    python etymology.py --all             # Process all entries missing etymology
    python etymology.py --all --force     # Regenerate all entries

Requirements:
    pip install requests pyyaml
"""

import argparse
import re
import sys
import time
from pathlib import Path

try:
    import requests
    import yaml
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install requests pyyaml")
    sys.exit(1)

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DICTIONARY_DIR = PROJECT_ROOT / "_dictionary"

# Wiktionary API endpoint (French)
WIKTIONARY_API = "https://fr.wiktionary.org/api/rest_v1/page/definition/{word}"


def parse_front_matter(content: str) -> tuple[dict, str]:
    """Parse YAML front matter from markdown content."""
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", content, re.DOTALL)
    if not match:
        return {}, content
    front_matter = yaml.safe_load(match.group(1)) or {}
    body = match.group(2)
    return front_matter, body


def serialize_front_matter(front_matter: dict, body: str) -> str:
    """Serialize front matter and body back to markdown."""
    yaml_str = yaml.dump(front_matter, default_flow_style=False, allow_unicode=True, sort_keys=False)
    return f"---\n{yaml_str}---\n{body}"


def clean_html(text: str) -> str:
    """Remove HTML tags and clean up text."""
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Decode common HTML entities
    text = text.replace('&amp;', '&')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&quot;', '"')
    text = text.replace('&#39;', "'")
    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def format_etymology(raw_etymology: str) -> str:
    """Format etymology text, converting key terms to markdown italic."""
    text = clean_html(raw_etymology)

    # Wrap language names and foreign words in italics
    # Common patterns: "From Latin word", "from Greek phyllon"
    languages = ['Latin', 'Greek', 'French', 'Old English', 'Middle English',
                 'Old French', 'Proto-Germanic', 'German', 'Italian', 'Spanish',
                 'Sanskrit', 'Arabic', 'Hebrew', 'Old Norse', 'Dutch']

    for lang in languages:
        # Italicize the language name when followed by a word
        text = re.sub(
            rf'\b({lang})\s+([a-zA-Z]+)\b',
            rf'*\1* *\2*',
            text
        )

    return text


def fetch_etymology_wiktionary(word: str) -> str | None:
    """Fetch etymology from Wiktionary REST API."""
    try:
        headers = {
            'User-Agent': 'AgasophyBot/1.0 (etymology lookup for dictionary project)'
        }
        response = requests.get(
            WIKTIONARY_API.format(word=word.lower()),
            headers=headers,
            timeout=10
        )

        if response.status_code == 404:
            print(f"  Word '{word}' not found in Wiktionary")
            return None

        response.raise_for_status()
        data = response.json()

        # Look for French definitions
        if 'fr' not in data:
            print(f"  No French entry for '{word}'")
            return None

        for entry in data['fr']:
            # Check for etymology in the entry
            if 'etymology' in entry and entry['etymology']:
                return format_etymology(entry['etymology'])

        return None

    except requests.RequestException as e:
        print(f"  API error for '{word}': {e}")
        return None
    except (KeyError, ValueError) as e:
        print(f"  Parse error for '{word}': {e}")
        return None


def parse_wiki_template(template: str) -> str:
    """Parse a wiki template and extract meaningful text."""
    # Remove {{ and }}
    template = template.strip('{}')
    parts = template.split('|')

    if not parts:
        return ''

    template_name = parts[0].strip()

    # Language code mappings (French names for French Wiktionary)
    lang_names = {
        'en': 'anglais', 'la': 'latin', 'la-new': 'latin moderne', 'la-med': 'latin médiéval',
        'grc': 'grec ancien', 'grc-koi': 'grec koinè', 'el': 'grec',
        'fr': 'français', 'fro': 'ancien français', 'frm': 'moyen français',
        'ang': 'vieil anglais', 'enm': 'moyen anglais',
        'de': 'allemand', 'goh': 'vieux haut allemand', 'gmh': 'moyen haut allemand',
        'non': 'vieux norrois', 'gem-pro': 'proto-germanique', 'ine-pro': 'proto-indo-européen',
        'it': 'italien', 'es': 'espagnol', 'pt': 'portugais',
        'ar': 'arabe', 'he': 'hébreu', 'sa': 'sanskrit', 'fa': 'persan',
        'nl': 'néerlandais', 'dum': 'moyen néerlandais',
    }

    # Parse named parameters (e.g., mot=chaos, tr=kháos)
    named_params = {}
    positional_params = []
    for part in parts[1:]:
        if '=' in part:
            key, value = part.split('=', 1)
            named_params[key.strip()] = value.strip()
        else:
            positional_params.append(part.strip())

    # Handle French Wiktionary templates
    if template_name == 'étyl':
        # {{étyl|la|fr|mot=chaos}} or {{étyl|la|fr|paradoxon}} or {{étyl|grc|fr|mot=χάος|tr=kháos}}
        if positional_params:
            lang_code = positional_params[0]
            lang = lang_names.get(lang_code, lang_code)
            # Word can be in named param 'mot' or as 3rd positional param
            word = named_params.get('mot', '')
            if not word and len(positional_params) >= 3:
                word = positional_params[2]
            tr = named_params.get('tr', '')
            if word:
                if tr:
                    return f'*{lang}* *{word}* ({tr})'
                return f'*{lang}* *{word}*'
            return f'*{lang}*'

    elif template_name == 'polytonique':
        # {{polytonique|word|transliteration|meaning}}
        if positional_params:
            word = positional_params[0].strip('[]')
            tr = positional_params[1] if len(positional_params) >= 2 else ''
            meaning = positional_params[2] if len(positional_params) >= 3 else ''
            if meaning:
                return f'*{word}* ({tr}, « {meaning} »)'
            elif tr:
                return f'*{word}* ({tr})'
            return f'*{word}*'

    elif template_name == 'date':
        # {{date|lang=fr}} - skip date templates
        return ''

    elif template_name in ('R', 'réf'):
        # Reference templates - skip
        return ''

    # Handle English Wiktionary templates (for compatibility)
    elif template_name in ('bor', 'borrowed'):
        if len(positional_params) >= 3:
            lang = lang_names.get(positional_params[1], positional_params[1])
            word = positional_params[2]
            return f'*{lang}* *{word}*'
        elif len(positional_params) >= 2:
            lang = lang_names.get(positional_params[1], positional_params[1])
            return f'*{lang}*'

    elif template_name in ('der', 'derived'):
        if len(positional_params) >= 3:
            lang = lang_names.get(positional_params[1], positional_params[1])
            word = positional_params[2]
            return f'*{lang}* *{word}*'
        elif len(positional_params) >= 2:
            lang = lang_names.get(positional_params[1], positional_params[1])
            return f'*{lang}*'

    elif template_name in ('inh', 'inherited'):
        if len(positional_params) >= 3:
            lang = lang_names.get(positional_params[1], positional_params[1])
            word = positional_params[2]
            return f'*{lang}* *{word}*'

    elif template_name in ('m', 'mention', 'l', 'link', 'lien'):
        if len(positional_params) >= 2:
            lang = lang_names.get(positional_params[0], positional_params[0])
            word = positional_params[1]
            gloss = positional_params[3] if len(positional_params) >= 4 and positional_params[3] else ''
            if gloss:
                return f'*{lang}* *{word}* « {gloss} »'
            return f'*{lang}* *{word}*'

    elif template_name in ('cog', 'cognate'):
        if len(positional_params) >= 2:
            lang = lang_names.get(positional_params[0], positional_params[0])
            word = positional_params[1]
            return f'*{lang}* *{word}*'

    return ''


def fetch_etymology_parse_api(word: str) -> str | None:
    """Fetch etymology using Wiktionary parse API (fallback)."""
    try:
        params = {
            'action': 'parse',
            'page': word.lower(),
            'prop': 'wikitext',
            'format': 'json'
        }
        headers = {
            'User-Agent': 'AgasophyBot/1.0 (etymology lookup for dictionary project)'
        }
        response = requests.get(
            'https://fr.wiktionary.org/w/api.php',
            params=params,
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        data = response.json()

        if 'error' in data:
            return None

        wikitext = data.get('parse', {}).get('wikitext', {}).get('*', '')

        # Look for Etymology section (French: Étymologie)
        etym_match = re.search(r'===\s*\{\{S\|étymologie\}\}\s*===\n(.*?)(?=\n===)',
                              wikitext, re.DOTALL | re.IGNORECASE)
        if not etym_match:
            # Try alternative format
            etym_match = re.search(r'===\s*Étymologie\s*===\n(.*?)(?=\n===)',
                                  wikitext, re.DOTALL | re.IGNORECASE)

        if etym_match:
            etymology = etym_match.group(1).strip()

            # Parse templates and replace with readable text
            def replace_template(match):
                return parse_wiki_template(match.group(0))

            # Handle nested templates by processing innermost first
            prev = None
            while prev != etymology:
                prev = etymology
                etymology = re.sub(r'\{\{([^{}]*)\}\}', replace_template, etymology)

            # Extract text from links [[word|display]] -> display, [[word]] -> word
            etymology = re.sub(r'\[\[([^|\]]+\|)?([^\]]+)\]\]', r'\2', etymology)
            # Remove bold/italic wiki markup
            etymology = re.sub(r"'''?", '', etymology)
            # Remove reference tags
            etymology = re.sub(r'<ref[^>]*>.*?</ref>', '', etymology)
            etymology = re.sub(r'<ref[^>]*/>', '', etymology)
            # Remove any remaining HTML tags
            etymology = re.sub(r'<[^>]+>', '', etymology)
            # Fix language code artifacts like "la-lat"
            etymology = re.sub(r'\bla-lat\b', 'Late Latin', etymology)
            etymology = re.sub(r'\bla-med\b', 'Medieval Latin', etymology)
            etymology = re.sub(r'\bla-new\b', 'New Latin', etymology)
            # Remove "Displaced native ." and similar incomplete sentences
            etymology = re.sub(r'Displaced native\s*\.?', '', etymology)
            # Clean up whitespace
            etymology = re.sub(r'\s+', ' ', etymology).strip()
            # Remove leading colon (common in French Wiktionary)
            etymology = re.sub(r'^:\s*', '', etymology)
            # Remove empty parentheses and clean up punctuation
            etymology = re.sub(r'\(\s*\)', '', etymology)
            etymology = re.sub(r',\s*,', ',', etymology)
            etymology = re.sub(r'\s+', ' ', etymology).strip()
            # Remove trailing punctuation artifacts
            etymology = re.sub(r'\s*[,;]\s*$', '', etymology)
            # Capitalize first letter
            if etymology:
                etymology = etymology[0].upper() + etymology[1:]

            if etymology and len(etymology) > 10:
                return etymology

        return None

    except Exception as e:
        print(f"  Parse API error for '{word}': {e}")
        return None


def fetch_etymology(word: str) -> str | None:
    """Fetch etymology, trying multiple sources."""
    # Try REST API first
    result = fetch_etymology_wiktionary(word)
    if result:
        return result

    # Fallback to parse API
    print(f"  Trying parse API for '{word}'...")
    return fetch_etymology_parse_api(word)


def remove_origin_from_body(body: str) -> str:
    """Remove any existing Origin section from the body."""
    # Remove **Origin:** line and following content until next section or end
    body = re.sub(r'\n*\*\*Origin:\*\*.*?(?=\n\n|\n\*\*|$)', '', body, flags=re.DOTALL)
    return body.strip()


def get_word_files() -> list[Path]:
    """Get all dictionary word files (excluding index.md)."""
    files = []
    for md_file in DICTIONARY_DIR.rglob("*.md"):
        if md_file.name != "index.md":
            files.append(md_file)
    return sorted(files)


def process_word_file(file_path: Path, force: bool = False) -> bool:
    """Process a single dictionary file, adding etymology to front matter."""
    content = file_path.read_text()
    front_matter, body = parse_front_matter(content)

    word = front_matter.get("word", "")
    if not word:
        print(f"  Skipping {file_path}: no 'word' in front matter")
        return False

    # Never overwrite custom etymology
    if front_matter.get("etymology_alt"):
        print(f"  Skipping '{word}': has custom etymology (etymology_alt)")
        return False

    # Check if already has etymology in front matter and not forcing
    if not force and front_matter.get("etymology"):
        print(f"  Skipping '{word}': already has etymology")
        return False

    print(f"  Fetching etymology for '{word}'...")
    etymology = fetch_etymology(word)

    if not etymology:
        print(f"  No etymology found for '{word}'")
        return False

    # Add etymology to front matter
    front_matter["etymology"] = etymology

    # Remove any old Origin section from body
    new_body = remove_origin_from_body(body)

    # Write back
    new_content = serialize_front_matter(front_matter, new_body)
    file_path.write_text(new_content)
    print(f"  Updated {file_path.name} with etymology")

    return True


def process_single_word(word: str) -> bool:
    """Find and process a single word's dictionary entry."""
    word_lower = word.lower()
    first_letter = word_lower[0]

    file_path = DICTIONARY_DIR / first_letter / f"{word_lower}.md"

    if file_path.exists():
        print(f"Processing: {file_path}")
        return process_word_file(file_path, force=True)

    print(f"Error: Could not find dictionary entry for '{word}'")
    print(f"Expected at: {file_path}")
    return False


def process_all(force: bool = False) -> int:
    """Process all dictionary entries."""
    files = get_word_files()
    updated_count = 0

    print(f"Found {len(files)} dictionary entries")

    for i, file_path in enumerate(files):
        print(f"\nProcessing: {file_path.name}")
        if process_word_file(file_path, force=force):
            updated_count += 1

        # Rate limiting - be nice to the API
        if i < len(files) - 1:
            time.sleep(1)

    return updated_count


def main():
    parser = argparse.ArgumentParser(
        description="Fetch etymology data for dictionary entries from Wiktionary"
    )
    parser.add_argument(
        "word",
        nargs="?",
        help="Word to process (or use --all for batch processing)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Process all dictionary entries"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate even if etymology already exists"
    )

    args = parser.parse_args()

    if args.all:
        count = process_all(force=args.force)
        print(f"\nUpdated {count} entries")
    elif args.word:
        success = process_single_word(args.word)
        sys.exit(0 if success else 1)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
