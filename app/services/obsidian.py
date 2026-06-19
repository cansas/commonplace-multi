"""Parse Readwise Obsidian export files from a local vault."""

import re
from typing import List, Dict
from datetime import datetime


def parse_readwise_md(content: str, filename: str = "") -> List[Dict]:
    """
    Parse a Readwise Obsidian-format .md file.
    Format:
      # Book Title
      ## Metadata
      - Author: [[Author Name]]
      - Full Title: Book Title
      - Category: #books
      ## Highlights
      - Highlight text ([Location 123](url))
          - Tags: [[tag]]
    """
    highlights = []
    book_title = ""
    book_author = ""

    # Extract title from # heading
    title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if title_match:
        book_title = title_match.group(1).strip()

    # Extract author from metadata
    author_match = re.search(r"^-\s+Author:\s+\[\[(.+?)\]\]", content, re.MULTILINE)
    if author_match:
        book_author = author_match.group(1).strip()

    # Category
    category = "books"
    cat_match = re.search(r"^-\s+Category:\s+#(\w+)", content, re.MULTILINE)
    if cat_match:
        category = cat_match.group(1)

    # Find the ## Highlights section
    highlights_section = re.split(r"^##\s+Highlights", content, flags=re.MULTILINE)
    if len(highlights_section) < 2:
        raise ValueError("No '## Highlights' section found in file")

    body = highlights_section[1]

    # Parse highlighted lines from Obsidian Readwise format.
    # Lines starting with "- " (with possible leading whitespace) are highlights.
    # Sub-lines with "Tags:" contain tags.
    current_highlight = None

    for line in body.split("\n"):
        stripped = line.strip()

        # Check for tag continuation line
        if current_highlight and stripped.startswith("- Tags:"):
            tag_matches = re.findall(r"\[\[(.+?)\]\]", stripped)
            current_highlight.setdefault("tags", []).extend(tag_matches)
            continue

        # Check for highlight line
        hl_match = re.match(r"^-\s+(.+?)(?:\s*\(Location\s+(\d+).*?\))?\s*$", stripped)
        if hl_match and not stripped.startswith("- Tags:"):
            # Save previous
            if current_highlight:
                highlights.append(current_highlight)

            text = hl_match.group(1).strip()
            # Remove note indicator if present
            text = re.sub(r"^\*\*Note:\*\*\s*", "", text)
            # Strip trailing Readwise/Kindle URLs like ([Location N](url)) or (url)
            text = re.sub(r"\s*\(\[?[Ll]ocation\s+\d+\]?\([^)]+\)\)?\s*$", "", text)
            text = text.strip()

            current_highlight = {
                "text": text,
                "book_title": book_title,
                "book_author": book_author,
                "category": category,
                "source_type": "readwise",
                "tags": [],
            }

            if hl_match.group(2):
                current_highlight["page"] = int(hl_match.group(2))
            continue

        # Handle multi-line highlights (continuation lines)
        if current_highlight and stripped and not stripped.startswith("#") and not stripped.startswith("[!") and not stripped.startswith("---"):
            # Could be continuation of previous highlight text
            if current_highlight.get("_collecting"):
                current_highlight["text"] += " " + stripped
            else:
                current_highlight["_collecting"] = True
                current_highlight["text"] += " " + stripped

    # Don't forget the last one
    if current_highlight:
        # Clean up internal fields

        inner = {k: v for k, v in current_highlight.items() if not k.startswith("_")}
        highlights.append(inner)

    return highlights


def parse_readwise_folder(file_contents: Dict[str, str]) -> List[Dict]:
    """
    Parse multiple files from a Readwise Books folder.
    file_contents: mapping of filename -> markdown content
    """
    all_highlights = []
    for filename, content in file_contents.items():
        all_highlights.extend(parse_readwise_md(content, filename))
    return all_highlights
