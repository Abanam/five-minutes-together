"""Build the v1.1 audio (make_audio.py stays unchanged so v1.0 can still be rebuilt).

    .venv/Scripts/python.exe tools/make_audio_v11.py --calibrate          # credit rate + are previous/next_text billed?
    .venv/Scripts/python.exe tools/make_audio_v11.py [--only en|ph|ar|all] [--no-retakes]

Sources (see deliverables/voices.md):
  ph-*  the six letter sounds: ElevenLabs (tools/letters_v11.py; the team's recordings were not good enough, so the
        user asked for ElevenLabs here too), chosen in the studio page, checked with the unchanged RULES
  b-*   joined from the new letter sounds with 0.4 s gaps (unchanged rule)
  w-*   ElevenLabs, chosen English voice, eleven_multilingual_v2, text "<word>." – onset checks + Whisper "small"
  x-*   ElevenLabs, same voice; "Sanad" must be heard as Sanad (try "Sanad", then the respelling "Sah-nad")
  ar/*  ElevenLabs, the Arabic voice made with Voice Design, one request per segment between the markers;
        {ph:x}/{w:x} are spliced in from the English clips (gaps 0.10/0.22 s and 0.08/0.20 s; where the script
        has a punctuation mark right next to a marker, v1.0's pause for that mark is used if it is longer)
Same files and manifest format as v1.0 (hash = fnv1a of the ar text; version = meta.version), plus
tools/audio_build_log.json with the source of every clip. Nothing is paid for twice (cache in tools/eleven.py).
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).parent))
import make_audio as M  # noqa: E402  (fnv1a, normalise, fade, to_mp3, silence, onset_ok, PUNCT_PAUSE, SR)
from audio_analysis import _runs, check_phoneme, describe_phoneme, extract_stop, formants, frame_labels, trim  # noqa: E402
from v11_common import ENGLISH_PROMPT, MARK, norm_ar, plan, seed_for, whisper_word_ok  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
AUD = APP / "audio"
WORK = ROOT / "tools" / ".audio-cache" / "v11"
VOICES = ROOT / "tools" / "voices.json"
CHOSEN = ROOT / "recordings" / "chosen"   # studio Record tab (human takes; not used for the letter sounds, see below)
LETTERS = WORK / "letters" / "chosen"     # the six letter sounds: ElevenLabs (tools/letters_v11.py), chosen in the studio
CALIB = WORK / "calibration.json"
SR = M.SR
LATE = ["teacher_guide", "about_purpose", "teacher_edit", "about_privacy", "about_ai"]  # generated last (budget rule)
CONTINUOUS, STOPS = ("s", "a", "i", "n"), ("t", "p")
CTX_MAX = 150      # characters of neighbouring Arabic text sent as previous_text / next_text (only if not billed)
SHORT_SEG = 12     # segments shorter than this (و، أو، في …) get their own context at every occurrence
RETAKE_FLOOR = 300  # no retakes below this many credits (brief §4.3)


class Stop(SystemExit):
    pass


def load_content() -> dict:
    return json.loads((APP / "content.json").read_text(encoding="utf-8"))


def voices() -> dict:
    return json.loads(VOICES.read_text(encoding="utf-8"))


def decode(path: Path, sr: int = SR) -> np.ndarray:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar", str(sr), "-"],
                         check=True, capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32).copy()


# ------------------------------------------------------------------ Whisper (same model and settings as verify_audio.py)
_wm = None


def whisper(path: Path, lang: str, prompt: str | None = None) -> str:
    global _wm
    if _wm is None:
        from faster_whisper import WhisperModel
        _wm = WhisperModel("small", device="cpu", compute_type="int8", download_root=str(Path.home() / ".cache" / "fmt-models" / "whisper"))
    kw = dict(language=lang, beam_size=5, without_timestamps=True)
    if prompt:
        kw["initial_prompt"] = prompt
    segs, _ = _wm.transcribe(str(path), **kw)
    return " ".join(s.text for s in segs).strip()


def ar_similarity(ref: str, heard: str) -> float:
    return difflib.SequenceMatcher(None, norm_ar(ref), norm_ar(heard)).ratio()


# ------------------------------------------------------------------ the checks of verify_audio.py (§7.4)
def drange(name: str, folder: str) -> tuple[float, float]:
    if folder != "en":
        return (0.8, 75.0)
    if name.startswith("ph-"):
        return (0.55, 0.95) if name[3:] in CONTINUOUS else (0.05, 0.45)
    return {"w-": (0.25, 1.6), "b-": (0.8, 3.5), "x-": (0.5, 5.0)}[name[:2]]


def clip_check(path: Path) -> dict:
    y = decode(path)
    dur = len(y) / SR
    lo, hi = drange(path.stem, path.parent.name)
    f = int(SR * 0.02)
    n = max(1, len(y) // f)
    r = np.sqrt(np.mean(y[: n * f].reshape(n, f) ** 2, axis=1) + 1e-12)
    act = r[r > r.max() * 10 ** (-30 / 20)]
    rms = float(20 * np.log10(np.sqrt(np.mean(act ** 2)) + 1e-12))
    peak = float(np.max(np.abs(y))) if y.size else 0.0
    flat = int(np.sum(np.abs(y) >= 0.999))
    return {"duration": round(dur, 3), "range": [lo, hi], "active_rms_db": round(rms, 1), "clipped_samples": flat,
            "pass": bool(lo <= dur <= hi and rms > -35 and peak < 0.999 and flat == 0)}


def verify_onset(y: np.ndarray, first: str) -> bool:
    """The word-onset check of verify_audio.py (step 4b), on a trimmed clip."""
    db, v, cen, _ = frame_labels(y, SR, 10.0)
    aud = [i for i in range(len(db)) if db[i] > -35][:6]
    if first in ("s", "t", "p"):
        return sum(1 for i in aud[:4] if v[i]) == 0
    if first in ("a", "i"):
        fm = formants(y[: int(SR * 0.09)], SR)
        return bool(fm) and fm["F2"] > 1400
    return True


# ------------------------------------------------------------------ English (words and phrases)
def first_sound(word: str, content: dict | None = None) -> str:
    c = content or load_content()
    if word in c["words"]:
        return c["words"][word]["sounds"][0]
    if word in c["keywords"]:
        return c["keywords"][word]["first"]
    return "t"  # "cat": /k/ is a voiceless stop, checked like /t/ and /p/


def process_english(mp3: Path, word: str, out_name: str) -> tuple[Path, bool]:
    """ElevenLabs MP3 -> 24 kHz, trimmed, normalised, faded, MP3 64 kbps. Returns (mp3, onset ok)."""
    y = decode(mp3)
    y = M.normalise(M.fade(trim(y, SR, top_db=45, pad_ms=12), 6, 30))
    out = WORK / "en" / f"{out_name}.mp3"
    M.to_mp3(y, out, 64)
    back = trim(decode(out), SR)
    first = first_sound(word)
    return out, bool(M.onset_ok(back, first) and verify_onset(back, first))


WORD_PLAN = ROOT / "tools" / "word_choices.json"


def word_plan() -> dict:
    """What the team approved or chose for single words (tracked in git, so the build can be repeated exactly):
    {word: {"extra_retakes": n, "respell": {"text": t, "tries": n}, "chosen": {"retake": r, "onset_from": d|null}, "why": …}}"""
    return json.loads(WORD_PLAN.read_text(encoding="utf-8")) if WORD_PLAN.exists() else {}


def build_words(log: dict, retakes: bool = True, extra: dict | None = None, respell: dict | None = None) -> list[str]:
    """extra = {word: n}: retakes beyond the brief's two, only where the user approved them (e.g. "pan": 5).
    respell = {word: (text, n)}: n more tries with another text (brief §4.4: "respell it"), approved by the user.
    Both are also read from tools/word_choices.json, together with the try the team chose by ear ("chosen"): that try is
    used even where the automatic checks disagree, and the checks are still run and logged."""
    import eleven
    c = load_content()
    v = voices()["english"]
    words = list(c["words"]) + list(c["keywords"]) + ["cat"]
    plan_all = word_plan()
    failed = []
    for w in words:
        wp = plan_all.get(w, {})
        n_plain = (3 + (extra or {}).get(w, wp.get("extra_retakes", 0))) if retakes else 1
        todo = [(f"{w}.", r) for r in range(n_plain)]
        rs = (respell or {}).get(w) or ((wp["respell"]["text"], wp["respell"]["tries"]) if wp.get("respell") else None)
        if retakes and rs:
            todo += [(rs[0], n_plain + j) for j in range(rs[1])]
        pick = wp.get("chosen")
        if pick:   # the team chose by ear among tries already made: only cached tries are listed again (no credits)
            def made(p: tuple[str, int]) -> bool:
                key = eleven.tts_key(p[0], v["voice_id"], seed_for(f"w-{w}", p[1]))
                return (eleven.CACHE / "tts" / (key + ".mp3")).exists()
            todo = [p for p in todo if made(p)]
        tries, chosen = [], None
        src_of = lambda t: eleven.tts(f"w-{w}", t["text"], v["voice_id"], t["seed"])[0]   # noqa: E731  (cached: no cost)
        for text, r in todo:
            if r and eleven.credits_left() < RETAKE_FLOOR:
                print(f"  w-{w}: no retake, fewer than {RETAKE_FLOOR} credits left")
                break
            src, cached, used = eleven.tts(f"w-{w}", text, v["voice_id"], seed_for(f"w-{w}", r))
            mp3, onset = process_english(src, w, f"w-{w}-r{r}")
            heard = whisper(mp3, "en", ENGLISH_PROMPT)
            ok, exact = whisper_word_ok(heard, w)
            tries.append({"retake": r, "text": text, "seed": seed_for(f"w-{w}", r), "onset_ok": onset, "whisper": heard,
                          "match": ok, "exact": exact, "credits": used, "cached": cached})
            if onset and ok and not pick:
                chosen = r
                break
        passed = chosen is not None
        stripped, how, by_ear = None, "natural", None
        if pick:   # the team's choice by ear; the unchanged checks are run on it and logged
            base = next(t for t in tries if t["retake"] == pick["retake"])
            if pick.get("onset_from") is not None:   # from the processed tries, exactly as on the listening page
                donor = next(t for t in tries if t["retake"] == pick["onset_from"])
                path, onset = transplant_stop(WORK / "en" / f"w-{w}-r{donor['retake']}.mp3", WORK / "en" / f"w-{w}-r{base['retake']}.mp3",
                                              w, f"w-{w}-r{base['retake']}-onset-r{donor['retake']}-chosen")
                how = f"onset from try {donor['retake']}"
                heard = whisper(path, "en", ENGLISH_PROMPT)
                ok = whisper_word_ok(heard, w)[0]
                stripped = path
            else:
                onset, heard, ok = base["onset_ok"], base["whisper"], base["match"]
            chosen, passed = base["retake"], bool(onset and ok)
            by_ear = {"why": wp.get("why"), "onset_ok": bool(onset), "whisper": heard, "match": ok}
        if not passed and not pick:   # a try that Whisper heard right but whose onset failed: cut the voiced lead (free)
            for t in tries:
                if t["match"] and not t["onset_ok"]:
                    src = src_of(t)
                    res = strip_try(src, w, f"w-{w}-r{t['retake']}-stripped")
                    if res and res[1]:
                        heard = whisper(res[0], "en", ENGLISH_PROMPT)
                        ok, exact = whisper_word_ok(heard, w)
                        t["onset_stripped"] = {"onset_ok": True, "whisper": heard, "match": ok}
                        if ok:
                            stripped, chosen, passed, how = res[0], t["retake"], True, "voiced lead cut"
                            break
        if not passed and not pick and first_sound(w) in STOPS:
            # Whisper heard a try right but its stop had almost no aspiration (voicing ~10 ms after the burst, which
            # sounds like /b/ to Arabic speakers): put the natural burst + aspiration of a try whose onset passed in front
            # of the right try's voiced part (same voice, same text, no extra credits), then check both again
            base = next((t for t in tries if t["match"]), None)
            donor = next((t for t in tries if t["onset_ok"]), None)
            if base and donor:
                res = splice_stop(src_of(donor), src_of(base), w, f"w-{w}-spliced")
                if res and res[1]:
                    heard = whisper(res[0], "en", ENGLISH_PROMPT)
                    ok, exact = whisper_word_ok(heard, w)
                    base["spliced_onset_from_retake"] = {"donor": donor["retake"], "onset_ok": True, "whisper": heard, "match": ok}
                    if ok:
                        stripped, chosen, passed, how = res[0], base["retake"], True, f"aspiration from try {donor['retake']}"
        if not passed and not pick and first_sound(w) in STOPS:
            # still not: the whole natural onset (burst + aspiration up to the voicing) of each try whose onset passed, in
            # front of the voiced part of each try Whisper heard right; pairs in try order, the first that passes both
            # unchanged checks is used (same voice, same text, cached tries: no extra credits)
            for base in [t for t in tries if t["match"]]:
                for donor in [t for t in tries if t["onset_ok"]]:
                    res = transplant_stop(src_of(donor), src_of(base), w, f"w-{w}-r{base['retake']}-onset-r{donor['retake']}")
                    tr = {"donor": donor["retake"], "onset_ok": bool(res and res[1])}
                    if res and res[1]:
                        heard = whisper(res[0], "en", ENGLISH_PROMPT)
                        tr["whisper"], tr["match"] = heard, whisper_word_ok(heard, w)[0]
                    base.setdefault("onset_transplants", []).append(tr)
                    if tr.get("match"):
                        stripped, chosen, passed, how = res[0], base["retake"], True, f"onset from try {donor['retake']}"
                        break
                if passed:
                    break
        if not passed:
            failed.append(w)
            chosen = next((t["retake"] for t in tries if t["match"]), next((t["retake"] for t in tries if t["onset_ok"]), 0))
        rec = ROOT / "recordings" / "chosen" / f"w-{w}.wav"
        if not passed and not pick and rec.exists():   # a word that failed twice and was recorded in the studio page
            y, _ = sf.read(rec, dtype="float32")
            M.to_mp3(M.normalise(M.fade(trim(y, SR, top_db=45, pad_ms=12), 6, 30)), AUD / "en" / f"w-{w}.mp3", 64)
            log["clips"][f"en/w-{w}.mp3"] = {"source": "human recording (project team member)", "file": str(rec.relative_to(ROOT)),
                                              "elevenlabs_tries": tries}
            print(f"  w-{w:7} recorded take used (ElevenLabs failed {len(tries)}x)")
            continue
        (AUD / "en").mkdir(parents=True, exist_ok=True)
        (AUD / "en" / f"w-{w}.mp3").write_bytes((stripped or WORK / "en" / f"w-{w}-r{chosen}.mp3").read_bytes())
        used_try = next(t for t in tries if t["retake"] == chosen)
        log["clips"][f"en/w-{w}.mp3"] = {"source": "ElevenLabs", "voice": v["name"], "voice_id": v["voice_id"],
                                          "model": "eleven_multilingual_v2", "settings": v.get("settings"), "text": used_try["text"],
                                          "retake_used": chosen, "onset_stripped": bool(stripped), "onset_method": how,
                                          "tries": tries, "passed": passed,
                                          **({"extra_retakes_approved_by_user": n_plain - 3} if n_plain > 3 else {}),
                                          **({"respelled_tries_approved_by_user": {"text": rs[0], "tries": rs[1]}} if retakes and rs else {}),
                                          **({"chosen_by_team_by_ear": by_ear} if by_ear else {})}
        print(f"  w-{w:7} {'OK ' if passed else 'FAIL'} try {chosen} {used_try['text']!r} heard "
              f"{(by_ear or {}).get('whisper', used_try['whisper'])!r} (tries {len(tries)}"
              f"{'' if how == 'natural' else ', ' + how}{', chosen by ear' if by_ear else ''})")
    set_record_words(failed)
    return failed


def splice_stop(donor_src: Path, base_src: Path, word: str, out_name: str, vot: float = 0.055) -> tuple[Path, bool] | None:
    """Give the right try a natural aspiration: its own burst, then aspiration grains taken from the donor try's
    aspiration (same voice, same word) up to `vot` seconds, then its own voiced part from the voicing onset."""
    donor = trim(decode(donor_src), SR, top_db=45, pad_ms=12)
    base = trim(decode(base_src), SR, top_db=45, pad_ms=12)
    asp = extract_stop(donor, SR)[int(0.008 * SR):]          # donor aspiration without its burst
    db, v, _, hop = frame_labels(base, SR, 10.0)
    aud = next((i for i in range(len(db)) if db[i] > -35), 0)
    on = next((i for i in range(aud, len(db)) if v[i] and db[i] > -30), None)
    if len(asp) < int(0.012 * SR) or on is None:
        return None
    burst = base[aud * hop: max(aud * hop + int(0.008 * SR), on * hop - int(0.004 * SR))]
    n = max(0, int(vot * SR) - len(burst))
    g = int(0.012 * SR)
    rng = np.random.default_rng(5)
    fill = np.zeros(n + g)
    for i in range(0, max(n, 1), g // 2):
        s = int(rng.integers(0, max(1, len(asp) - g)))
        piece = asp[s:s + g]
        fill[i:i + len(piece)] += piece * np.hanning(g)[: len(piece)]
    fill = fill[:n] * (float(np.sqrt(np.mean(asp ** 2))) / (float(np.sqrt(np.mean(fill ** 2))) + 1e-9) if n else 1.0)
    rest = base[max(0, on * hop - int(0.004 * SR)):]
    xf = int(0.004 * SR)
    f = np.linspace(0, 1, xf)
    head = np.concatenate([burst, fill]) if n else burst
    y = np.concatenate([head[:-xf], head[-xf:] * (1 - f) + rest[:xf] * f, rest[xf:]])
    out = WORK / "en" / f"{out_name}.mp3"
    M.to_mp3(M.normalise(M.fade(y, 3, 30)), out, 64)
    back = trim(decode(out), SR)
    first = first_sound(word)
    return out, bool(M.onset_ok(back, first) and verify_onset(back, first))


def transplant_stop(donor_src: Path, base_src: Path, word: str, out_name: str) -> tuple[Path, bool] | None:
    """The donor try's own onset (silence pad, burst and aspiration up to its voicing onset) joined to the base try's
    voiced part (from its voicing onset), with a 4 ms crossfade; then the unchanged onset checks."""
    def voicing_onset(y: np.ndarray) -> int | None:
        db, v, _, hop = frame_labels(y, SR, 10.0)
        aud = next((i for i in range(len(db)) if db[i] > -35), 0)
        on = next((i for i in range(aud, len(db)) if v[i] and db[i] > -30), None)
        return None if on is None else max(0, on * hop - int(0.004 * SR))
    donor = trim(decode(donor_src), SR, top_db=45, pad_ms=12)
    base = trim(decode(base_src), SR, top_db=45, pad_ms=12)
    d_on, b_on = voicing_onset(donor), voicing_onset(base)
    xf = int(0.004 * SR)
    if d_on is None or b_on is None or d_on < 2 * xf:
        return None
    head, rest = donor[:d_on + xf], base[b_on:]
    f = np.linspace(0, 1, xf)
    y = np.concatenate([head[:-xf], head[-xf:] * (1 - f) + rest[:xf] * f, rest[xf:]])
    out = WORK / "en" / f"{out_name}.mp3"
    M.to_mp3(M.normalise(M.fade(y, 3, 30)), out, 64)
    back = trim(decode(out), SR)
    first = first_sound(word)
    return out, bool(M.onset_ok(back, first) and verify_onset(back, first))


def strip_try(src: Path, word: str, out_name: str) -> tuple[Path, bool] | None:
    """Cut a voiced lead before the first sound (make_audio.strip_onset, as in v1.0), then re-run the onset checks."""
    first = first_sound(word)
    y = M.strip_onset(trim(decode(src), SR, top_db=45, pad_ms=12), first)
    if y is None:
        return None
    out = WORK / "en" / f"{out_name}.mp3"
    M.to_mp3(M.normalise(M.fade(y, 6, 30)), out, 64)
    back = trim(decode(out), SR)
    return out, bool(M.onset_ok(back, first) and verify_onset(back, first))


SANAD = re.compile(r"\bsa+h?[- ]?n+a+d\b")


def build_phrases(log: dict) -> None:
    import eleven
    c = load_content()
    v = voices()["english"]
    for key, text in c["english"].items():
        variants = [text] if "Sanad" not in text else [text, text.replace("Sanad", "Sah-nad")]
        info, pick = [], 0
        for k, sent in enumerate(variants):
            src, cached, used = eleven.tts(f"x-{key}", sent, v["voice_id"], seed_for(f"x-{key}"))
            y = M.normalise(M.fade(trim(decode(src), SR, top_db=45, pad_ms=12), 6, 40))
            out = WORK / "en" / f"x-{key}-{k}.mp3"
            M.to_mp3(y, out, 64)
            heard = whisper(out, "en")
            ok = "Sanad" not in text or bool(SANAD.search(heard.lower()))
            info.append({"text_sent": sent, "whisper": heard, "sanad_heard": ok if "Sanad" in text else None,
                         "credits": used, "cached": cached})
            if ok:
                pick = k
                break
        (AUD / "en" / f"x-{key}.mp3").write_bytes((WORK / "en" / f"x-{key}-{pick}.mp3").read_bytes())
        log["clips"][f"en/x-{key}.mp3"] = {"source": "ElevenLabs", "voice": v["name"], "voice_id": v["voice_id"],
                                            "model": "eleven_multilingual_v2", "settings": v.get("settings"),
                                            "seed": seed_for(f"x-{key}"), "text_sent": variants[pick], "tries": info,
                                            "sanad_confirmed": info[pick]["sanad_heard"]}
        print(f"  x-{key:9} heard {info[pick]['whisper']!r}")


# ------------------------------------------------------------------ letter sounds (human recordings) and blends
def prepare_take(raw: Path, out24: Path) -> np.ndarray:
    """Studio step 1: FFmpeg to 24 kHz mono, then a 70 Hz high-pass. The button clicks at both ends are dropped."""
    out24.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(raw), "-af", f"aresample={SR},highpass=f=70", "-ac", "1",
                    "-ar", str(SR), str(out24)], check=True)
    y, _ = sf.read(out24, dtype="float32")
    edge = int(0.15 * SR)
    if len(y) > 4 * edge:
        y = y[edge:-edge]
    sf.write(out24, y, SR, subtype="PCM_16")
    return y


def shape_phoneme(y: np.ndarray, letter: str) -> np.ndarray:
    """trim -> length rule -> normalise -> fades (the §6 final-processing rules without the MP3 step)."""
    y = trim(y, SR)
    if letter in CONTINUOUS:
        if len(y) > int(0.9 * SR):  # a long hold: keep its steady middle 0.85 s
            a = (len(y) - int(0.85 * SR)) // 2
            y = y[a:a + int(0.85 * SR)]
        return M.fade(M.normalise(y), 35, 100)
    if len(y) > int(0.30 * SR):     # a stop is burst + aspiration; a long breath tail is cut
        y = M.fade(y[: int(0.30 * SR)], 0, 40)
    return M.fade(M.normalise(y), 2, 12)


def check_take(y: np.ndarray, letter: str) -> tuple[dict, list[str]]:
    """describe_phoneme + check_phoneme (RULES unchanged); continuous sounds must also reach the 0.6 s final length."""
    d = describe_phoneme(y, SR)
    probs = check_phoneme(letter, d)
    if letter in CONTINUOUS and d["duration"] < 0.6 and not any(p.startswith("duration") for p in probs):
        probs.append(f"duration {d['duration']:.2f}s below the 0.6 s final-clip length")
    return d, probs


def finalize_phoneme(letter: str, log: dict) -> np.ndarray:
    """The chosen ElevenLabs letter sound -> the §6 final processing -> MP3 -> decoded again and re-checked."""
    src = LETTERS / f"ph-{letter}.wav"
    meta = json.loads((LETTERS / f"ph-{letter}.json").read_text(encoding="utf-8"))
    y, _ = sf.read(src, dtype="float32")
    y = shape_phoneme(y, letter)
    clip = np.concatenate([M.silence(0.1), y]) if letter in STOPS else y   # phones often cut the first tens of ms
    out = AUD / "en" / f"ph-{letter}.mp3"
    M.to_mp3(clip, out, 64)
    d, probs = check_take(trim(decode(out), SR), letter)
    if probs:
        raise Stop(f"/{letter}/ fails after MP3 encoding: {probs} – choose another candidate in the studio page")
    log["clips"][f"en/ph-{letter}.mp3"] = {
        "source": "ElevenLabs (the team's recordings were not good enough; changed at the user's request)",
        "voice": meta["voice"], "voice_id": meta["voice_id"], "model": "eleven_multilingual_v2",
        "text_sent": meta["text"], "kind": meta["kind"], "method": meta["how"], "natural_part_s": meta["source_seconds"],
        "processing": "trim, " + ("steady middle <= 0.85 s, normalise, fades 35/100 ms" if letter in CONTINUOUS
                                  else "<= 0.30 s, normalise, fades 2/12 ms, 0.1 s lead silence") + ", MP3 24 kHz 64 kbps",
        "measures": {k: (round(v, 3) if isinstance(v, float) else v) for k, v in d.items()}, "check_phoneme": "pass (after MP3)"}
    return y


def build_phonemes_and_blends(log: dict) -> dict:
    c = load_content()
    missing = [s for s in c["sounds"] if not (LETTERS / f"ph-{s}.wav").exists()]
    if missing:
        raise Stop(f"no letter sound chosen yet: {', '.join('ph-' + s for s in missing)} – run tools/letters_v11.py")
    ph = {s: finalize_phoneme(s, log) for s in c["sounds"]}
    for s, y in ph.items():
        print(f"  ph-{s}: {len(y) / SR:.2f} s")
    for w, meta in c["words"].items():
        parts = [M.silence(0.1)] if meta["sounds"][0] in STOPS else []
        for i, s in enumerate(meta["sounds"]):
            if i:
                parts.append(M.silence(0.4))
            parts.append(ph[s])
        M.to_mp3(M.normalise(np.concatenate(parts)), AUD / "en" / f"b-{w}.mp3", 64)
        log["clips"][f"en/b-{w}.mp3"] = {"source": "joined from the recorded letter sounds, 0.4 s gaps"}
    return ph


# ------------------------------------------------------------------ Arabic
PAUSE = {k: v for k, v in M.PUNCT_PAUSE.items() if k != "\n"}


def arabic_texts(c: dict) -> dict:
    t = {k: (v.get("say") or v["ar"], v["ar"]) for k, v in c["texts"].items() if "ar" in v and not v.get("noAudio")}
    for a in c["trustedApps"]:
        for f in ("why", "ask"):
            t[f"app_{a['id']}_{f}"] = (a[f].get("say") or a[f]["ar"], a[f]["ar"])
    order = [k for k in t if k not in LATE] + [k for k in LATE if k in t]
    return {k: t[k] for k in order}


def insert_pauses(say: str) -> list[tuple[str, str]]:
    """For every {ph:}/{w:} marker: the punctuation mark written right before and right after it ('' if none)."""
    out = []
    for m in MARK.finditer(say):
        pre, post = say[: m.start()].rstrip(), say[m.end():].lstrip()
        out.append((pre[-1:] if pre[-1:] in PAUSE else "", post[:1] if post[:1] in PAUSE else ""))
    return out


def segment_counts(texts: dict) -> dict:
    count: dict[str, int] = {}
    for say, _ in texts.values():
        for k, v in plan(say):
            if k == "ar":
                count[v] = count.get(v, 0) + 1
    return count


def contexts_for(say: str, counts: dict) -> list[tuple[str | None, str | None]]:
    """previous_text / next_text for each Arabic segment of one clip ((None, None) where a duplicate is made once)."""
    segs = [v for k, v in plan(say) if k == "ar"]
    out = []
    for i, s in enumerate(segs):
        if counts.get(s, 1) > 1 and len(s) >= SHORT_SEG:
            out.append((None, None))
            continue
        prev = " ".join(segs[:i])[-CTX_MAX:] or None
        nxt = " ".join(segs[i + 1:])[:CTX_MAX] or None
        out.append((prev, nxt))
    return out


def longest_silence(y: np.ndarray) -> float:
    db, _, _, hop = frame_labels(y, SR, 10.0)
    runs = [b - a for a, b in _runs(db < -45)]
    return max(runs) * hop / SR if runs else 0.0


def letters(s: str) -> int:
    return len(re.findall(r"[ء-ي]", s))


def segment_audio(seg: str, voice_id: str, ctx: tuple[str | None, str | None], retake: int = 0, item: str = "") -> tuple[np.ndarray, dict]:
    import eleven
    src, cached, used = eleven.tts(item or ("ar:" + seg[:20]), seg, voice_id, seed_for(seg, retake), previous_text=ctx[0], next_text=ctx[1])
    y = M.normalise(M.fade(trim(decode(src), SR, top_db=45, pad_ms=30), 5, 30))
    dur = len(y) / SR
    # speaking rate = characters of the text sent (letters, spaces, punctuation; no harakat) per second of speech,
    # the same way the brief counts characters ("168 characters" for the preview text); checked from 15 characters
    info = {"text": seg, "seed": seed_for(seg, retake), "retake": retake, "context": bool(ctx[0] or ctx[1]), "credits": used,
            "cached": cached, "seconds": round(dur, 2), "characters": len(seg), "letters": letters(seg),
            "chars_per_s": round(len(seg) / dur, 1) if dur else None, "longest_silence_s": round(longest_silence(y), 2)}
    info["rate_ok"] = len(seg) < 15 or (info["chars_per_s"] is not None and 8 <= info["chars_per_s"] <= 20)
    info["silence_ok"] = info["longest_silence_s"] <= 1.2
    return y, info


def build_arabic_clip(tid: str, say: str, voice_id: str, english_dir: Path | None = AUD / "en", counts: dict | None = None,
                      use_context: bool = False, retakes: dict | None = None) -> tuple[Path, dict]:
    """Assemble one Arabic clip. english_dir=None means the text has no English inserts (audition lines)."""
    items = plan(say)
    ctxs = iter(contexts_for(say, counts or {}) if use_context else [(None, None)] * len(items))
    pauses = iter(insert_pauses(say))
    seq, report = [M.silence(0.05)], {"segments": [], "inserts": []}
    for kind, val in items:
        if kind == "ar":
            y, info = segment_audio(val, voice_id, next(ctxs), (retakes or {}).get(val, 0), item=f"ar/{tid}")
            seq.append(y)
            report["segments"].append(info)
            continue
        if english_dir is None:
            raise ValueError(f"{tid} needs English inserts")
        clip = trim(decode(english_dir / f"{'ph' if kind == 'ph' else 'w'}-{val}.mp3"), SR, top_db=45, pad_ms=8)
        before, after = (0.10, 0.22) if kind == "ph" else (0.08, 0.20)
        pre, post = next(pauses)
        before, after = max(before, PAUSE.get(pre, 0)), max(after, PAUSE.get(post, 0))
        seq += [M.silence(before), M.normalise(clip), M.silence(after)]
        report["inserts"].append({"insert": f"{kind}:{val}", "gap_before": before, "gap_after": after})
    y = M.normalise(trim(np.concatenate(seq), SR, top_db=50, pad_ms=60))
    out = AUD / "ar" / f"{tid}.mp3"
    M.to_mp3(y, out, 48, SR)   # mono, 24 kHz, 48 kbps for every Arabic clip (the source is 44.1 kHz)
    speech = sum(s["seconds"] for s in report["segments"])
    report.update(seconds=round(len(y) / SR, 2), speech_seconds=round(speech, 2),
                  chars_per_s=round(sum(s["characters"] for s in report["segments"]) / speech, 1) if speech else None,
                  checks=clip_check(out))
    report["pass"] = bool(report["checks"]["pass"] and all(s["silence_ok"] and s["rate_ok"] for s in report["segments"]))
    return out, report


def calibration() -> dict:
    return json.loads(CALIB.read_text(encoding="utf-8")) if CALIB.exists() else {}


def calibrate() -> dict:
    """§4.3 rule 2: measured credits per character, and whether previous_text/next_text are billed."""
    import eleven
    usage = json.loads(eleven.USAGE_JSON.read_text(encoding="utf-8")) if eleven.USAGE_JSON.exists() else []
    tts_rows = [r for r in usage if r["kind"] == "tts" and not str(r.get("note", "")).startswith("ctx")]
    rate = round(sum(r["credits_used"] for r in tts_rows) / max(1, sum(r["chars"] for r in tts_rows)), 3) if tts_rows else None
    c = load_content()
    texts = arabic_texts(c)
    say = texts["d1_tip"][0]                   # its 2nd segment is "و" between two letter sounds: 1 character + context
    seg = [v for k, v in plan(say) if k == "ar"][1]
    ctx = contexts_for(say, segment_counts(texts))[1]
    before = eleven.credits_left()
    _, cached, used = eleven.tts("calibration: d1_tip 'و' with context", seg, voices()["arabic"]["voice_id"], seed_for(seg),
                                 previous_text=ctx[0], next_text=ctx[1])
    res = {"credits_per_character": rate, "measured_on": f"{len(tts_rows)} calls without context",
           "context_test": {"text": seg, "previous_text_chars": len(ctx[0] or ""), "next_text_chars": len(ctx[1] or ""),
                            "credits_used": used, "cached": cached, "credits_left_before": before},
           "context_billed": None}
    if not cached:
        res["context_billed"] = used > len(seg) + 2
    CALIB.parent.mkdir(parents=True, exist_ok=True)
    CALIB.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return res


RETAKES = WORK / "ar_retakes.json"   # {segment text: retake number} – segments re-made with a new seed (brief §4.3: ≤ 2)


def ar_retakes() -> dict:
    return json.loads(RETAKES.read_text(encoding="utf-8")) if RETAKES.exists() else {}


def fix_arabic(log: dict, use_context: bool, segments: list[str] | None = None) -> dict:
    """Re-make each Arabic segment that fails a §7.4 check (speaking rate 8–20 characters/s, silence ≤ 1.2 s), or the
    segments given, with a new seed: at most 2 retakes, none below RETAKE_FLOOR credits. Keeps the first take that passes."""
    import eleven
    c = load_content()
    vid = voices()["arabic"]["voice_id"]
    texts = arabic_texts(c)
    counts = segment_counts(texts)
    done = ar_retakes()
    todo = {}
    for tid, (say, _) in texts.items():
        segs = [v for k, v in plan(say) if k == "ar"]
        for s, ctx in zip(segs, contexts_for(say, counts) if use_context else [(None, None)] * len(segs)):
            info = segment_audio(s, vid, ctx, done.get(s, 0))[1]
            if (segments and s in segments) or (not segments and not (info["rate_ok"] and info["silence_ok"])):
                todo.setdefault(s, (tid, ctx, info))
    report = {}
    for s, (tid, ctx, first) in todo.items():
        tries = [dict(first, retake=done.get(s, 0))]
        for r in (1, 2):
            if eleven.credits_left() < RETAKE_FLOOR:
                print(f"  {tid}: no retake, fewer than {RETAKE_FLOOR} credits left")
                break
            _, info = segment_audio(s, vid, ctx, r, item=f"ar/{tid} retake {r}")
            tries.append(info)
            if info["rate_ok"] and info["silence_ok"]:
                done[s] = r
                break
        report[s] = {"clip": tid, "tries": [{k: t.get(k) for k in ("retake", "seconds", "characters", "chars_per_s", "longest_silence_s", "rate_ok", "silence_ok")} for t in tries],
                     "used_retake": done.get(s, 0)}
        print(f"  {tid}: " + ", ".join(f"retake {t['retake']}: {t['chars_per_s']} chars/s" for t in tries) + f" -> using retake {done.get(s, 0)}")
    RETAKES.write_text(json.dumps(done, ensure_ascii=False, indent=1), encoding="utf-8")
    log.setdefault("arabic_retakes", {}).update(report)
    return report


def build_arabic(log: dict, use_context: bool) -> dict:
    import eleven
    c = load_content()
    vid = voices()["arabic"]["voice_id"]
    texts = arabic_texts(c)
    counts = segment_counts(texts)
    retakes = ar_retakes()
    manifest_ar, failing = {}, []
    for tid, (say, ar_text) in texts.items():
        need = sum(len(v) for k, v in plan(say) if k == "ar")
        left = eleven.credits_left()
        if left < need:
            raise Stop(f"credits: {left} left, {tid} needs up to {need}. Everything made so far is kept (cache). "
                       f"Reset: {eleven.reset_date()} – see brief §4.6 for the options.")
        out, report = build_arabic_clip(tid, say, vid, AUD / "en", counts, use_context, retakes)
        manifest_ar[tid] = {"d": report["seconds"], "h": M.fnv1a(ar_text)}
        log["clips"][f"ar/{tid}.mp3"] = dict(source="ElevenLabs", voice=voices()["arabic"]["name"], voice_id=vid,
                                             model="eleven_multilingual_v2", settings=voices()["arabic"].get("settings"), **report)
        if not report["pass"]:
            failing.append(tid)
        print(f"  {tid:16} {report['seconds']:6.1f} s  {len(report['segments'])} seg  {report['chars_per_s']} chars/s"
              f"{'' if report['pass'] else '  CHECK FAILED'}")
    log["arabic_failing_checks"] = failing
    return manifest_ar


def write_manifest(manifest_ar: dict | None) -> None:
    c = load_content()
    old = json.loads((AUD / "manifest.json").read_text(encoding="utf-8"))
    en = {f.stem: round(len(decode(f)) / SR, 3) for f in sorted((AUD / "en").glob("*.mp3"))}
    ar = manifest_ar
    if ar is None:   # keep durations in step with the files
        ar = {k: {"d": round(len(decode(AUD / "ar" / f"{k}.mp3")) / SR, 2), "h": v["h"]} for k, v in old["ar"].items()}
    man = {"version": c["meta"]["version"], "en": en, "ar": ar}
    (AUD / "manifest.json").write_text(json.dumps(man, ensure_ascii=False, indent=1), encoding="utf-8")


def set_record_words(failed: list[str]) -> None:
    """Extra cards for the studio page's Record tab: only the words that still fail (brief §7.2)."""
    p = ROOT / "tools" / "studio" / "state.json"
    s = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    keep = [i for i in s.get("record_extra", []) if i.get("kind") != "word"]
    s["record_extra"] = keep + [{"item": f"w-{w}", "kind": "word", "word": w} for w in failed]
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")


