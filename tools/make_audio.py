"""Generate every audio clip the app uses, from app/content.json.

    .venv/Scripts/python.exe tools/make_audio.py

English  : Kokoro-82M v1.0 (Apache-2.0) via kokoro-onnx, voice af_heart, IPA input.
Phonemes : pure letter SOUNDS from IPA input (never letter names):
             /s/      frication cut from Kokoro "ðə sˈʌn", lengthened by noise grains
             /t/ /p/  burst + aspiration cut from Kokoro "ðə tˈæp" / "ðə pˈʌn" (cut before voicing)
             /æ/ /ɪ/  steady vowel frames (selected by formants) from Kokoro carrier words, sustained
             /n/      Kokoro "nnn"
           every candidate must pass audio_analysis.check_phoneme(); otherwise espeak-ng
           phoneme mode ([[...]]) is used; if that also fails the build stops.
Blends   : phoneme clips joined with 0.4 s gaps (p … a … n).
Arabic   : Meta MMS-TTS (facebook/mms-tts-ara, CC BY-NC 4.0), phrase by phrase, with real
           pauses; English sounds/words in a text ({ph:s}, {w:sat}) are spliced in from the
           English clips so the Arabic voice never says a letter name.
All clips: silence trimmed, loudness-normalised (active RMS), mono, MP3 via ffmpeg.
Writes app/audio/en/*.mp3, app/audio/ar/*.mp3, app/audio/manifest.json, tools/audio_build_log.json
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

sys.path.insert(0, str(Path(__file__).parent))
from audio_analysis import (_runs, check_phoneme, describe_phoneme, extract_fricative,  # noqa: E402
                            extract_stop, frame_labels, trim, voicing)

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
AUD = APP / "audio"
CACHE = ROOT / "tools" / ".audio-cache"
MODELS = Path.home() / ".cache" / "fmt-models"
MMS_PY = ROOT / ".venv-mms" / "Scripts" / "python.exe"
SR = 24000
VOICE = "af_heart"
TARGET_DB = -20.0
PEAK_DB = -1.0
rng = np.random.default_rng(2024)

WORD_IPA = {
    # CVC words
    "at": "ˈæt", "sat": "sˈæt", "pat": "pˈæt", "tap": "tˈæp", "it": "ˈɪt", "sit": "sˈɪt",
    "sip": "sˈɪp", "tip": "tˈɪp", "pit": "pˈɪt", "in": "ˈɪn", "pin": "pˈɪn", "tin": "tˈɪn",
    "nap": "nˈæp", "pan": "pˈæn",
    # keywords
    "sun": "sˈʌn", "sand": "sˈænd", "ant": "ˈænt", "apple": "ˈæpᵊl", "tent": "tˈɛnt",
    "tomato": "təmˈAɾO", "palm": "pˈɑm", "pen": "pˈɛn", "insect": "ˈɪnsɛkt", "ink": "ˈɪŋk",
    "net": "nˈɛt", "nest": "nˈɛst",
    # used only inside the Arabic tip for /a/ ("كما في cat")
    "cat": "kˈæt",
}


# ----------------------------------------------------------------- helpers
def fnv1a(s: str) -> str:
    """32-bit FNV-1a over UTF-16 code units (same as the app's JS)."""
    h = 0x811C9DC5
    b = unicodedata.normalize("NFC", s).encode("utf-16-le")
    for i in range(0, len(b), 2):
        h ^= b[i] | (b[i + 1] << 8)
        h = (h * 0x01000193) & 0xFFFFFFFF
    return f"{h:08x}"


AR_DIAC = re.compile("[ً-ْٰـۡ]")


def strip_diacritics(s: str) -> str:
    return AR_DIAC.sub("", s)


def active_rms_db(y: np.ndarray) -> float:
    if y.size == 0:
        return -120.0
    frame = int(SR * 0.02)
    n = max(1, len(y) // frame)
    fr = y[: n * frame].reshape(n, frame) if len(y) >= frame else y.reshape(1, -1)
    r = np.sqrt(np.mean(fr ** 2, axis=1) + 1e-12)
    act = r[r > r.max() * 10 ** (-30 / 20)]
    return float(20 * np.log10(np.sqrt(np.mean(act ** 2)) + 1e-12))


def normalise(y: np.ndarray, target_db: float = TARGET_DB) -> np.ndarray:
    y = y.astype(np.float64)
    y = y - np.mean(y)
    g = 10 ** ((target_db - active_rms_db(y)) / 20)
    y = y * g
    peak = np.max(np.abs(y)) + 1e-12
    lim = 10 ** (PEAK_DB / 20)
    if peak > lim:
        y = y * (lim / peak)
    return y.astype(np.float32)


def fade(y: np.ndarray, a_ms: float = 8, r_ms: float = 25) -> np.ndarray:
    y = y.copy()
    a, r = int(SR * a_ms / 1000), int(SR * r_ms / 1000)
    if len(y) > a + r:
        y[:a] *= np.linspace(0, 1, a)
        y[-r:] *= np.linspace(1, 0, r)
    return y


def silence(sec: float) -> np.ndarray:
    return np.zeros(int(SR * sec), np.float32)


def to_mp3(y: np.ndarray, path: Path, kbps: int, out_sr: int = SR) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        wav = Path(td) / "x.wav"
        sf.write(wav, y, SR, subtype="PCM_16")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-map_metadata", "-1",
                        "-ac", "1", "-ar", str(out_sr), "-codec:a", "libmp3lame", "-b:a", f"{kbps}k", str(path)],
                       check=True)


