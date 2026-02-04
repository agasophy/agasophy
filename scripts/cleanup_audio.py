#!/usr/bin/env python3
"""
Remove orphaned audio files not linked to any dictionary entry.

Usage:
    python cleanup_audio.py          # Dry run (show what would be deleted)
    python cleanup_audio.py --delete # Actually delete orphaned files
"""

import argparse
import re
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Missing dependency: pyyaml")
    print("Install with: pip install pyyaml")
    exit(1)

PROJECT_ROOT = Path(__file__).parent.parent
DICTIONARY_DIR = PROJECT_ROOT / "_dictionary"
AUDIO_DIR = PROJECT_ROOT / "assets" / "audio"


def parse_front_matter(content: str) -> dict:
    """Parse YAML front matter from markdown content."""
    match = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
    if not match:
        return {}
    return yaml.safe_load(match.group(1)) or {}


def get_linked_audio_files() -> set:
    """Get all audio files referenced in dictionary entries."""
    linked = set()

    for md_file in DICTIONARY_DIR.rglob("*.md"):
        if md_file.name == "index.md":
            continue

        content = md_file.read_text()
        front_matter = parse_front_matter(content)

        audio_path = front_matter.get("audio", "")
        if audio_path:
            # Extract filename from path like /assets/audio/word.mp3
            filename = Path(audio_path).name
            linked.add(filename)

    return linked


def get_existing_audio_files() -> set:
    """Get all audio files in the audio directory."""
    if not AUDIO_DIR.exists():
        return set()
    return {f.name for f in AUDIO_DIR.glob("*.mp3")}


def main():
    parser = argparse.ArgumentParser(
        description="Remove orphaned audio files not linked to any dictionary entry"
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Actually delete orphaned files (default is dry run)"
    )
    args = parser.parse_args()

    linked = get_linked_audio_files()
    existing = get_existing_audio_files()
    orphaned = existing - linked

    if not orphaned:
        print("No orphaned audio files found.")
        return

    print(f"Found {len(orphaned)} orphaned audio file(s):")
    for filename in sorted(orphaned):
        filepath = AUDIO_DIR / filename
        print(f"  {filename}")
        if args.delete:
            filepath.unlink()

    if args.delete:
        print(f"\nDeleted {len(orphaned)} file(s).")
    else:
        print(f"\nDry run - use --delete to remove these files.")


if __name__ == "__main__":
    main()
