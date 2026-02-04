#!/usr/bin/env python3
"""
Migrate 'See also' links from body content to front matter.
"""

import re
from pathlib import Path
import yaml

PROJECT_ROOT = Path(__file__).parent.parent
DICTIONARY_DIR = PROJECT_ROOT / "_dictionary"


def parse_front_matter(content: str) -> tuple[dict, str]:
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", content, re.DOTALL)
    if not match:
        return {}, content
    front_matter = yaml.safe_load(match.group(1)) or {}
    body = match.group(2)
    return front_matter, body


def serialize_front_matter(front_matter: dict, body: str) -> str:
    yaml_str = yaml.dump(front_matter, default_flow_style=False, allow_unicode=True, sort_keys=False)
    return f"---\n{yaml_str}---\n{body}"


def extract_see_also(body: str) -> tuple[list, str]:
    """Extract see also links and return (links, cleaned_body)."""
    # Match **See also:** [Link](/path), [Link2](/path2)
    pattern = r'\*\*See also:\*\*\s*(.*?)(?:\n\n|\n*$)'
    match = re.search(pattern, body, re.DOTALL | re.IGNORECASE)

    if not match:
        return [], body

    links_text = match.group(1).strip()

    # Extract individual links: [Text](/path)
    link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
    links = []
    for link_match in re.finditer(link_pattern, links_text):
        links.append({
            'text': link_match.group(1),
            'url': link_match.group(2)
        })

    # Remove the see also section from body
    cleaned_body = re.sub(pattern, '', body, flags=re.DOTALL | re.IGNORECASE).strip()

    return links, cleaned_body


def process_file(file_path: Path) -> bool:
    content = file_path.read_text()
    front_matter, body = parse_front_matter(content)

    see_also, new_body = extract_see_also(body)

    if not see_also:
        return False

    front_matter['see_also'] = see_also

    new_content = serialize_front_matter(front_matter, new_body + '\n')
    file_path.write_text(new_content)

    print(f"  Updated {file_path.name}: {len(see_also)} links")
    return True


def main():
    files = [f for f in DICTIONARY_DIR.rglob("*.md") if f.name != "index.md"]
    updated = 0

    for file_path in sorted(files):
        print(f"Processing: {file_path.name}")
        if process_file(file_path):
            updated += 1

    print(f"\nUpdated {updated} files")


if __name__ == "__main__":
    main()
