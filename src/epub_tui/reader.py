from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, ListView, ListItem, Label, Markdown
from textual.containers import Horizontal, VerticalScroll
from textual.binding import Binding

from epub_tui.epub_loader import EpubLoader


class ReaderScreen(Screen):
    BINDINGS = [
        Binding("n", "next_chapter", "Next"),
        Binding("p", "prev_chapter", "Prev"),
        Binding("t", "toggle_sidebar", "TOC"),
        Binding("escape", "back", "Back"),
        Binding("q", "back", "Back"),
    ]

    def __init__(self, epub_path: str) -> None:
        super().__init__()
        self._epub_path = epub_path
        self._loader = EpubLoader()
        self._current_index = 0

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="body"):
            yield ListView(id="chapter-list")
            with VerticalScroll(id="content-scroll"):
                yield Markdown("", id="content")
        yield Footer()

    async def on_mount(self) -> None:
        try:
            self._loader.load(self._epub_path)
        except Exception as e:
            self.query_one("#content", Markdown).update(f"**Error loading EPUB:** {e}")
            return

        self.sub_title = f"{self._loader.title} — {self._loader.author}"

        list_view = self.query_one("#chapter-list", ListView)
        list_view.clear()

        if self._loader.toc_entries:
            for entry in self._loader.toc_entries:
                indent = "  " * entry.level
                list_view.append(ListItem(Label(f"{indent}{entry.title}")))
        else:
            # Fallback: no TOC, list spine chapters directly
            for ch in self._loader.chapters:
                list_view.append(ListItem(Label(ch.title)))

        if self._loader.chapters:
            await self._load_chapter(0)
        else:
            await self.query_one("#content", Markdown).update(
                "_This EPUB has no readable chapters._"
            )

    async def _load_chapter(self, index: int, fragment: str | None = None) -> None:
        if not self._loader.chapters:
            return
        index = max(0, min(index, len(self._loader.chapters) - 1))
        self._current_index = index

        content = self.query_one("#content", Markdown)
        md_text = self._loader.get_chapter_markdown(index)
        # Must await so the DOM is fully updated before goto_anchor() is called
        await content.update(md_text)

        if fragment:
            anchor = self._loader.find_anchor_for_fragment(index, fragment)
            if anchor and content.goto_anchor(anchor):
                return
        # Default: scroll to top
        self.query_one("#content-scroll", VerticalScroll).scroll_home(animate=False)

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.index is None:
            return

        if self._loader.toc_entries:
            entry = self._loader.toc_entries[event.index]
            ch_index = self._loader.find_chapter_index(entry.file_href)
            if ch_index == -1:
                return
            await self._load_chapter(ch_index, entry.fragment)
        else:
            await self._load_chapter(event.index)

    async def action_next_chapter(self) -> None:
        await self._load_chapter(self._current_index + 1)

    async def action_prev_chapter(self) -> None:
        await self._load_chapter(self._current_index - 1)

    def action_toggle_sidebar(self) -> None:
        sidebar = self.query_one("#chapter-list", ListView)
        sidebar.display = not sidebar.display

    def action_back(self) -> None:
        if len(self.app.screen_stack) > 1:
            self.app.pop_screen()
        else:
            self.app.exit()