# ----------------------------------------------------------------- Kokoro
_kokoro = None


def kokoro():
    global _kokoro
    if _kokoro is None:
        from kokoro_onnx import Kokoro
        _kokoro = Kokoro(str(MODELS / "kokoro-v1.0.onnx"), str(MODELS / "voices-v1.0.bin"))
    return _kokoro


def ko(ph: str, speed: float = 0.9, trim_audio: bool = True) -> np.ndarray:
    y, sr = kokoro().create(ph, voice=VOICE, speed=speed, is_phonemes=True, trim=trim_audio)
    assert sr == SR
    return np.asarray(y, np.float32)


def ko_text(text: str, speed: float = 0.95) -> np.ndarray:
    y, sr = kokoro().create(text, voice=VOICE, speed=speed, lang="en-us")
    assert sr == SR
    return np.asarray(y, np.float32)


def _split_after_pause(y: np.ndarray, near: float = 0.5, min_ms: int = 150):
    """Return the audio after the pause (≥ min_ms of near-silence) closest to `near` × length."""
    db, _, _, hop = frame_labels(y, SR, 10.0)
    n = len(db)
    quiet = _runs(db < -40)
    # the gap between the two copies: the longest quiet stretch in the middle part of the clip
    mids = [r for r in quiet if r[1] - r[0] >= 8 and 0.25 * n < (r[0] + r[1]) / 2 < 0.75 * n]
    if mids:
        a, b = max(mids, key=lambda r: r[1] - r[0])
    else:
        runs = [r for r in quiet if r[1] - r[0] >= min_ms // 10 and r[0] > 8 and r[1] < n - 8]
        if not runs:
            return None
        a, b = min(runs, key=lambda r: abs((r[0] + r[1]) / 2 - near * n))
    return y[max(0, b * hop - int(SR * 0.012)):]


def ko_clean(ph: str, speed: float = 0.9) -> np.ndarray:
    """Kokoro adds a short voiced 'uh' at the very start of an utterance. We say the item twice
    ("sˈæt. sˈæt.") and keep the second one, which starts cleanly after a real pause."""
    for sep in (". ", "… ", ", ", "! "):
        y = ko(f"{ph}{sep}{ph}.", speed, True)
        second = _split_after_pause(y, 0.5)
        if second is not None and len(second) >= SR * 0.15:
            return trim(second, SR)
    raise RuntimeError(f"could not isolate the second '{ph}'")


def _frame_f2(y: np.ndarray):
    fr, hop = _frame_formants(y)
    return [(f2 if v and d > -30 else None) for f1, f2, d, v in fr], hop


def strip_onset(y: np.ndarray, first: str):
    """Remove Kokoro's short voiced start-up sound before the first real sound of a word."""
    y = trim(y, SR, top_db=45, pad_ms=5)
    db, v, cen, hop = frame_labels(y, SR, 10.0)
    n = len(db)
    aud = next((i for i in range(n) if db[i] > -35), 0)
    cut = None
    if first == "s":
        cut = next((i for i in range(aud, n) if not v[i] and cen[i] > 3000 and db[i] > -35), None)
        if cut is not None:
            cut = max(0, cut * hop - int(SR * 0.005))
    elif first in ("t", "p"):
        i = aud
        while i < n and v[i]:
            i += 1
        if i < n and i > aud:
            cut = max(0, i * hop - int(SR * 0.012))
        elif i == aud:
            cut = aud * hop
    elif first in ("a", "i"):
        f2, h2 = _frame_f2(y)
        j = next((k for k in range(len(f2) - 1) if f2[k] and f2[k + 1] and f2[k] > 1400 and f2[k + 1] > 1400), None)
        if j is not None:
            cut = j * h2
    if cut is None:
        return None
    # vowels get a softer 25 ms attack so the cut does not sound like a consonant
    out = fade(y[cut:].copy(), 25 if first in ("a", "i") else 6, 25)
    return out if len(out) > SR * 0.15 else None


def onset_ok(y: np.ndarray, first: str) -> bool:
    db, v, cen, _ = frame_labels(y, SR, 10.0)
    aud = [i for i in range(len(db)) if db[i] > -35][:6]
    if first in ("s", "t", "p"):
        return sum(1 for i in aud[:4] if v[i]) == 0
    if first in ("a", "i"):
        f2, _ = _frame_f2(y[: int(SR * 0.12)])
        vals = [x for x in f2 if x is not None][:3]
        return bool(vals) and float(np.median(vals)) > 1400
    return True


_wm = None


def whisper_hears(y: np.ndarray, word: str) -> tuple[bool, str]:
    global _wm
    from faster_whisper import WhisperModel
    if _wm is None:
        _wm = WhisperModel("small", device="cpu", compute_type="int8", download_root=str(MODELS / "whisper"))
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "w.wav"
        sf.write(p, y, SR)
        segs, _ = _wm.transcribe(str(p), language="en", beam_size=5, without_timestamps=True,
                                 initial_prompt="A single English word for children learning to read:")
        hyp = " ".join(s.text for s in segs).strip()
    clean = re.sub(r"[^a-z0-9 ]", "", hyp.lower()).strip()
    same = {"sun": {"son"}, "ant": {"and", "aunt"}, "ink": {"inc"}, "tin": {"ten", "10"}, "palm": {"pom", "pam", "bomb"}, "in": {"inn"}}
    ok_set = {word} | same.get(word, set())
    toks = clean.split()
    # exact, a same-sound spelling, or the word inside a short transcript ("to be sat")
    return (clean in ok_set or (len(toks) <= 4 and any(t in ok_set for t in toks))), hyp


def clean_word(word: str, ipa: str, first: str, log: dict) -> np.ndarray:
    """Pick the first candidate with a clean onset that Whisper hears as the intended word."""
    tried = []
    best = None
    for speed in (0.9, 0.85, 0.8):
        cands = []
        solo = ko(ipa, speed, False)
        if first != "n":
            cands.append(("solo, start-up sound removed", strip_onset(solo, first)))
        try:
            cands.append(("second of two", ko_clean(ipa, speed)))
        except RuntimeError:
            pass
        for how, y in cands:
            if y is None:
                continue
            ok_on = bool(onset_ok(y, first))
            heard_ok, hyp = whisper_hears(y, word)
            tried.append({"how": how, "speed": speed, "onset_ok": ok_on, "whisper": hyp})
            if ok_on and heard_ok:
                log["words"][word] = {"method": how, "speed": speed, "whisper": hyp, "whisper_match": True, "tried": len(tried)}
                return y
            if ok_on and best is None:
                best = (how, speed, hyp, y)
    if best:
        # clean onset confirmed acoustically; Whisper (unreliable on single words) heard something else
        how, speed, hyp, y = best
        log["words"][word] = {"method": how, "speed": speed, "whisper": hyp, "whisper_match": False, "tried": tried}
        return y
    log["words"][word] = {"method": "plain (no clean-onset candidate)", "whisper_match": False, "tried": tried}
    return trim(ko(ipa, 0.9), SR)


def ko_clean_phrase(ph: str, speed: float = 0.95) -> np.ndarray:
    """For sentences: a throw-away 'ðə.' takes the start-up artefact, we keep what follows the first pause."""
    y = ko("ðˈɪs… " + ph, speed, True)
    db, _, _, hop = frame_labels(y, SR, 10.0)
    runs = [r for r in _runs(db < -40) if r[1] - r[0] >= 8 and r[0] > 5 and r[0] < len(db) * 0.4]
    if not runs:
        return trim(ko(ph, speed, True), SR)  # could not split: keep the plain phrase
    b = runs[0][1]
    return trim(y[max(0, b * hop - int(SR * 0.012)):], SR)


# ----------------------------------------------------------------- phonemes
def stretch_noise(seg: np.ndarray, target: float) -> np.ndarray:
    core = seg[int(len(seg) * .15): int(len(seg) * .85)]
    g = int(SR * 0.04)
    h = g // 2
    n = int(target * SR)
    out = np.zeros(n + g)
    w = np.hanning(g)
    for i in range(0, n, h):
        s = int(rng.integers(0, max(1, len(core) - g)))
        out[i:i + g] += core[s:s + g] * w
    out = out[:n]
    a, r = int(SR * .035), int(SR * .10)
    out[:a] *= np.linspace(0, 1, a)
    out[-r:] *= np.linspace(1, 0, r) ** 1.5
    return out.astype(np.float32)


def _frame_formants(y: np.ndarray):
    """(F1, F2, dB, voiced) per 10 ms frame using the cepstral envelope."""
    win, hop, nfft = int(SR * .04), int(SR * .01), 4096
    fq = np.fft.rfftfreq(nfft, 1 / SR)
    cut = int(SR * .0018)
    db, v, _, _ = frame_labels(y, SR, 10.0)
    out = []
    for j, i in enumerate(range(0, max(0, len(y) - win), hop)):
        if j >= len(v):
            break
        f = y[i:i + win] * np.hanning(win)
        sp = np.abs(np.fft.rfft(f, nfft)) + 1e-9
        c = np.fft.irfft(np.log(sp))
        c[cut:len(c) - cut] = 0
        env = np.fft.rfft(c).real
        m1 = (fq >= 250) & (fq <= 1150)
        f1 = fq[np.argmax(np.where(m1, env, -1e9))]
        m2 = (fq >= max(f1 + 350, 850)) & (fq <= 3000)
        f2 = fq[np.argmax(np.where(m2, env, -1e9))]
        out.append((f1, f2, db[j], v[j]))
    return out, hop


VOWEL_BOX = {"a": ((750, 1150), (1650, 2300)), "i": ((300, 480), (2250, 2900))}


def steady_vowel(y: np.ndarray, letter: str):
    (f1lo, f1hi), (f2lo, f2hi) = VOWEL_BOX[letter]
    fr, hop = _frame_formants(y)
    ok = np.array([v and d > -18 and f1lo <= f1 <= f1hi and f2lo <= f2 <= f2hi for f1, f2, d, v in fr])
    # allow single-frame dropouts inside a run
    for i in range(1, len(ok) - 1):
        if not ok[i] and ok[i - 1] and ok[i + 1]:
            ok[i] = True
    runs = _runs(ok)
    if not runs:
        return None
    a, b = max(runs, key=lambda r: r[1] - r[0])
    if (b - a) * 10 < 70:
        return None
    return y[a * hop:(b + 2) * hop]


def sustain(seg: np.ndarray, target: float = 0.72) -> np.ndarray:
    """Lengthen a steady voiced segment by correlation-aligned, cross-faded looping."""
    # flatten slow amplitude changes so the loop does not pulse
    env = np.sqrt(np.convolve(seg ** 2, np.ones(int(SR * .03)) / int(SR * .03), mode="same") + 1e-9)
    s = seg / env * np.median(env)
    xf = int(SR * 0.025)
    out = s.copy()
    n = int(target * SR)
    while len(out) < n:
        tail = out[-xf:]
        best, lag = -2.0, 0
        for L in range(0, min(len(s) - 2 * xf, int(SR * 0.012))):
            c = s[L:L + xf]
            r = float(np.dot(tail, c) / (np.linalg.norm(tail) * np.linalg.norm(c) + 1e-9))
            if r > best:
                best, lag = r, L
        chunk = s[lag:]
        f = np.linspace(0, 1, xf)
        out = np.concatenate([out[:-xf], out[-xf:] * (1 - f) + chunk[:xf] * f, chunk[xf:]])
    out = out[:n]
    a, r = int(SR * .035), int(SR * .12)
    out[:a] *= np.linspace(0, 1, a)
    out[-r:] *= np.linspace(1, 0, r) ** 1.3
    return out.astype(np.float32)


def islands(y: np.ndarray) -> int:
    db, _, _, _ = frame_labels(y, SR, 10.0)
    return len([r for r in _runs(db > -35) if r[1] - r[0] >= 3])


def espeak_candidate(letter: str):
    from espeak_synth import synth
    mn = {"s": "s", "a": "a", "t": "t", "p": "p", "i": "I", "n": "n"}[letter]
    y, sr = synth(f"[[{mn}]]", voice="en-gb-x-rp" if letter == "a" else "en-us", rate=80, pitch=60)
    if sr != SR:
        y = resample_poly(y, SR, sr).astype(np.float32)
    y = trim(y, SR)
    if letter == "s":
        y = stretch_noise(y, 0.72)
    elif letter in "ain" and len(y) > int(SR * 0.05):
        y = sustain(y[int(len(y) * .2): int(len(y) * .8)], 0.72)
    return y


def phoneme_candidates(letter: str):
    """Yield (method, source, audio) candidates in order of preference."""
    if letter == "s":
        for ctx in ("ðə sˈʌn", "ðə sˈɪp", "ðə sˈæt"):
            for sp in (0.85, 0.75):
                seg = extract_fricative(ko(ctx, sp, False), SR)
                if len(seg) > SR * 0.08:
                    yield "kokoro-carrier-frication", f"{ctx} @{sp}", stretch_noise(seg, 0.72)
    elif letter in "tp":
        ctxs = ("ðə tˈʌp", "ðə tˈɪp", "ðə tˈæp") if letter == "t" else ("ðə pˈʌn", "ðə pˈæn", "ðə pˈɪn")
        for ctx in ctxs:
            for sp in (0.85, 0.75):
                seg = extract_stop(ko(ctx, sp, False), SR)
                if len(seg) > SR * 0.03:
                    pre = silence(0.03)
                    yield "kokoro-carrier-burst", f"{ctx} @{sp}", np.concatenate([pre, fade(seg, 2, 10)])
    elif letter in "ai":
        ctxs = ("ðə bˈæd", "ʔˈææ", "ˈæt", "hˈæt") if letter == "a" else ("ˈɪt", "ðə bˈɪd", "hˈɪt", "ˈɪn")
        for ctx in ctxs:
            for sp in (0.65, 0.75, 0.55):
                seg = steady_vowel(ko(ctx, sp, False), letter)
                if seg is not None:
                    yield "kokoro-steady-vowel", f"{ctx} @{sp}", sustain(seg, 0.72)
    elif letter == "n":
        for ph, sp in (("nnn", 0.75), ("nnn", 0.65), ("ˈnː", 0.6)):
            try:
                y = ko_clean(ph, sp)  # second of two, so no start-up 'uh' before the hum
            except RuntimeError:
                continue
            if islands(y) == 1:
                yield "kokoro-isolated (second of two)", f"{ph} @{sp}", y
    yield "espeak-ng-phoneme-mode", f"[[{letter}]]", espeak_candidate(letter)


def build_phonemes(log: dict) -> dict:
    out = {}
    for letter in ("s", "a", "t", "p", "i", "n"):
        chosen = None
        tried = []
        for method, src, y in phoneme_candidates(letter):
            y = normalise(fade(y, 3, 15))
            d = describe_phoneme(y, SR)
            probs = check_phoneme(letter, d)
            tried.append({"method": method, "source": src, "problems": probs})
            if not probs:
                chosen = (method, src, y, d)
                break
        if chosen is None:
            raise SystemExit(f"No candidate for /{letter}/ passed the phoneme checks: {tried}")
        method, src, y, d = chosen
        out[letter] = y
        log["phonemes"][letter] = {"method": method, "source": src, "tried": len(tried),
                                   "measures": {k: (round(v, 3) if isinstance(v, float) else v) for k, v in d.items()}}
        print(f"  /{letter}/  {method:26s} {src:18s} dur {d['duration']:.2f}s  (candidate {len(tried)})")
    return out


# ----------------------------------------------------------------- Arabic
MARK = re.compile(r"\{(ph|w):([a-z]+)\}")
PUNCT_PAUSE = {"،": 0.26, ",": 0.26, "؛": 0.3, ";": 0.3, ":": 0.32, ".": 0.48, "؟": 0.48, "?": 0.48,
               "!": 0.45, "\n": 0.5}
SPLIT = re.compile(r"([،,؛;:.؟?!\n])")


def arabic_plan(script: str):
    """Turn a say-script into [('ar', phrase, pause) | ('ph', x) | ('w', x)] items."""
    script = script.replace("…", "،").replace("...", "،").replace("«", "").replace("»", "")
    script = script.replace("(", "").replace(")", "").replace("–", "،").replace("—", "،")
    items = []
    pos = 0
    for m in list(MARK.finditer(script)) + [None]:
        chunk = script[pos: m.start()] if m else script[pos:]
        parts = SPLIT.split(chunk)
        for i in range(0, len(parts), 2):
            text = strip_diacritics(parts[i]).strip()
            punct = parts[i + 1] if i + 1 < len(parts) else ""
            if text:
                if re.search(r"[A-Za-z0-9٠-٩]", text):
                    raise ValueError(f"Latin letters or digits reach the Arabic voice: {text!r} — add a 'say' script")
                items.append(["ar", text, PUNCT_PAUSE.get(punct, 0.12)])
            elif punct and items:
                if items[-1][0] == "ar":
                    items[-1][2] = max(items[-1][2], PUNCT_PAUSE.get(punct, 0.12))
                else:
                    items.append(["gap", PUNCT_PAUSE.get(punct, 0.12)])
        if m:
            items.append([m.group(1), m.group(2)])
            pos = m.end()
    return items


def mms_synth(phrases: list[str]) -> dict:
    keys = {p: "p_" + hashlib.sha1(p.encode("utf-8")).hexdigest()[:16] for p in phrases}
    req = [{"key": k, "text": p} for p, k in keys.items()]
    out_dir = CACHE / "mms"
    out_dir.mkdir(parents=True, exist_ok=True)
    req_path = CACHE / "mms_requests.json"
    req_path.write_text(json.dumps(req, ensure_ascii=False, indent=0), encoding="utf-8")
    subprocess.run([str(MMS_PY), str(ROOT / "tools" / "tts_mms.py"), str(req_path), str(out_dir)], check=True)
    res = {}
    for p, k in keys.items():
        y, sr = sf.read(out_dir / f"{k}.wav", dtype="float32")
        y = resample_poly(y, SR, sr).astype(np.float32)
        res[p] = normalise(fade(trim(y, SR, top_db=45), 5, 30))
    return res


# ----------------------------------------------------------------- main
def main() -> None:
    content = json.loads((APP / "content.json").read_text(encoding="utf-8"))
    log = {"engine": {"english": "Kokoro-82M v1.0 (kokoro-onnx), voice af_heart, Apache-2.0",
                      "arabic": "Meta MMS-TTS facebook/mms-tts-ara (VITS), CC BY-NC 4.0",
                      "fallback": "espeak-ng phoneme mode (GPL-3.0 engine) only if a Kokoro phoneme fails its checks"},
           "phonemes": {}, "files": {}}
    manifest = {"version": content["meta"]["version"], "en": {}, "ar": {}}
    (AUD / "en").mkdir(parents=True, exist_ok=True)
    (AUD / "ar").mkdir(parents=True, exist_ok=True)

    print("Phonemes (pure letter sounds from IPA input):")
    ph = build_phonemes(log)
    for k, y in ph.items():
        to_mp3(y, AUD / "en" / f"ph-{k}.mp3", 64)
        manifest["en"][f"ph-{k}"] = round(len(y) / SR, 3)

    print("Words and keywords:")
    words = {}
    log["words"] = {}
    firsts = {w: m["sounds"][0] for w, m in content["words"].items()}
    firsts.update({k: v["first"] for k, v in content["keywords"].items()})
    firsts["cat"] = "t"  # /k/: a voiceless stop, checked like t and p
    for w, ipa in WORD_IPA.items():
        y = normalise(fade(clean_word(w, ipa, firsts[w], log)))
        print(f"  {w:7s} {log['words'][w].get('method')} {log['words'][w].get('whisper', '')}")
        words[w] = y
        to_mp3(y, AUD / "en" / f"w-{w}.mp3", 64)
        manifest["en"][f"w-{w}"] = round(len(y) / SR, 3)
    print(f"  {len(words)} word clips")

    print("Segmented blends (0.4 s gaps):")
    for w, meta in content["words"].items():
        parts = []
        for i, s in enumerate(meta["sounds"]):
            if i:
                parts.append(silence(0.4))
            parts.append(ph[s])
        y = normalise(np.concatenate(parts))
        to_mp3(y, AUD / "en" / f"b-{w}.mp3", 64)
        manifest["en"][f"b-{w}"] = round(len(y) / SR, 3)
    print(f"  {len(content['words'])} blend clips")

    print("English phrases:")
    sanad = "sˈɑnɑd"
    for key, text in content["english"].items():
        if "Sanad" in text:
            # say the mascot's Arabic name properly (sanad), not an English guess
            a, b = text.split("Sanad", 1)
            tok = kokoro().tokenizer
            pa = tok.phonemize(a.strip(), "en-us") if a.strip() else ""
            lead = "." if b.lstrip().startswith(".") else ""
            pb = tok.phonemize(b.strip().lstrip(".").strip(), "en-us")
            y = ko_clean_phrase((pa + " " if pa else "") + sanad + lead + " " + pb, 0.95)
        else:
            y = ko_clean_phrase(kokoro().tokenizer.phonemize(text, "en-us"), 0.95)
        y = normalise(fade(y))
        to_mp3(y, AUD / "en" / f"x-{key}.mp3", 64)
        manifest["en"][f"x-{key}"] = round(len(y) / SR, 3)
    print(f"  {len(content['english'])} phrase clips")

    print("Arabic parent texts (MMS + spliced English sounds):")
    plans = {}
    for tid, t in content["texts"].items():
        if "ar" not in t or t.get("noAudio"):
            continue
        plans[tid] = arabic_plan(t.get("say") or t["ar"])
    for app in content.get("trustedApps", []):
        for fld in ("why", "ask"):
            if fld in app:
                plans[f"app_{app['id']}_{fld}"] = arabic_plan(app[fld].get("say") or app[fld]["ar"])
    phrases = sorted({it[1] for p in plans.values() for it in p if it[0] == "ar"})
    print(f"  {len(plans)} texts, {len(phrases)} unique phrases")
    ar_audio = mms_synth(phrases)
    for tid, plan in plans.items():
        seq = [silence(0.05)]
        for it in plan:
            if it[0] == "ar":
                seq += [ar_audio[it[1]], silence(it[2])]
            elif it[0] == "gap":
                seq.append(silence(it[1]))
            elif it[0] == "ph":
                seq += [silence(0.1), ph[it[1]], silence(0.22)]
            elif it[0] == "w":
                if it[1] not in words:
                    raise ValueError(f"{tid}: no English clip for word {it[1]!r}")
                seq += [silence(0.08), words[it[1]], silence(0.2)]
        y = normalise(trim(np.concatenate(seq), SR, top_db=50, pad_ms=60))
        mixed = any(it[0] in ("ph", "w") for it in plan)
        # pure Arabic: MMS is 16 kHz anyway -> 16 kHz / 32 kbps; with English sounds keep 24 kHz / 48 kbps
        to_mp3(y, AUD / "ar" / f"{tid}.mp3", 48 if mixed else 32, SR if mixed else 16000)
        src = content["texts"][tid]["ar"] if tid in content["texts"] else None
        if src is None:
            a_id, fld = tid[4:].rsplit("_", 1)
            src = next(a for a in content["trustedApps"] if a["id"] == a_id)[fld]["ar"]
        manifest["ar"][tid] = {"d": round(len(y) / SR, 2), "h": fnv1a(src)}
        log["files"][f"ar/{tid}.mp3"] = {"plan": [it if it[0] != "ar" else ["ar", it[1]] for it in plan]}
    print(f"  {len(plans)} Arabic clips")

    (AUD / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    (ROOT / "tools" / "audio_build_log.json").write_text(json.dumps(log, ensure_ascii=False, indent=1), encoding="utf-8")
    total = sum(f.stat().st_size for f in AUD.rglob("*.mp3"))
    print(f"Done: {len(list(AUD.rglob('*.mp3')))} MP3 files, {total / 1024:.0f} KB")


if __name__ == "__main__":
    main()
