# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the app (file browser)
uv run epub-tui

# Open a specific EPUB directly
uv run epub-tui path/to/book.epub

# Install/sync dependencies
uv sync

# Add a dependency
uv add <package>
```

There are no tests or linting configured.

## Architecture

The app is a [Textual](https://textual.textualize.io/) TUI with two screens managed via a stack:

**Screen flow:**
1. `EpubTuiApp` (`app.py`) — root app, pushes either `BrowserScreen` or `ReaderScreen` on mount
2. `BrowserScreen` (`app.py`) — file browser using Textual's `DirectoryTree`; pushes `ReaderScreen` when an `.epub` is selected
3. `ReaderScreen` (`reader.py`) — two-panel layout: `ListView` TOC sidebar (left, 25%) + `Markdown` content area (right)

**Data flow:**
- `EpubLoader` (`epub_loader.py`) parses the EPUB in `ReaderScreen.on_mount()` (not in `compose()`)
- Chapters are built from **spine order** (not TOC order); TOC is only used to resolve chapter titles via `_collect_toc_titles`
- `get_chapter_markdown()` converts chapter HTML→Markdown via `html2text` (with `body_width=0` to disable wrapping), falling back to BeautifulSoup plain text on error

**Key Textual patterns used:**
- `CSS_PATH = "epub_tui.tcss"` in `EpubTuiApp` is resolved relative to `app.py` by Textual
- `ListView` is populated empty in `compose()` then rebuilt in `on_mount()` after loading
- `BINDINGS` on each `Screen` define footer shortcuts; `action_*` methods handle them
