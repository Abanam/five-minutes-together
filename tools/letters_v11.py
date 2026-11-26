"""v1.1 letter sounds made with ElevenLabs. The team's recordings were not good enough (a noisy room:
every /t/ take failed), so at the user's request the six pure sounds come from ElevenLabs too. A pure
sound is never a letter name: every candidate is checked with audio_analysis.check_phoneme and the
UNCHANGED RULES, exactly as a recorded take would have been.

    .venv/Scripts/python.exe tools/letters_v11.py        # make + check the candidates, recommend, update the studio page

Voices: the chosen English voice (George) and Alice, the female British default voice from the audition
(the RULES' vowel ranges were set for a female voice; George's /æ/ sits at their lower edge).
Candidates for each sound (eleven_multilingual_v2, the build's settings; some prompts at speed 0.7):
  prompt – a short text that asks for the sound ("Ssssss.", "Nnnnnnnnnnn.", "Bad.", "Iiiiink.", "Tea.", "Puh." …).
           For vowels the steady vowel is cut out; for stops the burst and aspiration before the vowel.
  word   – the sound cut out of words already made (no extra credits).
Continuous sounds shorter than 0.6 s are brought to 0.72 s as in v1.0 (noise grains for /s/; correlation-aligned
looping of the steady part for vowels and /n/); longer ones keep their steady middle (≤ 0.85 s).
Stops shorter than 0.12 s also get a variant whose natural aspiration is continued to 0.15 s with grains of
itself, decaying (labelled "aspiration lengthened"); the natural burst is never changed.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).parent))
import eleven  # noqa: E402
import make_audio as M  # noqa: E402
import make_audio_v11 as V  # noqa: E402
from audio_analysis import RULES, _runs, extract_fricative, extract_stop, frame_labels, trim  # noqa: E402
from v11_common import seed_for  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = V.WORK / "letters"
CHOSEN = OUT / "chosen"
STATE = ROOT / "tools" / "studio" / "state.json"
SR = V.SR
ALICE = ("Alice", "Xb7hH8MSUJpSbSDYk0k2")
VOICED = ("a", "i", "n")
# (text, speed): a slower speed and a following high or rounded vowel lengthen a stop's aspiration (longer VOT);
# British English lengthens /æ/ before a voiced consonant ("bad"); the vowel or the burst is cut out afterwards.
PROMPTS = {"s": [("Ssssss.", 0.9), ("Sssssun.", 0.9), ("Sssssssssss.", 0.9)],
           "a": [("Aaaaant.", 0.9), ("Aaaaapple.", 0.9), ("Bad.", 0.7), ("Baaaad.", 0.9), ("Caaaat.", 0.9)],
           "t": [("Tuh.", 0.9), ("Too.", 0.7), ("Tea.", 0.7), ("Two!", 0.9)],
           "p": [("Puh.", 0.9), ("Pooh.", 0.7), ("Pea.", 0.7), ("Pool!", 0.9)],
           "i": [("Iiiiink.", 0.9), ("Iiiiinsect.", 0.9), ("Biiiit.", 0.9)],
           "n": [("Nnnnnn.", 0.9), ("Nnnnnnet.", 0.9), ("Nnnnnnnnnnn.", 0.9)]}
# Alice also gets prompts that tend to give a naturally LONG vowel or murmur (the user asked for an /æ/ with no
# looping: a looped vowel sounds mechanical), e.g. a drawn-out "Daaaaad!" or "Baaaaad." said slowly.
ALICE_PROMPTS = {"s": [("Sssssun.", 0.9)],
                 "a": [("Bad.", 0.7), ("Aaaaant.", 0.9), ("Baaaad.", 0.9), ("Daaaaad!", 0.9), ("Baaaaaad.", 0.7),
                       ("Saaaaad.", 0.9), ("Haaaaand.", 0.9), ("Aaaaand…", 0.7)],
                 "t": [("Tea.", 0.7), ("Tuh.", 0.9)], "p": [("Pea.", 0.7), ("Puh.", 0.9)],
                 "i": [("Iiiiink.", 0.9), ("Biiiit.", 0.9), ("Iiiiiit.", 0.7), ("Ihhhhh.", 0.9),
                       # the vowel held inside a word that has /ɪ/, so it stays lax ("i" as in it), not "ee"
                       ("Fiiiiish.", 0.9), ("Biiiiig.", 0.9), ("Hiiiiiss.", 0.9), ("Siiiiit.", 0.9)],
                 "n": [("Nnnnnnnnnnn.", 0.9), ("Nnnnnnnnnnnnnnnn.", 0.9), ("Nnnnnnnnnnn…", 0.7)]}
NO_LOOP = {"a"}   # sounds for which a looped candidate is never offered (the user's decision)
WORDS = {"s": ["sun", "sand", "sat", "sip", "sit"], "t": ["tap", "tip", "tin", "tent", "tomato"],
         "p": ["pat", "pan", "pin", "pit", "pen", "palm"], "a": ["at", "ant", "apple", "sat", "tap", "nap", "pat", "cat"],
         "i": ["it", "in", "ink", "insect", "sit", "sip", "tip", "pin", "tin", "pit"],
         "n": ["nap", "net", "nest", "in", "pin", "tin", "pan"]}


def voices() -> list[tuple[str, str]]:
    en = V.voices()["english"]
    return [(en["name"], en["voice_id"])] + ([ALICE] if en["voice_id"] != ALICE[1] else [])


def word_sources(word: str, vid: str) -> list[tuple[str, int, Path]]:
    """The ElevenLabs MP3s already made for a word with this voice (every retake that exists)."""
    out = []
    for r in range(3):
        p = eleven.CACHE / "tts" / (eleven.tts_key(f"{word}.", vid, seed_for(f"w-{word}", r)) + ".mp3")
        if p.exists():
            out.append((f"{word}.", r, p))
    return out


def inner(lo: float, hi: float, k: float = 0.05) -> tuple[float, float]:
    w = hi - lo
    return lo + k * w, hi - k * w


def steady_vowel(y: np.ndarray, letter: str) -> np.ndarray | None:
    """Longest run of voiced, loud frames whose F1/F2 lie inside the RULES ranges (5 % margin)."""
    (f1lo, f1hi), (f2lo, f2hi) = inner(*RULES[letter]["F1"]), inner(*RULES[letter]["F2"])
    fr, hop = M._frame_formants(y)
    ok = np.array([bool(v) and d > -18 and f1lo <= f1 <= f1hi and f2lo <= f2 <= f2hi for f1, f2, d, v in fr], bool)
    for i in range(1, len(ok) - 1):          # allow single-frame dropouts inside a run
        if not ok[i] and ok[i - 1] and ok[i + 1]:
            ok[i] = True
    runs = [r for r in _runs(ok) if (r[1] - r[0]) * 10 >= 70]
    if not runs:
        return None
    a, b = max(runs, key=lambda r: r[1] - r[0])
    return y[a * hop:(b + 2) * hop]


def long_vowel(y: np.ndarray, letter: str) -> np.ndarray | None:
    """The whole drawn-out vowel of a prompt like "Haaaaand.": the longest run of voiced, loud frames in the broad
    region of that vowel (/æ/: F1 ≥ 600 and F2 ≥ 1400 Hz; /ɪ/: F1 ≤ 500 and F2 ≥ 1800 Hz). check_phoneme (RULES
    unchanged) then judges the segment as a whole – median formants and how much they move."""
    fr, hop = M._frame_formants(y)
    if letter == "a":
        ok = [bool(v) and d > -20 and f1 >= 600 and f2 >= 1400 for f1, f2, d, v in fr]
    else:
        ok = [bool(v) and d > -20 and f1 <= 500 and f2 >= 1800 for f1, f2, d, v in fr]
    ok = np.array(ok, bool)
    for i in range(1, len(ok) - 1):
        if not ok[i] and ok[i - 1] and ok[i + 1]:
            ok[i] = True
    runs = [r for r in _runs(ok) if (r[1] - r[0]) * 10 >= 150]
    if not runs:
        return None
    a, b = max(runs, key=lambda r: r[1] - r[0])
    return y[a * hop:(b + 2) * hop]


def nasal(y: np.ndarray, where: str) -> np.ndarray | None:
    """The /n/ murmur: voiced, loud, low-centroid frames at the start, the end, or the longest run (≥ 50 ms)."""
    db, v, cen, hop = frame_labels(y, SR, 10.0)
    runs = [r for r in _runs(v & (db > -30) & (cen < 900)) if r[1] - r[0] >= 5]
    if not runs:
        return None
    a, b = runs[0] if where == "start" else runs[-1]
    if where == "longest":
        a, b = max(runs, key=lambda r: r[1] - r[0])
    return y[a * hop: b * hop + int(0.02 * SR)]


def cut(letter: str, y: np.ndarray, source: str) -> list[tuple[str, np.ndarray]]:
    """[(how, segment)] for one source clip."""
    y = trim(y, SR, top_db=45, pad_ms=10)
    if letter == "s":
        seg = extract_fricative(y, SR)
        return [("frication", seg)] if len(seg) > 0.06 * SR else []
    if letter in ("t", "p"):
        seg = extract_stop(y, SR)
        return [("burst + aspiration", seg)] if len(seg) > 0.03 * SR else []
    if letter in ("a", "i"):
        out = []
        seg = steady_vowel(y, letter)
        if seg is not None:
            out.append(("steady vowel", seg))
        whole = long_vowel(y, letter)
        if whole is not None and (seg is None or len(whole) > len(seg) + int(0.05 * SR)):
            out.append(("whole drawn-out vowel", whole))
        return out
    # "Nnnnnn." is all murmur; "Nnnnnnet."/nap/net/nest start with it; in/pin/tin/pan end with it
    where = "longest" if source.startswith(("Nnnnnn.", "Nnnnnnnnnnn.")) else "start" if source.lower().startswith("n") else "end"
    seg = nasal(y, where)
    return [(f"murmur ({where})", seg)] if seg is not None else []


def time_stretch(seg: np.ndarray, target: float) -> np.ndarray:
    """Slow a natural segment down to `target` seconds with FFmpeg's atempo (overlap-add; pitch and formants kept).
    Used only for small factors (natural part ≥ 0.4 s), so no part is audibly repeated."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "pipe:0",
                          "-filter:a", f"atempo={len(seg) / SR / target:.4f}", "-f", "f32le", "-ar", str(SR), "-ac", "1", "pipe:1"],
                         input=seg.astype(np.float32).tobytes(), capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).copy()


