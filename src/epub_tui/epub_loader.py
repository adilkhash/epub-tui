from __future__ import annotations

import os
import re
from collections import defaultdict
from dataclasses import dataclass
from urllib.parse import quote

import ebooklib
from ebooklib import epub
import html2text
from bs4 import BeautifulSoup


@dataclass
class Chapter:
    id: str
    title: str
    content: bytes
    href: str


@dataclass
class TocEntry:
    title: str
    file_href: str    # chapter file, no fragment
    fragment: str | None  # anchor id within the file, or None
    level: int        # nesting depth (0 = top-level)


def _collect_toc_entries(toc_items, level: int = 0) -> list[TocEntry]:
    """Recursively collect all TOC entries as a flat list with nesting depth."""
    entries: list[TocEntry] = []
    for item in toc_items:
        if isinstance(item, epub.Link):
            if item.title:
                parts = item.href.split("#", 1)
                entries.append(TocEntry(
                    title=item.title,
                    file_href=parts[0],
                    fragment=parts[1] if len(parts) > 1 else None,
                    level=level,
                ))
        elif isinstance(item, tuple) and len(item) == 2:
            section, children = item
            if isinstance(section, epub.Section) and section.title:
                parts = (section.href or "").split("#", 1)
                entries.append(TocEntry(
                    title=section.title,
                    file_href=parts[0],
                    fragment=parts[1] if len(parts) > 1 else None,
                    level=level,
                ))
            entries.extend(_collect_toc_entries(children, level + 1))
    return entries


_SLUG_STRIP_RE = re.compile(r"[^\w\s-]")
_SLUG_SPACE_RE = re.compile(r"\s+")


def _textual_slug(text: str) -> str:
    """Replicate Textual's heading slug algorithm for goto_anchor() compatibility."""
    s = text.strip().lower()
    s = _SLUG_STRIP_RE.sub("", s)
    s = _SLUG_SPACE_RE.sub("-", s)
    return quote(s)


class EpubLoader:
    def __init__(self):
        self._book: epub.EpubBook | None = None
        self._path: str = ""
        self.chapters: list[Chapter] = []
        self.toc_entries: list[TocEntry] = []
        self.title: str = "Unknown Title"
        self.author: str = "Unknown"

    def load(self, path: str) -> None:
        self._path = path
        self._book = epub.read_epub(path)

        # Extract metadata
        title_meta = self._book.get_metadata("DC", "title")
        self.title = title_meta[0][0] if title_meta else os.path.basename(path)

        author_meta = self._book.get_metadata("DC", "creator")
        self.author = author_meta[0][0] if author_meta else "Unknown"

        # Build full TOC entry list
        self.toc_entries = _collect_toc_entries(self._book.toc)

        # Build href -> title map for chapter title resolution.
        # Prefer fragment-less entries; first match wins.
        toc_map: dict[str, str] = {}
        for entry in self.toc_entries:
            if not entry.fragment:
                toc_map.setdefault(entry.file_href, entry.title)
                toc_map.setdefault(os.path.basename(entry.file_href), entry.title)
        # Fallback: also include fragment entries (covers books where every link has a fragment)
        for entry in self.toc_entries:
            toc_map.setdefault(entry.file_href, entry.title)
            toc_map.setdefault(os.path.basename(entry.file_href), entry.title)

        # Build chapters from spine order
        self.chapters = []
        for item_id, _linear in self._book.spine:
            item = self._book.get_item_with_id(item_id)
            if item is None or item.get_type() != ebooklib.ITEM_DOCUMENT:
                continue

            href = item.get_name()
            href_basename = os.path.basename(href)
            chapter_title = (
                toc_map.get(href)
                or toc_map.get(href_basename)
                or "-"
            )

            self.chapters.append(
                Chapter(
                    id=item_id,
                    title=chapter_title,
                    content=item.get_body_content(),
                    href=href,
                )
            )

    def find_chapter_index(self, file_href: str) -> int:
        """Return spine index for file_href, or -1 if not found."""
        basename = os.path.basename(file_href)
        for i, ch in enumerate(self.chapters):
            if ch.href == file_href or os.path.basename(ch.href) == basename:
                return i
        return -1

    def find_anchor_for_fragment(self, chapter_index: int, fragment_id: str) -> str | None:
        """Translate an HTML id attribute to Textual's goto_anchor()-compatible slug.

        Walks all headings in document order with the same TrackedSlugs logic
        Textual uses, so the returned slug is guaranteed to match.
        """
        if chapter_index < 0 or chapter_index >= len(self.chapters):
            return None

        html_str = self.chapters[chapter_index].content.decode("utf-8", errors="replace")
        soup = BeautifulSoup(html_str, "html.parser")

        HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}

        # Locate which heading this fragment maps to.
        # Iterate all tags in document order; track last seen heading.
        last_heading = None
        target_heading = None
        for el in soup.find_all(True):
            if el.name in HEADING_TAGS:
                last_heading = el
            if el.get("id") == fragment_id:
                if el.name in HEADING_TAGS:
                    target_heading = el
                else:
                    # Prefer a heading nested inside the target element
                    inner = el.find(["h1", "h2", "h3", "h4", "h5", "h6"])
                    target_heading = inner if inner is not None else last_heading
                break

        if target_heading is None:
            return None

        # Walk all headings in order, replicating TrackedSlugs to get the correct slug.
        seen: defaultdict[str, int] = defaultdict(int)
        for heading in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
            base = _textual_slug(heading.get_text())
            count = seen[base]
            seen[base] += 1
            slug = base if count == 0 else f"{base}-{count}"
            if heading is target_heading:
                return slug

        return None

    def get_chapter_markdown(self, index: int) -> str:
        if not self.chapters or index < 0 or index >= len(self.chapters):
            return "_No content available._"

        raw_html = self.chapters[index].content
        html_str = raw_html.decode("utf-8", errors="replace")

        try:
            converter = html2text.HTML2Text()
            converter.ignore_links = False
            converter.ignore_images = True
            converter.body_width = 0  # No wrapping — let Textual handle it
            return converter.handle(html_str)
        except Exception:
            # Fallback to BeautifulSoup plain text
            soup = BeautifulSoup(html_str, "html.parser")
            return soup.get_text(separator="\n")
