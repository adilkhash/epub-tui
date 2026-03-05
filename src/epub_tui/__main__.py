import sys
from epub_tui.app import EpubTuiApp


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else None
    app = EpubTuiApp(epub_path=path)
    app.run()


if __name__ == "__main__":
    main()
