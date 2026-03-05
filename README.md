# epub-tui

A terminal EPUB reader built with [Textual](https://textual.textualize.io/).

## Features

- File browser to navigate and open EPUB files
- Chapter sidebar with TOC navigation
- Keyboard-driven reading

## Installation

Requires [uv](https://docs.astral.sh/uv/).

```bash
git clone <repo>
cd epub-tui
uv sync
```

## Usage

```bash
# Open file browser
uv run epub-tui

# Open a specific EPUB
uv run epub-tui path/to/book.epub
```

## Keybindings

| Key | Action |
|-----|--------|
| `Enter` | Open EPUB / select chapter |
| `n` | Next chapter |
| `p` | Previous chapter |
| `t` | Toggle TOC sidebar |
| `Esc` / `q` | Back / Quit |

## Dependencies

- [textual](https://github.com/Textualize/textual) — TUI framework
- [ebooklib](https://github.com/aerkalov/ebooklib) — EPUB parsing
- [html2text](https://github.com/Alir3z4/html2text) — HTML to Markdown conversion
- [beautifulsoup4](https://www.crummy.com/software/BeautifulSoup/) — HTML fallback parsing