def main() -> None:
    import eleven
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="all", choices=["all", "en", "ph", "ar"])
    ap.add_argument("--no-retakes", action="store_true")
    ap.add_argument("--calibrate", action="store_true")
    ap.add_argument("--extra-retakes", default="", help="word=n,… retakes beyond the brief's two, approved by the user")
    ap.add_argument("--respell", default="", help="word=text:n,… n more tries with another text, approved by the user "
                                                  "(both are normally read from tools/word_choices.json)")
    ap.add_argument("--fix-arabic", action="store_true", help="re-make Arabic segments that fail a §7.4 check (≤ 2 retakes)")
    ap.add_argument("--retake-segments", default="", help="file with Arabic segments to re-make (one per line), e.g. after Whisper")
    a = ap.parse_args()
    extra = {k: int(n) for k, n in (p.split("=") for p in a.extra_retakes.split(",") if p)}
    respell = {k: (t.rsplit(":", 1)[0], int(t.rsplit(":", 1)[1])) for k, t in (p.split("=", 1) for p in a.respell.split(",") if p)}
    try:
        if a.calibrate:
            calibrate()
            return
        logp = ROOT / "tools" / "audio_build_log.json"
        log = json.loads(logp.read_text(encoding="utf-8")) if logp.exists() else {}
        if log.get("build") != "v1.1":
            log = {"build": "v1.1", "clips": {}}
        print(f"Credits left before (account counter): {eleven.credits_left(fresh=True)}")
        try:
            if a.fix_arabic or a.retake_segments:
                cal = calibration()
                segs = [s for s in Path(a.retake_segments).read_text(encoding="utf-8").splitlines() if s.strip()] if a.retake_segments else None
                print("Arabic retakes:")
                fix_arabic(log, use_context=not cal.get("context_billed", True), segments=segs)
                return
            if a.only in ("all", "en"):
                print("English words:")
                log["words_failed"] = build_words(log, retakes=not a.no_retakes, extra=extra, respell=respell)
                print("English phrases:")
                build_phrases(log)
            if a.only in ("all", "ph"):
                print("Letter sounds and blends (recordings):")
                build_phonemes_and_blends(log)
            man_ar = None
            if a.only in ("all", "ar"):
                cal = calibration()
                if cal.get("context_billed") is None:
                    raise Stop("run --calibrate first (checks whether previous_text/next_text are billed)")
                print(f"Arabic (context {'off: it is billed' if cal['context_billed'] else 'on: not billed'}):")
                man_ar = build_arabic(log, use_context=not cal["context_billed"])
            write_manifest(man_ar)
        finally:
            logp.write_text(json.dumps(log, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"Credits left after (this run's balance): {eleven.credits_left()}")
    except eleven.ElevenError as e:
        if "quota_exceeded" in e.detail:
            print(f"STOP: the ElevenLabs credits are used up. Everything made so far is cached. Reset: {eleven.reset_date()} (brief §4.6).")
        elif "detected_unusual_activity" in e.detail:
            print("STOP: ElevenLabs blocked the free tier on this network (VPN/proxy?). See brief §4.5.")
        elif e.status in (401, 403):
            print(f"STOP: permission problem – {e.detail} (the key needs Text to Speech, Voices read+write, User read).")
        else:
            print(f"STOP: {e}")
        sys.exit(2)


if __name__ == "__main__":
    main()
