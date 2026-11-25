"""Zip the app folder: deliverables/five-minutes-together.zip  (python tools/make_zip.py)"""
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
OUT = ROOT / "deliverables" / "five-minutes-together.zip"
live = json.loads((APP / "content.json").read_text(encoding="utf-8"))["meta"].get("liveUrl", "")

NOTE = f"""5 Minutes Together – خمس دقائق معًا  (v1.0)

This zip is the complete app folder (plain HTML, CSS and JavaScript; no build step).

Live version: {live}

To run this folder yourself, it must be served by a web server (browsers do not allow
JavaScript modules or the offline service worker from a double-clicked file), for example:
    python -m http.server 8000      (inside the "app" folder), then open http://localhost:8000/
Any static host works (GitHub Pages, Netlify, a school server).

To open the app with a double-click and no internet, use offline-backup.html instead
(the whole app in one file).

Teachers can change letters, words and Arabic texts in app/content.json.
"""

with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    z.writestr("five-minutes-together/README.txt", NOTE)
    for p in sorted(APP.rglob("*")):
        if p.is_file() and not p.name.startswith("_"):
            z.write(p, "five-minutes-together/app/" + p.relative_to(APP).as_posix())
print(f"wrote {OUT.name} ({OUT.stat().st_size / 1024 / 1024:.2f} MB)")
