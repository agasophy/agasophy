#!/usr/bin/env python3
"""
Generate IPA pronunciation and audio files for dictionary entries.

Usage:
    python pronunciation.py WORD              # Process a single word
    python pronunciation.py --all             # Process all entries missing pronunciation
    python pronunciation.py --all --force     # Regenerate all entries

Requirements:
    pip install eng-to-ipa gtts pyyaml
"""

import argparse
import os
import re
import sys
from pathlib import Path

try:
    from epitran import Epitran
    from gtts import gTTS
    import yaml
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install epitran gtts pyyaml")
    sys.exit(1)

# Initialize French transliterator
epi = Epitran('fra-Latn')

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DICTIONARY_DIR = PROJECT_ROOT / "_dictionary"
AUDIO_DIR = PROJECT_ROOT / "assets" / "audio"


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


def generate_ipa(word: str) -> str:
    """Generate IPA pronunciation for a French word using epitran."""
    try:
        result = epi.transliterate(word.lower())
        if not result or result == word.lower():
            print(f"  Warning: Could not generate IPA for '{word}'")
            return ""
        return f"/{result}/"
    except Exception as e:
        print(f"  Warning: Could not generate IPA for '{word}': {e}")
        return ""


def generate_audio(word: str, output_path: Path) -> bool:
    """Generate MP3 audio file for a word."""
    try:
        tts = gTTS(word, lang='fr')
        output_path.parent.mkdir(parents=True, exist_ok=True)
        tts.save(str(output_path))
        return True
    except Exception as e:
        print(f"  Warning: Could not generate audio for '{word}': {e}")
        return False


def get_word_files() -> list[Path]:
    """Get all dictionary word files (excluding index.md)."""
    files = []
    for md_file in DICTIONARY_DIR.rglob("*.md"):
        if md_file.name != "index.md":
            files.append(md_file)
    return sorted(files)


def process_word_file(file_path: Path, force: bool = False) -> bool:
    """Process a single dictionary file, adding pronunciation and audio."""
    content = file_path.read_text()
    front_matter, body = parse_front_matter(content)

    word = front_matter.get("word", "")
    if not word:
        print(f"  Skipping {file_path}: no 'word' in front matter")
        return False

    word_lower = word.lower()
    audio_path = AUDIO_DIR / f"{word_lower}.mp3"
    audio_url = f"/assets/audio/{word_lower}.mp3"

    updated = False

    # Generate pronunciation if missing or forced
    if force or not front_matter.get("pronunciation"):
        print(f"  Generating IPA for '{word}'...")
        pronunciation = generate_ipa(word)
        if pronunciation:
            front_matter["pronunciation"] = pronunciation
            updated = True

    # Generate audio if missing or forced
    if force or not audio_path.exists():
        print(f"  Generating audio for '{word}'...")
        if generate_audio(word, audio_path):
            front_matter["audio"] = audio_url
            updated = True
    elif "audio" not in front_matter:
        # Audio file exists but not in front matter
        front_matter["audio"] = audio_url
        updated = True

    # Write back if updated
    if updated:
        new_content = serialize_front_matter(front_matter, body)
        file_path.write_text(new_content)
        print(f"  Updated {file_path.name}")

    return updated


def process_single_word(word: str) -> bool:
    """Find and process a single word's dictionary entry."""
    word_lower = word.lower()
    first_letter = word_lower[0]

    # Look for the file
    possible_paths = [
        DICTIONARY_DIR / first_letter / f"{word_lower}.md",
    ]

    for file_path in possible_paths:
        if file_path.exists():
            print(f"Processing: {file_path}")
            return process_word_file(file_path, force=True)

    print(f"Error: Could not find dictionary entry for '{word}'")
    print(f"Expected at: {possible_paths[0]}")
    return False


def process_all(force: bool = False) -> int:
    """Process all dictionary entries."""
    files = get_word_files()
    updated_count = 0

    print(f"Found {len(files)} dictionary entries")

    for file_path in files:
        print(f"\nProcessing: {file_path.name}")
        if process_word_file(file_path, force=force):
            updated_count += 1

    return updated_count


def main():
    parser = argparse.ArgumentParser(
        description="Generate IPA pronunciation and audio for dictionary entries"
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
        help="Regenerate even if pronunciation/audio already exists"
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
