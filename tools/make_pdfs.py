"""Make the PDF deliverables with Chromium's print engine:
  deliverables/printable-cards.pdf   – A4 cards for the 5 days (the in-app #/cards page)
  deliverables/teacher-flyer.pdf     – A4 Arabic flyer with the QR code (the in-app #/flyer page)
  deliverables/all-screens-backup.pdf – every screen in order, with titles (Appendix A backup)

    python tools/make_pdfs.py [--base https://…]
"""
import argparse
import datetime as dt
import html
import json
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
DELIV = ROOT / "deliverables"
sys.path.insert(0, str(ROOT / "tools"))
from serve import serve  # noqa: E402


def print_route(b, base, route, out):
    ctx = b.new_context(viewport={"width": 900, "height": 1200})
    pg = ctx.new_page()
    pg.goto(base + "#/home")
    pg.evaluate("localStorage.setItem('fmt1.settings', JSON.stringify({onboarded:true}))")
    pg.goto(base + "#/home")
    pg.locator('[data-test="home"]').wait_for()
    pg.evaluate("window.FMT.app.gateUntil = Date.now() + 10 * 60 * 1000")
    pg.goto(base + route)
    pg.locator(".print-page").first.wait_for()
    pg.evaluate("document.fonts.ready")
    pg.wait_for_timeout(800)
    pg.emulate_media(media="print")
    pg.pdf(path=str(out), format="A4", print_background=True, prefer_css_page_size=True, margin={"top": "0", "bottom": "0", "left": "0", "right": "0"})
    ctx.close()
    print("wrote", out.name)


def all_screens(b, live_url, shots: Path, version: str):
    order = json.loads((shots / "order.json").read_text(encoding="utf-8"))
    main = [o for o in order if "/extra/" not in o[0]]
    extra = [o for o in order if "/extra/" in o[0]]
    qr = (ROOT / "app" / "img" / "qr-code.svg")
    qr_html = qr.read_text(encoding="utf-8") if qr.exists() else ""
    cards = []
    for i, (src, title) in enumerate(main + extra, 1):
        cards.append(f'<figure><figcaption><b>{i}.</b> {html.escape(title)}</figcaption><img src="{src}"></figure>')
    pages = [cards[i:i + 2] for i in range(0, len(cards), 2)]
    body = "".join(f'<section class="page">{"".join(p)}</section>' for p in pages)
    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><style>
    @page {{ size: A4; margin: 12mm; }}
    body {{ font-family: "Segoe UI", Arial, sans-serif; color: #24434F; }}
    .cover {{ page-break-after: always; text-align: center; padding-top: 30mm; }}
    .cover h1 {{ font-size: 28pt; margin: 0; }} .cover h2 {{ font-weight: 400; margin: 4mm 0 10mm; }}
    .cover .qr {{ width: 55mm; margin: 0 auto; }} .cover p {{ font-size: 12pt; }}
    .page {{ display: flex; justify-content: space-between; page-break-after: always; height: 270mm; }}
    figure {{ width: 88mm; margin: 0; }} figcaption {{ font-size: 10pt; min-height: 16mm; margin-bottom: 2mm; }}
    figure img {{ width: 88mm; border: 1px solid #ccc; border-radius: 4mm; }}
    ol {{ text-align: left; display: inline-block; font-size: 10pt; }}
    </style></head><body>
    <div class="cover"><h1>5 Minutes Together – خمس دقائق معًا</h1><h2>Backup: every screen of the v{html.escape(version)} prototype, in order</h2>
    <div class="qr">{qr_html}</div><p><b>{html.escape(live_url)}</b></p>
    <p>Mobile screenshots at 390 × 844 (2× scale), taken {dt.date.today().isoformat()} from real app states (the five days were actually played in an automated browser).</p>
    <ol>{''.join(f'<li>{html.escape(t)}</li>' for _, t in main + extra)}</ol></div>
    {body}</body></html>"""
    tmp = DELIV / "_all_screens.html"
    tmp.write_text(doc, encoding="utf-8")
    pg = b.new_page()
    pg.goto(tmp.as_uri())
    pg.wait_for_timeout(500)
    pg.pdf(path=str(DELIV / "all-screens-backup.pdf"), format="A4", print_background=True, margin={"top": "12mm", "bottom": "12mm", "left": "12mm", "right": "12mm"})
    pg.close()
    tmp.unlink()
    print("wrote all-screens-backup.pdf", len(main + extra), "screens")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=None)
    ap.add_argument("--shots", default="deliverables/screenshots", help="screenshot folder with order.json")
    a = ap.parse_args()
    shots = ROOT / a.shots
    content = json.loads((ROOT / "app" / "content.json").read_text(encoding="utf-8"))
    live = content["meta"].get("liveUrl", "")
    httpd = None
    base = a.base
    if not base:
        httpd = serve(8831)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        base = "http://127.0.0.1:8831/"
    with sync_playwright() as p:
        b = p.chromium.launch()
        print_route(b, base, "#/cards", DELIV / "printable-cards.pdf")
        print_route(b, base, "#/flyer", DELIV / "teacher-flyer.pdf")
        if (shots / "order.json").exists():
            all_screens(b, live, shots, content["meta"]["version"])
        b.close()
    if httpd:
        httpd.shutdown()


if __name__ == "__main__":
    main()
