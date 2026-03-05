from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, DirectoryTree
from textual.binding import Binding


class BrowserScreen(Screen):
    BINDINGS = [
        Binding("q", "app.quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield DirectoryTree(".")
        yield Footer()

    def on_directory_tree_file_selected(
        self, event: DirectoryTree.FileSelected
    ) -> None:
        path = str(event.path)
        if path.lower().endswith(".epub"):
            from epub_tui.reader import ReaderScreen
            self.app.push_screen(ReaderScreen(path))


class EpubTuiApp(App):
    CSS_PATH = "epub_tui.tcss"
    TITLE = "EPUB Reader"

    def __init__(self, epub_path: str | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._epub_path = epub_path

    def on_mount(self) -> None:
        if self._epub_path:
            from epub_tui.reader import ReaderScreen
            self.push_screen(ReaderScreen(self._epub_path))
        else:
            self.push_screen(BrowserScreen())
