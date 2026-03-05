from __future__ import annotations

import os
from dataclasses import dataclass

import ebooklib
from ebooklib import epub
import html2text
from bs4 import BeautifulSoup


@dataclass
class Chapter:
    id: str
    title: str
    content: bytes


def _collect_toc_titles(toc_items) -> dict[str, str]:
    """Recursively collect href -> title mapping from TOC."""
    result: dict[str, str] = {}
    for item in toc_items:
        if isinstance(item, epub.Link):
            # Strip fragment identifiers from href
            href = item.href.split("#")[0]
            result[href] = item.title
        elif isinstance(item, tuple) and len(item) == 2:
            section, children = item
            if isinstance(section, epub.Section) and section.href:
                href = section.href.split("#")[0]
                result[href] = section.title
            result.update(_collect_toc_titles(children))
    return result


class EpubLoader:
    def __init__(self):
        self._book: epub.EpubBook | None = None
        self._path: str = ""
        self.chapters: list[Chapter] = []
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

        # Build href -> title map from TOC
        toc_map = _collect_toc_titles(self._book.toc)

        # Build chapters from spine order
        self.chapters = []
        for item_id, _linear in self._book.spine:
            item = self._book.get_item_with_id(item_id)
            if item is None or item.get_type() != ebooklib.ITEM_DOCUMENT:
                continue

            # Resolve title: TOC map -> fallback
            href = item.get_name()
            href_basename = os.path.basename(href)
            chapter_title = (
                toc_map.get(href)
                or toc_map.get(href_basename)
            )

            if chapter_title is None:
                continue

            self.chapters.append(
                Chapter(
                    id=item_id,
                    title=chapter_title,
                    content=item.get_body_content(),
                )
            )

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
