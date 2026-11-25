"""Generate the QR code for the live link (segno, MIT licence).
Writes app/img/qr-code.svg (used in the app, flyer and cards) and deliverables/qr-code.png + .svg.

    python tools/make_qr.py https://<user>.github.io/five-minutes-together/
"""
import sys
from pathlib import Path

import segno

ROOT = Path(__file__).resolve().parents[1]
url = sys.argv[1]
qr = segno.make(url, error="q")
(ROOT / "app" / "img").mkdir(parents=True, exist_ok=True)
(ROOT / "deliverables").mkdir(exist_ok=True)
qr.save(ROOT / "app" / "img" / "qr-code.svg", scale=8, border=3, dark="#0F3D4A", light="#FFFFFF", xmldecl=False, svgns=True, title="QR code: " + url)
qr.save(ROOT / "deliverables" / "qr-code.svg", scale=10, border=4, dark="#000000", light="#FFFFFF", title="QR code: " + url)
qr.save(ROOT / "deliverables" / "qr-code.png", scale=20, border=4, dark="#000000", light="#FFFFFF")
print("QR for", url, "version", qr.version, qr.error)
