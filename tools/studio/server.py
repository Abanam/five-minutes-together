r"""Local studio page for the v1.1 audio: http://127.0.0.1:8770/ (this PC only; nothing here is published).

    .venv\Scripts\python.exe tools\studio\server.py [--no-browser]

Tabs: "Voices" (choose the English and the Arabic voice; results come from tools/audition.py) and
"Record" (the six letter sounds; extra cards appear only when needed). Every take is processed and
checked here: FFmpeg to 24 kHz mono + 70 Hz high-pass, trim, normalise, fades, then describe_phoneme +
check_phoneme with the UNCHANGED RULES. Takes are stored in recordings/ (gitignored); the chosen take
in recordings/chosen/ph-<letter>.wav. Standard library http.server only; it listens on 127.0.0.1.
"""
from __future__ import annotations

import json
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import numpy as np  # noqa: E402
import soundfile as sf  # noqa: E402

import audition  # noqa: E402
import eleven  # noqa: E402
import letters_v11  # noqa: E402
import make_audio_v11 as V  # noqa: E402
from audio_analysis import RULES, trim  # noqa: E402

PORT = 8770
REC = ROOT / "recordings"
TAKES = REC / "takes"
CHOSEN = REC / "chosen"
MAX_TAKES = 5
SR = V.SR
TEXTS = json.loads((HERE / "texts.json").read_text(encoding="utf-8"))
MEDIA_DIRS = [ROOT / "tools" / ".audio-cache", REC]
STATIC = {"/studio/": (HERE, {".html", ".js", ".css", ".json"}),
          "/app/": (ROOT / "app", {".js", ".css", ".woff2", ".svg", ".mp3", ".json", ".png"})}
TYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8",
         ".json": "application/json; charset=utf-8", ".mp3": "audio/mpeg", ".wav": "audio/wav", ".woff2": "font/woff2",
         ".svg": "image/svg+xml", ".png": "image/png"}
LOCK = threading.Lock()
JOB = {"state": "idle", "error": None, "what": None}


# ------------------------------------------------------------------ items and takes
def items() -> list[dict]:
    c = V.load_content()
    out = [{"item": f"ph-{s}", "kind": "phoneme", "letter": s, "ipa": m["ipa"], "keywords": m["keywords"]}
           for s, m in c["sounds"].items()]
    return out + audition.load_state().get("record_extra", [])


def takes(item: str) -> list[dict]:
    rows = [json.loads(p.read_text(encoding="utf-8")) for p in TAKES.glob(f"{item}-*.json")]
    return sorted((r for r in rows if r.get("item") == item), key=lambda r: r["take"])


def chosen(item: str) -> dict | None:
    p = CHOSEN / f"{item}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def media_url(p: Path) -> str:
    return "/media/" + str(p.resolve().relative_to(ROOT)).replace("\\", "/")


def classify(letter: str, problems: list[str], d: dict) -> list[str]:
    """check_phoneme's problems -> the message keys of the brief (§6)."""
    lo, hi = RULES[letter]["dur"]
    keys = []
    for p in problems:
        if p.startswith("duration"):
            keys.append("short" if d["duration"] < (lo + hi) / 2 else "long")
        elif p.startswith("voiced stretch"):
            keys.append("vowel_added")
        elif p.startswith("voiced") and ">" in p:
            keys.append("s_voiced")
        elif p.startswith("voiced") and "<" in p:
            keys.append("weak")
        elif p.startswith("centroid") and "<" in p:
            keys.append("muffled")
        elif p.startswith("centroid") and ">" in p:
            keys.append("hissy")
        elif p.startswith("low-band"):
            keys.append("not_n")
        elif "not measurable" in p:
            keys.append("unclear")
        elif p.startswith(("F1", "F2")) and "moves" in p:
            keys.append("moves")
        elif p.startswith(("F1", "F2")):
            keys.append("formant")
        elif p.startswith("starts with"):
            keys.append("vowel_start")
        else:
            keys.append("unclear")
    return list(dict.fromkeys(keys))


def message(key: str) -> str:
    return TEXTS["messages"].get(key) or TEXTS["extra_messages_not_in_brief"][key]


def new_take(item: str, raw: bytes) -> tuple[int, Path]:
    TAKES.mkdir(parents=True, exist_ok=True)
    old = takes(item)
    keep = chosen(item)
    while len(old) >= MAX_TAKES:        # only the last 5 takes are kept (never the chosen one)
        drop = next((t for t in old if not keep or t["take"] != keep["take"]), None)
        if drop is None:
            break
        k = drop["take"]
        for name in (f"{item}-{k}-raw.wav", f"{item}-{k}-24k.wav", f"{item}-{k}-check.wav", f"{item}-{k}-check.mp3", f"{item}-{k}.json"):
            (TAKES / name).unlink(missing_ok=True)
        old = takes(item)
    n = (max((t["take"] for t in old), default=0)) + 1
    rawp = TAKES / f"{item}-{n}-raw.wav"
    rawp.write_bytes(raw)
    return n, rawp


