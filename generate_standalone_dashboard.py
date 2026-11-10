#!/usr/bin/env python3
"""
generate_standalone_dashboard.py - Generates the standalone dashboard.html
Inlines styles.css, app.js, and preloaded snapshot data from local CSVs and JSONs
so the user can open dashboard.html directly in any browser by double-clicking.
"""

import json
from pathlib import Path
import dashboard_server

BASE_DIR = Path(__file__).resolve().parent
DASHBOARD_DIR = BASE_DIR / "dashboard"
STANDALONE_HTML = BASE_DIR / "dashboard.html"

def generate():
    index_html = (DASHBOARD_DIR / "index.html").read_text(encoding="utf-8")
    styles_css = (DASHBOARD_DIR / "styles.css").read_text(encoding="utf-8")
    app_js = (DASHBOARD_DIR / "app.js").read_text(encoding="utf-8")
    
    # Get live snapshot data
    stats = dashboard_server.build_full_stats()
    stats_json_str = json.dumps(stats, ensure_ascii=False, indent=2)

    # Inline CSS
    html = index_html.replace(
        '<link rel="stylesheet" href="styles.css">',
        f'<style>\n{styles_css}\n</style>'
    )

    # In app.js, initialize state.data with live snapshot
    custom_app_js = app_js.replace(
        'data: {',
        f'data: {stats_json_str},\n  _placeholder: {{'
    )

    # Inline JS
    html = html.replace(
        '<script src="app.js"></script>',
        f'<script>\n{custom_app_js}\n</script>'
    )

    STANDALONE_HTML.write_text(html, encoding="utf-8")
    print(f"✅ Generated standalone {STANDALONE_HTML} ({len(html)} bytes)")

if __name__ == "__main__":
    generate()
