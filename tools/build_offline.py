"""Build deliverables/offline-backup.html: the whole app in ONE file that opens with a double-click
(file://, no server, no internet). ES modules are bundled into one script, and CSS, fonts,
content.json, every MP3 and the QR code are embedded (base64 data).

    python tools/build_offline.py
"""
import base64
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
OUT = ROOT / "deliverables" / "offline-backup.html"

IMPORT_RE = re.compile(r"^import\s+(?P<what>[\s\S]+?)\s+from\s+'(?P<src>[^']+)';[ \t]*$", re.M)
EXPORT_DECL = re.compile(r"^export\s+(async\s+function|function|const|let|class)\s+([A-Za-z_$][\w$]*)", re.M)
EXPORT_LIST = re.compile(r"^export\s*\{([^}]*)\};?\s*$", re.M)


def mod_id(path: Path) -> str:
    return "__M_" + re.sub(r"\W", "_", path.relative_to(APP / "js").as_posix()[:-3])


def bundle(entry: Path) -> str:
    order, seen = [], set()

    def visit(p: Path):
        if p in seen:
            return
        seen.add(p)
        src = p.read_text(encoding="utf-8")
        for m in IMPORT_RE.finditer(src):
            visit((p.parent / m.group("src")).resolve())
        order.append(p)

    visit(entry.resolve())
    out = []
    for p in order:
        src = p.read_text(encoding="utf-8")
        header = []
        for m in IMPORT_RE.finditer(src):
            dep = mod_id((p.parent / m.group("src")).resolve())
            what = m.group("what").strip()
            if what.startswith("* as "):
                header.append(f"const {what[5:].strip()} = {dep};")
            else:
                names = what.strip("{} ").split(",")
                parts = []
                for n in names:
                    n = n.strip()
                    if not n:
                        continue
                    if " as " in n:
                        a, b = [x.strip() for x in n.split(" as ")]
                        parts.append(f"{a}: {b}")
                    else:
                        parts.append(n)
                header.append(f"const {{ {', '.join(parts)} }} = {dep};")
        body = IMPORT_RE.sub("", src)
        exports = [m.group(2) for m in EXPORT_DECL.finditer(body)]
        for m in EXPORT_LIST.finditer(body):
            exports += [x.strip().split(" as ")[0] for x in m.group(1).split(",") if x.strip()]
        body = EXPORT_DECL.sub(lambda m: f"{m.group(1)} {m.group(2)}", body)
        body = EXPORT_LIST.sub("", body)
        out.append(f"// ---- {p.relative_to(APP).as_posix()}\nconst {mod_id(p)} = (function () {{\n" + "\n".join(header) + "\n" + body +
                   f"\nreturn {{ {', '.join(sorted(set(exports)))} }};\n}})();\n")
    return "\n".join(out)


def b64(p: Path) -> str:
    return base64.b64encode(p.read_bytes()).decode("ascii")


def main():
    css = (APP / "css" / "app.css").read_text(encoding="utf-8")
    css = re.sub(r'url\("\.\./fonts/([^"]+)"\)', lambda m: f'url("data:font/woff2;base64,{b64(APP / "fonts" / m.group(1))}")', css)
    manifest = json.loads((APP / "audio" / "manifest.json").read_text(encoding="utf-8"))
    audio = {}
    for f in sorted((APP / "audio").rglob("*.mp3")):
        audio[f.relative_to(APP).as_posix()] = b64(f)
    qr = APP / "img" / "qr-code.svg"
    embed = {
        "content": json.loads((APP / "content.json").read_text(encoding="utf-8")),
        "manifest": manifest,
        "audio": audio,
        "qr": ("data:image/svg+xml;base64," + b64(qr)) if qr.exists() else None,
    }
    js = bundle(APP / "js" / "main.js")
    html = (APP / "index.html").read_text(encoding="utf-8")
    html = re.sub(r'<meta http-equiv="Content-Security-Policy"[^>]*>\n?', "", html)
    html = re.sub(r'<link rel="(manifest|apple-touch-icon|preload|modulepreload)"[^>]*>\n?', "", html)
    html = re.sub(r'<link rel="icon" href="icons/icon-192.png"[^>]*>\n?', "", html)
    html = html.replace('<link rel="icon" href="icons/favicon.svg" type="image/svg+xml">',
                        f'<link rel="icon" href="data:image/svg+xml;base64,{b64(APP / "icons" / "favicon.svg")}" type="image/svg+xml">')
    html = html.replace('<link rel="stylesheet" href="css/app.css">', f"<style>\n{css}\n</style>")
    html = html.replace('<script nomodule src="js/old-browser.js"></script>', "")
    data = json.dumps(embed, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html = html.replace('<script type="module" src="js/main.js"></script>',
                        "<script>window.__FMT_EMBED__ = " + data + ";</script>\n<script>\n(function () {\n" + js.replace("</script", "<\\/script") + "\n})();\n</script>")
    html = html.replace("<title>", "<!-- Offline backup: the whole app in one file. Opens with a double-click; nothing is sent anywhere. -->\n<title>", 1)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size / 1024 / 1024:.2f} MB, {len(audio)} audio clips embedded)")


if __name__ == "__main__":
    main()
