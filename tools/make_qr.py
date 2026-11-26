"""Generate a QR code for a link (segno, BSD-3).

    python tools/make_qr.py https://<user>.github.io/five-minutes-together/
        -> app/img/qr-code.svg (used in the app, flyer and cards) + deliverables/qr-code.png/.svg
    python tools/make_qr.py https://<user>.github.io/five-minutes-together/v1.0/ --name qr-code-v1.0
        -> deliverables/qr-code-v1.0.png/.svg only (the main QR code is not touched)
"""
import sys
from pathlib import Path

import segno

ROOT = Path(__file__).resolve().parents[1]
args = [a for a in sys.argv[1:] if not a.startswith("--")]
url = args[0]
name = "qr-code"
if "--name" in sys.argv:
    name = sys.argv[sys.argv.index("--name") + 1]
    args = [a for a in args if a != name]
qr = segno.make(url, error="q")
(ROOT / "deliverables").mkdir(exist_ok=True)
if name == "qr-code":
    (ROOT / "app" / "img").mkdir(parents=True, exist_ok=True)
    qr.save(ROOT / "app" / "img" / "qr-code.svg", scale=8, border=3, dark="#0F3D4A", light="#FFFFFF", xmldecl=False, svgns=True, title="QR code: " + url)
qr.save(ROOT / "deliverables" / f"{name}.svg", scale=10, border=4, dark="#000000", light="#FFFFFF", title="QR code: " + url)
qr.save(ROOT / "deliverables" / f"{name}.png", scale=20, border=4, dark="#000000", light="#FFFFFF")
print("QR for", url, "->", name, "version", qr.version, qr.error)
