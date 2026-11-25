"""Render the app icons from the Sanad mascot SVG (art.js) with Playwright/Chromium.
Outputs app/icons/icon-192.png, icon-512.png, maskable-512.png, apple-touch-icon.png, favicon.svg"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).parent))
from serve import serve  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "app" / "icons"
OUT.mkdir(parents=True, exist_ok=True)

PAGE = """<!doctype html><html><body style="margin:0;background:transparent">
<div id="c"></div>
<script type="module">
import { sanadParts } from './js/art.js';
window.makeIcon = (size, bg, pad) => {
  const inner = sanadParts({ anim: false, shadow: false });
  const r = size * 0.22;
  const bgRect = bg ? `<rect width="200" height="200" rx="${bg === 'square' ? 0 : 44}" fill="#1AA6A6"/><circle cx="100" cy="100" r="78" fill="#BFE9E6" opacity=".55"/>` : '';
  const s = (1 - pad * 2);
  document.getElementById('c').innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="${size}" height="${size}">${bgRect}<g transform="translate(${200 * pad} ${200 * pad + 6}) scale(${s})">${inner}</g></svg>`;
  return document.getElementById('c').innerHTML;
};
window.ready = true;
</script></body></html>"""


def main():
    (ROOT / "app" / "_icon.html").write_text(PAGE, encoding="utf-8")
    httpd = serve(8799)
    import threading
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page()
            pg.goto("http://127.0.0.1:8799/_icon.html")
            pg.wait_for_function("window.ready === true")
            jobs = [("icon-192.png", 192, "round", 0.06), ("icon-512.png", 512, "round", 0.06),
                    ("maskable-512.png", 512, "square", 0.17), ("apple-touch-icon.png", 180, "square", 0.08)]
            for name, size, bg, pad in jobs:
                pg.set_viewport_size({"width": size, "height": size})
                pg.evaluate(f"makeIcon({size}, '{bg}', {pad})")
                pg.locator("#c svg").screenshot(path=str(OUT / name), omit_background=(bg == "round"))
                print("wrote", name)
            svg = pg.evaluate("makeIcon(64, 'round', 0.04)")
            (OUT / "favicon.svg").write_text(svg, encoding="utf-8")
            print("wrote favicon.svg")
            b.close()
    finally:
        httpd.shutdown()
        (ROOT / "app" / "_icon.html").unlink(missing_ok=True)


if __name__ == "__main__":
    main()