def lengthen(letter: str, seg: np.ndarray) -> tuple[np.ndarray, str] | None:
    """(audio, note) for a cut segment; None if the only way to reach 0.6 s would be looping a sound in NO_LOOP."""
    if letter in ("t", "p") or len(seg) >= int(0.6 * SR):
        return seg, ""
    if letter == "s":
        return M.stretch_noise(seg, 0.72), " → lengthened to 0.72 s (noise grains)"
    if len(seg) >= int(0.4 * SR):
        return time_stretch(seg, 0.65), f" → slowed from {len(seg) / SR:.2f} s to 0.65 s (time-stretch, no looping)"
    if letter in NO_LOOP:
        return None
    return M.sustain(seg, 0.72), " → lengthened to 0.72 s (looped steady part)"


def extend_aspiration(seg: np.ndarray, target: float = 0.15) -> np.ndarray | None:
    """Keep the whole natural burst + aspiration and continue the aspiration with grains of itself, decaying."""
    b = int(0.012 * SR)
    if len(seg) >= int(0.12 * SR) or len(seg) < b + int(0.025 * SR):
        return None
    asp = seg[b:]
    xf = int(0.005 * SR)
    n = int(target * SR) - len(seg) + xf
    g = int(0.012 * SR)
    rng = np.random.default_rng(11)
    grains = np.zeros(n + g)
    w = np.hanning(g)
    for i in range(0, n, g // 2):
        s = int(rng.integers(0, max(1, len(asp) - g)))
        grains[i:i + g] += asp[s:s + g] * w[: len(asp[s:s + g])]
    grains = grains[:n]
    ref = float(np.sqrt(np.mean(seg[-int(0.015 * SR):] ** 2))) + 1e-9
    grains *= ref / (float(np.sqrt(np.mean(grains[: int(0.015 * SR)] ** 2))) + 1e-9)
    grains *= np.exp(np.linspace(0, np.log(0.08), n))          # dies away like a natural aspiration (-22 dB)
    f = np.linspace(0, 1, xf)
    return np.concatenate([seg[:-xf], seg[-xf:] * (1 - f) + grains[:xf] * f, grains[xf:]]).astype(np.float32)


def candidates(letter: str) -> list[dict]:
    """Paid prompts (a few credits each) and free cuts from words already made, for every voice."""
    found = []
    for vname, vid in voices():
        sources = []
        for text, speed in (PROMPTS if vname != ALICE[0] else ALICE_PROMPTS)[letter]:
            settings = dict(eleven.SETTINGS, speed=speed)
            seed_item = f"ph-{letter}:{text}" if vname != ALICE[0] else f"ph-{letter}:{text}:alice"
            mp3, cached, used = eleven.tts(f"ph-{letter} prompt ({vname})", text, vid, seed_for(seed_item), settings=settings)
            sources.append(("prompt", text if speed == eleven.SETTINGS["speed"] else f"{text} (speed {speed})", 0, mp3, used, cached))
        for w in WORDS[letter]:
            for text, r, mp3 in word_sources(w, vid):
                sources.append(("word", text, r, mp3, 0, True))
        for kind, text, r, mp3, used, cached in sources:
            for how, seg in cut(letter, V.decode(mp3), text):
                variants = [x for x in [lengthen(letter, seg)] if x is not None]
                if letter in ("t", "p"):
                    ext = extend_aspiration(seg)
                    if ext is not None:
                        variants.append((ext, f" → aspiration lengthened to 0.15 s (natural part {len(seg) / SR:.3f} s)"))
                for src, note in variants:
                    shaped = V.shape_phoneme(src, letter)
                    d, probs = V.check_take(shaped, letter)
                    found.append({"voice": vname, "voice_id": vid, "kind": kind, "text": text, "retake": r, "how": how + note,
                                  "lengthened": bool(note), "looped": "looped" in note,
                                  "source_seconds": round(len(seg) / SR, 3), "credits": used,
                                  "cached": cached, "src": src, "shaped": shaped,
                                  "measures": {k: (round(v, 3) if isinstance(v, float) else v) for k, v in d.items()},
                                  "problems": probs, "ok": not probs})
                    used = 0
    return found


# Reference vowel formants (Peterson & Barney 1952, adult averages): the candidate closest to the vowel the
# child should hear wins, so a long /ɪ/ that drifts towards "ee" (/iː/) or an /æ/ that drifts towards "ah" loses.
TARGET = {"female": {"a": (860, 2050), "i": (430, 2480)}, "male": {"a": (660, 1720), "i": (390, 1990)}}
GENDER = {"Alice": "female", "George": "male", "Daniel": "male"}


def rank(letter: str, c: dict, voiced_voice: str) -> tuple:
    m = c["measures"]
    if letter in ("t", "p"):
        # no voicing at all, then a burst + aspiration near 0.15 s (a natural one before a lengthened one),
        # then the longer natural part; unvoiced sounds carry little of the voice, so any voice may win
        return (c["ok"], m["voiced_fraction"] == 0, -abs(min(m["duration"], 0.30) - 0.15) - (0.02 if c["lengthened"] else 0),
                c["source_seconds"])
    if letter == "s":
        return (c["ok"], not c["lengthened"], min(c["source_seconds"], 0.6), c["kind"] == "prompt", -m["voiced_fraction"])
    same = c["voice"] == voiced_voice     # a, i, n carry pitch and timbre and meet in the blends: one voice for all three
    natural = 2 if not c["lengthened"] else 1 if not c.get("looped") else 0   # natural > gently slowed > looped
    if letter in ("a", "i"):
        t1, t2 = TARGET[GENDER.get(c["voice"], "female")][letter]
        dist = abs(m.get("F1", 0) - t1) / t1 + abs(m.get("F2", 0) - t2) / t2
        # the right vowel first (a held /ɪ/ that drifts towards "ee" is wrong for the child), then no looping
        return (c["ok"], dist <= 0.2, natural > 0, same, -round(dist, 1), natural, min(c["source_seconds"], 0.6))
    return (c["ok"], natural > 0, same, natural, min(c["source_seconds"], 0.6), c["kind"] == "prompt", m["low_ratio_0_500"])


def media(p: Path) -> str:
    return "/media/" + str(p.resolve().relative_to(ROOT)).replace("\\", "/")


def choose(letter: str, k: int, state: dict | None = None) -> dict:
    """Copy candidate k to letters/chosen/ph-<letter>.wav (+ .json with its source) and mark it in the state."""
    state = state if state is not None else json.loads(STATE.read_text(encoding="utf-8"))
    info = state["letters"][letter]["candidates"][k]
    if not info["ok"]:
        raise ValueError("only a candidate that passes the checks can be used")
    CHOSEN.mkdir(parents=True, exist_ok=True)
    (CHOSEN / f"ph-{letter}.wav").write_bytes((OUT / f"{letter}-{k}-src.wav").read_bytes())
    (CHOSEN / f"ph-{letter}.json").write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding="utf-8")
    state["letters"][letter]["chosen"] = k
    return state


