# run_shiny.py

import os
import socket
import threading
import time
import webbrowser
from pathlib import Path
from shiny import run_app
from shiny.express import wrap_express_app

def open_browser(host: str, port: int, timeout: float = 10.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1):
                webbrowser.open(f"http://{host}:{port}")
                return
        except OSError:
            time.sleep(0.1)
    raise RuntimeError(f"Timed out waiting for {host}:{port}")

if __name__ == "__main__":
    # wrap_express_app wants a pathlib.Path
    app_path = Path(__file__).parent / "shiny_implementation.py"
    app = wrap_express_app(app_path)

    host, port = "127.0.0.1", 8000

    # 1) spawn a thread that will open exactly one tab
    threading.Thread(target=open_browser, args=(host, port), daemon=True).start()

    # 2) serve in-process, no reload, no extra subprocesses
    run_app(
        app,
        host=host,
        port=port,
        reload=False,         # ← disable hot-reload here
        launch_browser=False  # ← we’ll open it ourselves
    )
