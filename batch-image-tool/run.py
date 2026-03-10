#!/usr/bin/env python3
"""
Launch Batch Image Tool: choose desktop (tkinter) or web UI.

  python run.py          → web UI (default)
  python run.py --web    → web UI
  python run.py --tk     → tkinter desktop UI (requires tkinter)

Or run directly:
  python -m app_web      → web UI
  python -m gui          → tkinter UI only (exits with message if tkinter missing)
"""
import sys


def main():
    if "--tk" in sys.argv:
        from gui import HAS_TK, run_tk
        if not HAS_TK:
            print("tkinter not available. Use web UI: python run.py --web")
            sys.exit(1)
        run_tk()
    else:
        from app_web import app, open_browser
        import threading
        threading.Timer(1.0, open_browser).start()
        app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
