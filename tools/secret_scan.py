"""Secret scan (brief §4.2, §11 test 9) – run before every commit; the git pre-commit hook runs it too.

    python tools/secret_scan.py            # tracked + staged files, deliverables/ and the build logs
    python tools/secret_scan.py --staged   # staged files only (pre-commit hook)

Looks for the ElevenLabs key itself (read from .env at run time, never printed) and for any string
matching sk_[A-Za-z0-9]{20,}. Also checks that .env is gitignored and not tracked.
Prints only file names and line numbers, never the match. Exit code 1 if anything is found.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERN = re.compile(rb"sk_[A-Za-z0-9]{20,}")
EXTRA_DIRS = ["deliverables", "tools/.audio-cache/eleven", "tools/studio"]   # local deliverables and logs (not in git)
EXTRA_FILES = ["tools/audio_build_log.json", "tools/audio_verification.json", "tools/voices.json"]
SKIP_SUFFIX = {".mp3", ".wav", ".woff2", ".png", ".jpg", ".ico", ".onnx", ".bin"}


def git() -> str:
    return shutil.which("git") or str(Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "fmt-tools" / "git" / "cmd" / "git.exe")


def run_git(*args: str) -> str:
    return subprocess.run([git(), *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8").stdout


def env_key() -> bytes | None:
    env = ROOT / ".env"
    if not env.exists():
        return None
    for line in env.read_text(encoding="utf-8-sig").splitlines():
        if line.strip().startswith("ELEVENLABS_API_KEY="):
            v = line.split("=", 1)[1].strip().strip('"').strip("'")
            return v.encode("utf-8") if len(v) >= 16 else None
    return None


def files(staged_only: bool) -> list[Path]:
    names = set(run_git("diff", "--cached", "--name-only", "--diff-filter=ACMR").splitlines())
    if not staged_only:
        names |= set(run_git("ls-files").splitlines())
        for d in EXTRA_DIRS:
            p = ROOT / d
            if p.exists():
                names |= {str(f.relative_to(ROOT)).replace("\\", "/") for f in p.rglob("*") if f.is_file()}
        names |= {f for f in EXTRA_FILES if (ROOT / f).exists()}
    return sorted(ROOT / n for n in names if n and n != ".env" and (ROOT / n).is_file())


def scan(paths: list[Path], key: bytes | None) -> list[str]:
    hits = []
    for p in paths:
        if p.suffix.lower() in SKIP_SUFFIX and p.stat().st_size > 0:
            data = p.read_bytes()       # binary: still checked for the key itself, without line numbers
            if (key and key in data) or PATTERN.search(data):
                hits.append(f"{p.relative_to(ROOT)} (binary)")
            continue
        for i, line in enumerate(p.read_bytes().splitlines(), 1):
            if (key and key in line) or PATTERN.search(line):
                hits.append(f"{p.relative_to(ROOT)}:{i}")
    return hits


def main() -> int:
    staged_only = "--staged" in sys.argv
    problems = []
    if run_git("ls-files", ".env").strip():
        problems.append(".env is TRACKED by git")
    if subprocess.run([git(), "check-ignore", "-q", ".env"], cwd=ROOT).returncode != 0:
        problems.append(".env is NOT gitignored")
    paths = files(staged_only)
    hits = scan(paths, env_key())
    for h in hits:
        problems.append(f"possible API key in {h}")
    if problems:
        print("SECRET SCAN FAILED – commit aborted:\n  " + "\n  ".join(problems))
        return 1
    print(f"Secret scan OK: {len(paths)} files checked ({'staged' if staged_only else 'tracked, staged, deliverables and logs'}); "
          f"no API key and no sk_… string; .env is gitignored and untracked.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
