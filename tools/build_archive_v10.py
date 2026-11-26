"""Build app/v1.0/: the v1.0 app from git tag v1.0, served at .../five-minutes-together/v1.0/ for comparison.

Every file is byte-identical to the tag (audio included) except three, changed only as the v1.1 brief says:
  index.html   – no <link rel="manifest">, a slim "archived version" banner linking to ../
  js/main.js   – the service-worker registration is removed (v1.0's sw.js deletes other "fmt-" caches,
                 so it must never run next to v1.1)
  js/store.js  – localStorage keys prefixed "fmt10." so progress, settings and answers never mix with v1.1

    python tools/build_archive_v10.py
"""
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "app" / "v1.0"
GIT = os.path.expandvars(r"%LOCALAPPDATA%\Programs\fmt-tools\git\cmd\git.exe")
if not Path(GIT).exists():
    GIT = "git"

BANNER = (
    '<div id="archive-banner" style="position:relative;z-index:50;background:#24434F;color:#fff;font:600 15px/1.45 '
    "'Baloo Bhaijaan 2','Andika',sans-serif;padding:8px 14px;text-align:center\">"
    '<a href="../" style="color:#fff;text-decoration:underline;display:inline-block;min-height:44px;padding:6px 4px">'
    '<span lang="ar" dir="rtl">نسخة مؤرشفة: الإصدار 1.0 للمقارنة فقط – الإصدار الحالي ←</span><br>'
    '<span lang="en" dir="ltr">Archived version 1.0, for comparison only – current version →</span></a></div>\n'
)


def git_bytes(spec: str) -> bytes:
    return subprocess.run([GIT, "show", spec], capture_output=True, check=True, cwd=ROOT).stdout


def main() -> None:
    files = subprocess.run([GIT, "ls-tree", "-r", "--name-only", "v1.0", "app/"], capture_output=True, text=True,
                           check=True, cwd=ROOT).stdout.split()
    if OUT.exists():
        shutil.rmtree(OUT)
    changed = {}
    for f in files:
        data = git_bytes(f"v1.0:{f}")
        rel = f[len("app/"):]
        dest = OUT / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if rel == "index.html":
            t = data.decode("utf-8")
            before = t
            t = t.replace('<link rel="manifest" href="manifest.webmanifest">\n', "")
            t = t.replace('<body>\n', '<body>\n' + BANNER, 1)
            assert t != before and "manifest.webmanifest" not in t and "archive-banner" in t
            data = t.encode("utf-8")
            changed[rel] = "removed the manifest link; added the archive banner"
        elif rel == "js/main.js":
            t = data.decode("utf-8")
            start = t.index("function registerServiceWorker() {")
            end = t.index("\nasync function boot()")
            t = t[:start] + ("function registerServiceWorker() {\n"
                             "  // archived v1.0: no service worker (v1.0's sw.js would delete the v1.1 cache)\n}\n") + t[end:]
            assert "serviceWorker.register" not in t
            data = t.encode("utf-8")
            changed[rel] = "service-worker registration removed"
        elif rel == "js/store.js":
            t = data.decode("utf-8")
            assert "const NS = 'fmt1.';" in t
            t = t.replace("const NS = 'fmt1.';", "const NS = 'fmt10.'; // archived v1.0: separate storage from v1.1")
            data = t.encode("utf-8")
            changed[rel] = "localStorage prefix fmt10."
        dest.write_bytes(data)
    # proof: every other file is byte-identical to the tag
    same = sum(1 for f in files if f[len("app/"):] not in changed
               and hashlib.sha256((OUT / f[len("app/"):]).read_bytes()).digest() == hashlib.sha256(git_bytes(f"v1.0:{f}")).digest())
    (OUT / "ARCHIVE.json").write_text(json.dumps({"source": "git tag v1.0", "files": len(files), "byte_identical": same,
                                                  "changed": changed}, indent=1), encoding="utf-8")
    print(f"app/v1.0: {len(files)} files from tag v1.0; {same} byte-identical; changed: {list(changed)}")


if __name__ == "__main__":
    main()
