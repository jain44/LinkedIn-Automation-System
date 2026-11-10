#!/usr/bin/env python3
"""
start_dashboard.py - One-Click Launcher for Outreach Dashboard
Starts the local API server and automatically opens http://localhost:5050 in the browser.
"""

import sys
import time
import webbrowser
import threading
from dashboard_server import run_server, DEFAULT_PORT

def open_browser():
    time.sleep(1.2)
    url = f"http://localhost:{DEFAULT_PORT}"
    print(f"🌐 Opening {url} in your default browser...")
    webbrowser.open(url)

if __name__ == "__main__":
    # Launch browser after slight delay
    threading.Thread(target=open_browser, daemon=True).start()
    try:
        run_server(DEFAULT_PORT)
    except KeyboardInterrupt:
        print("\n👋 Dashboard server stopped.")