def main() -> None:
    c = V.load_content()
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    chars = sum(len(t) for v in PROMPTS.values() for t, _ in v) + sum(len(t) for v in ALICE_PROMPTS.values() for t, _ in v)
    print(f"Credits left (account counter): {eleven.credits_left()} – prompts send at most {chars} characters "
          "(cached ones cost nothing); word cuts are free")
    OUT.mkdir(parents=True, exist_ok=True)
    found = {letter: candidates(letter) for letter in c["sounds"]}
    # one voice for the voiced sounds (a, i, n carry the voice's pitch and timbre; the blends join them)
    names = [v for v, _ in voices()]
    full = [v for v in names if all(any(x["ok"] and x["voice"] == v for x in found[l]) for l in VOICED)]
    voiced_voice = full[0] if full else names[0]
    letters = {}
    for letter, rows in found.items():
        rows.sort(key=lambda x: rank(letter, x, voiced_voice), reverse=True)
        out = []
        for k, f in enumerate(rows):
            sf.write(OUT / f"{letter}-{k}-src.wav", f.pop("src"), SR, subtype="PCM_16")
            sf.write(OUT / f"{letter}-{k}.wav", f.pop("shaped"), SR, subtype="PCM_16")
            f.update(n=k, url=media(OUT / f"{letter}-{k}.wav"), recommended=(k == 0 and f["ok"]))
            out.append(f)
        letters[letter] = {"candidates": out, "chosen": None}
    state["letters"] = letters
    state["letters_voice"] = voiced_voice
    for letter in c["sounds"]:
        rows = letters[letter]["candidates"]
        if rows and rows[0]["ok"]:
            choose(letter, 0, state)
        best = rows[0] if rows else None
        print(f"  /{letter}/ {sum(r['ok'] for r in rows)}/{len(rows)} pass; recommended: "
              + (f"{best['voice']} {best['kind']} {best['text']!r} ({best['how']}), {best['measures']['duration']:.2f} s"
                 if best and best["ok"] else "NONE"))
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Voice for the voiced sounds (a, i, n): {voiced_voice}. Credits left (account counter): {eleven.credits_left()}")


if __name__ == "__main__":
    main()
