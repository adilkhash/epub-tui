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

    def on_mount(self) -> None:
        try:
            self._loader.load(self._epub_path)
        except Exception as e:
            self.query_one("#content", Markdown).update(f"**Error loading EPUB:** {e}")
            return

        self.sub_title = f"{self._loader.title} — {self._loader.author}"

        # Rebuild ListView now that chapters are loaded
        list_view = self.query_one("#chapter-list", ListView)
        list_view.clear()
        for ch in self._loader.chapters:
            list_view.append(ListItem(Label(ch.title)))

        if self._loader.chapters:
            self._load_chapter(0)
        else:
            self.query_one("#content", Markdown).update(
                "_This EPUB has no readable chapters._"
            )

    def _load_chapter(self, index: int) -> None:
        if not self._loader.chapters:
            return
        index = max(0, min(index, len(self._loader.chapters) - 1))
        self._current_index = index

        md_text = self._loader.get_chapter_markdown(index)
        self.query_one("#content", Markdown).update(md_text)

        # Scroll to top
        scroll = self.query_one("#content-scroll", VerticalScroll)
        scroll.scroll_home(animate=False)

        # Highlight active chapter in sidebar
        list_view = self.query_one("#chapter-list", ListView)
        list_view.index = index

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.index is not None:
            self._load_chapter(event.index)

    def action_next_chapter(self) -> None:
        self._load_chapter(self._current_index + 1)

    def action_prev_chapter(self) -> None:
        self._load_chapter(self._current_index - 1)

    def action_toggle_sidebar(self) -> None:
        sidebar = self.query_one("#chapter-list", ListView)
        sidebar.display = not sidebar.display

    def action_back(self) -> None:
        if len(self.app.screen_stack) > 1:
            self.app.pop_screen()
        else:
            self.app.exit()
