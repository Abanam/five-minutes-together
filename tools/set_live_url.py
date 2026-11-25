"""Record the public link everywhere it is needed:
app/content.json (meta.liveUrl – used by the teacher page, WhatsApp message, flyer and cards),
README.md and deliverables/REPORT_NOTES.md ({{LIVE_URL}} placeholders).

    python tools/set_live_url.py https://<user>.github.io/five-minutes-together/
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
url = sys.argv[1].rstrip("/") + "/"

p = ROOT / "app" / "content.json"
src = p.read_text(encoding="utf-8")
if '"liveUrl"' in src:
    src = re.sub(r'"liveUrl":\s*"[^"]*"', f'"liveUrl": "{url}"', src, count=1)
else:
    src = src.replace('"version": "1.0",', f'"version": "1.0",\n    "liveUrl": "{url}",', 1)
p.write_text(src, encoding="utf-8")

for f in (ROOT / "README.md", ROOT / "deliverables" / "REPORT_NOTES.md", ROOT / "deliverables" / "README.md"):
    if f.exists():
        t = f.read_text(encoding="utf-8")
        f.write_text(t.replace("{{LIVE_URL}}", url), encoding="utf-8")
print("live URL set to", url)
