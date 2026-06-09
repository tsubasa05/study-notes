#!/usr/bin/env python3
"""Validate that the study-note index matches the repository's HTML files."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
import re
import sys
from urllib.parse import unquote, urlsplit


def class_tokens(attrs: dict[str, str | None]) -> set[str]:
    return set((attrs.get("class") or "").split())


def clean_text(parts: list[str]) -> str:
    return re.sub(r"\s+", " ", "".join(parts)).strip()


class NoteMetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._capture: str | None = None
        self._parts: list[str] = []
        self.title = ""
        self.h1 = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "title" and not self.title:
            self._capture = "title"
            self._parts = []
        elif tag == "h1" and not self.h1:
            self._capture = "h1"
            self._parts = []

    def handle_data(self, data: str) -> None:
        if self._capture:
            self._parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == self._capture:
            value = clean_text(self._parts)
            setattr(self, self._capture, value)
            self._capture = None
            self._parts = []


@dataclass
class Card:
    categories: list[str]
    href: str | None = None


class IndexParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.cards: list[Card] = []
        self.filters: set[str] = set()
        self.visible_count_text: list[str] = []
        self._current_card: Card | None = None
        self._capture_count = False

    def handle_starttag(self, tag: str, attrs_list: list[tuple[str, str | None]]) -> None:
        attrs = dict(attrs_list)
        classes = class_tokens(attrs)

        if tag == "article" and "note-card" in classes:
            self._current_card = Card((attrs.get("data-category") or "").split())
            self.cards.append(self._current_card)

        if tag == "a" and self._current_card and "card-link" in classes:
            self._current_card.href = attrs.get("href")

        if tag == "button" and "filter-button" in classes:
            value = attrs.get("data-filter")
            if value:
                self.filters.add(value)

        if attrs.get("id") == "visible-count":
            self._capture_count = True

    def handle_data(self, data: str) -> None:
        if self._capture_count:
            self.visible_count_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "article":
            self._current_card = None
        if tag == "span" and self._capture_count:
            self._capture_count = False


def read_html(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def note_title(path: Path) -> str:
    parser = NoteMetadataParser()
    parser.feed(read_html(path))
    return parser.h1 or parser.title or "(no title)"


def discover_notes(root: Path, index_path: Path) -> dict[str, Path]:
    notes: dict[str, Path] = {}
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() != ".html":
            continue
        relative = path.relative_to(root)
        if path == index_path or any(part.startswith(".") for part in relative.parts):
            continue
        notes[relative.as_posix()] = path
    return notes


def normalize_local_href(href: str) -> str | None:
    parsed = urlsplit(href)
    if parsed.scheme or parsed.netloc:
        return None
    path = unquote(parsed.path)
    if not path or path.startswith("/"):
        return None
    return PurePosixPath(path).as_posix().removeprefix("./")


def validate(root: Path) -> int:
    index_path = root / "index.html"
    if not index_path.is_file():
        print(f"ERROR: index.html not found under {root}", file=sys.stderr)
        return 1

    parser = IndexParser()
    parser.feed(read_html(index_path))
    notes = discover_notes(root, index_path)
    errors: list[str] = []
    warnings: list[str] = []
    indexed_paths: list[str] = []

    for position, card in enumerate(parser.cards, start=1):
        if not card.href:
            errors.append(f"card {position} has no .card-link href")
            continue

        relative = normalize_local_href(card.href)
        if relative is None:
            errors.append(f"card {position} has a non-local or invalid href: {card.href}")
            continue

        indexed_paths.append(relative)
        if relative not in notes:
            errors.append(f"card {position} links to a missing note: {relative}")

        if not card.categories:
            errors.append(f"card {position} has no data-category")
        for category in card.categories:
            if category not in parser.filters:
                errors.append(
                    f"card {position} uses category '{category}' without a matching filter"
                )

    duplicates = sorted(path for path, count in Counter(indexed_paths).items() if count > 1)
    for path in duplicates:
        errors.append(f"duplicate card link: {path}")

    for relative in sorted(set(notes) - set(indexed_paths)):
        errors.append(f"unindexed note: {relative} | {note_title(notes[relative])}")

    count_text = clean_text(parser.visible_count_text)
    match = re.search(r"\d+", count_text)
    if not match:
        errors.append("#visible-count does not contain a number")
    elif int(match.group()) != len(parser.cards):
        errors.append(
            f"#visible-count is {match.group()}, but {len(parser.cards)} cards exist"
        )

    used_categories = {category for card in parser.cards for category in card.categories}
    for category in sorted(parser.filters - {"all"} - used_categories):
        warnings.append(f"unused category filter: {category}")

    print(f"Index: {index_path.relative_to(root).as_posix()}")
    print(f"Cards: {len(parser.cards)}")
    print(f"Notes: {len(notes)}")
    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}")

    if errors:
        print(f"Result: FAILED ({len(errors)} error(s))")
        return 1

    print("Result: OK")
    return 0


def parse_args() -> argparse.Namespace:
    default_root = Path(__file__).resolve().parents[4]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=default_root,
        help="repository root containing index.html",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return validate(args.root.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