def process_phoneme(item: str, letter: str, raw: bytes) -> dict:
    n, rawp = new_take(item, raw)
    y_raw, _ = sf.read(rawp, dtype="float32", always_2d=True)
    loud = int(np.sum(np.abs(y_raw) >= 0.999)) > 10
    y24 = V.prepare_take(rawp, TAKES / f"{item}-{n}-24k.wav")
    rec = {"item": item, "kind": "phoneme", "letter": letter, "take": n, "ok": False, "problems": [], "messages": []}
    if y24.size == 0 or float(np.max(np.abs(y24))) < 0.003 or len(trim(y24, SR)) < int(0.03 * SR):
        rec["problems"], keys = ["no sound"], ["unclear"]
    else:
        shaped = V.shape_phoneme(y24, letter)
        sf.write(TAKES / f"{item}-{n}-check.wav", shaped, SR, subtype="PCM_16")
        rec["url"] = media_url(TAKES / f"{item}-{n}-check.wav")
        d, probs = V.check_take(shaped, letter)
        rec["measures"] = {k: (round(v, 3) if isinstance(v, float) else v) for k, v in d.items()}
        rec["problems"] = probs
        keys = classify(letter, probs, d)
    if loud:
        keys = ["loud"] + keys
        rec["problems"].append("raw take clipped (more than 10 samples at full scale)")
    rec["message_keys"] = keys
    rec["messages"] = [message(k) for k in keys]
    rec["ok"] = not rec["problems"]
    (TAKES / f"{item}-{n}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    return rec


def process_word(item: str, word: str, raw: bytes) -> dict:
    """A word that failed twice with ElevenLabs (brief §7.2): onset checks + Whisper, like the generated words."""
    n, rawp = new_take(item, raw)
    y24 = V.prepare_take(rawp, TAKES / f"{item}-{n}-24k.wav")
    y = V.M.normalise(V.M.fade(trim(y24, SR, top_db=45, pad_ms=12), 6, 30))
    mp3 = TAKES / f"{item}-{n}-check.mp3"
    V.M.to_mp3(y, mp3, 64)
    back = trim(V.decode(mp3), SR)
    first = V.first_sound(word)
    onset = bool(V.M.onset_ok(back, first) and V.verify_onset(back, first))
    heard = V.whisper(mp3, "en", V.ENGLISH_PROMPT)
    match, exact = V.whisper_word_ok(heard, word)
    rec = {"item": item, "kind": "word", "word": word, "take": n, "url": media_url(mp3), "heard": heard, "onset_ok": onset,
           "match": match, "ok": bool(onset and match), "problems": [], "messages": []}
    if not match:
        rec["problems"].append(f"Whisper heard {heard!r}")
        rec["messages"].append(f"سمع البرنامج: «{heard}». قل الكلمة مرة واحدة بوضوح.")
    if not onset:
        rec["problems"].append("unclean onset")
        rec["messages"].append("بداية الكلمة غير نظيفة؛ ابدأ بالصوت الأول مباشرة.")
    (TAKES / f"{item}-{n}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    return rec


def use_take(item: str, n: int) -> dict:
    rec = next((t for t in takes(item) if t["take"] == n), None)
    if rec is None or not rec["ok"]:
        raise ValueError("only a take marked ✓ can be used")
    CHOSEN.mkdir(parents=True, exist_ok=True)
    (CHOSEN / f"{item}.wav").write_bytes((TAKES / f"{item}-{n}-24k.wav").read_bytes())
    (CHOSEN / f"{item}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    return rec


# ------------------------------------------------------------------ state for the page
def page_state() -> dict:
    s = audition.load_state()
    its = items()
    return {"texts": TEXTS, "items": its, "takes": {i["item"]: takes(i["item"]) for i in its},
            "chosen": {i["item"]: chosen(i["item"]) for i in its}, "english": s.get("english"), "arabic": s.get("arabic"),
            "letters": s.get("letters"), "letters_voice": s.get("letters_voice"), "job": JOB, "max_takes": MAX_TAKES}


def run_job(what: str, fn) -> None:
    def target():
        JOB.update(state="running", error=None, what=what)
        try:
            fn()
            JOB.update(state="done")
        except BaseException as e:  # noqa: BLE001 – shown in the page, key masked
            JOB.update(state="error", error=eleven.mask(f"{type(e).__name__}: {e}"))
    threading.Thread(target=target, daemon=True).start()


class Handler(BaseHTTPRequestHandler):
    server_version = "fmt-studio"

    def log_message(self, fmt, *args):  # quiet, except errors
        if args and str(args[1])[:1] in "45":
            sys.stderr.write("%s %s\n" % (self.command, fmt % args))

    def send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, obj, code: int = 200) -> None:
        self.send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"), TYPES[".json"])

    def send_file(self, p: Path) -> None:
        self.send(200, p.read_bytes(), TYPES.get(p.suffix.lower(), "application/octet-stream"))

    def do_GET(self):
        path = unquote(urlparse(self.path).path)
        if path in ("/", "/index.html"):
            return self.send_file(HERE / "index.html")
        if path == "/api/state":
            return self.send_json(page_state())
        if path.startswith("/media/"):
            p = (ROOT / path[len("/media/"):]).resolve()
            if p.suffix.lower() in (".mp3", ".wav") and p.is_file() and any(p.is_relative_to(d.resolve()) for d in MEDIA_DIRS):
                return self.send_file(p)
            return self.send(404, b"not found", "text/plain")
        for prefix, (base, exts) in STATIC.items():
            if path.startswith(prefix):
                p = (base / path[len(prefix):]).resolve()
                if p.suffix.lower() in exts and p.is_file() and p.is_relative_to(base.resolve()):
                    return self.send_file(p)
        self.send(404, b"not found", "text/plain")

    def do_POST(self):
        u = urlparse(self.path)
        n = int(self.headers.get("Content-Length") or 0)
        if n > 30 * 1024 * 1024:
            return self.send(413, b"too large", "text/plain")
        body = self.rfile.read(n) if n else b""
        try:
            if u.path == "/api/take":
                item = parse_qs(u.query).get("item", [""])[0]
                it = next((i for i in items() if i["item"] == item), None)
                if it is None:
                    return self.send_json({"error": "unknown item"}, 400)
                with LOCK:
                    rec = process_phoneme(item, it["letter"], body) if it["kind"] == "phoneme" else process_word(item, it["word"], body)
                    try:   # the browser's actual microphone settings (echo cancellation etc. must be off)
                        rec["mic"] = json.loads(parse_qs(u.query).get("mic", ["{}"])[0])
                    except ValueError:
                        rec["mic"] = None
                    (TAKES / f"{item}-{rec['take']}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
                return self.send_json(rec)
            data = json.loads(body.decode("utf-8") or "{}")
            if u.path == "/api/use":
                with LOCK:
                    use_take(data["item"], int(data["take"]))
                return self.send_json(page_state())
            if u.path == "/api/english":
                with LOCK:
                    s = audition.load_state()
                    if data["voice_id"] not in [v["voice_id"] for v in s["english"]["voices"]]:
                        return self.send_json({"error": "unknown voice"}, 400)
                    s["english"]["chosen"] = data["voice_id"]
                    audition.save_state(s)
                    audition.write_voices_json(s)
                return self.send_json(page_state())
            if u.path == "/api/arabic":
                if JOB["state"] == "running":
                    return self.send_json({"error": "busy"}, 409)
                with LOCK:
                    s = audition.load_state()
                    s["arabic"]["chosen_preview"] = int(data["preview"])
                    s["arabic"]["approved"] = False
                    s["arabic"].pop("lines", None)
                    audition.save_state(s)
                run_job("arabic-lines", lambda: audition.arabic_lines())
                return self.send_json(page_state())
            if u.path == "/api/letter":              # choose one of the ElevenLabs letter-sound candidates
                with LOCK:
                    s = letters_v11.choose(str(data["letter"]), int(data["n"]))
                    audition.save_state(s)
                return self.send_json(page_state())
            if u.path == "/api/arabic-voice":        # website mode: the voice ID made on elevenlabs.io
                vid = str(data.get("voice_id", "")).strip()
                if not vid.isalnum() or not 10 <= len(vid) <= 40:
                    return self.send_json({"error": "this does not look like a voice ID"}, 400)
                if JOB["state"] == "running":
                    return self.send_json({"error": "busy"}, 409)
                run_job("arabic-lines", lambda: audition.arabic_lines_for(vid))
                return self.send_json(page_state())
            if u.path == "/api/arabic-approve":
                with LOCK:
                    s = audition.load_state()
                    s["arabic"]["approved"] = bool(data.get("ok"))
                    audition.save_state(s)
                    audition.write_voices_json(s)
                return self.send_json(page_state())
        except Exception as e:  # noqa: BLE001
            return self.send_json({"error": eleven.mask(f"{type(e).__name__}: {e}")}, 500)
        self.send(404, b"not found", "text/plain")


def main() -> None:
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://127.0.0.1:{PORT}/"
    print(f"Studio running at {url}  (Ctrl+C to stop)")
    if "--no-browser" not in sys.argv:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
