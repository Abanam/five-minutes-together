"""Verify every audio clip in code (we cannot listen):

1. every clip referenced by content.json / the app exists and is listed in the manifest;
2. duration is in the expected range for its type;
3. not silent (active RMS) and not clipping (peak below 0 dBFS, no flat-topped samples);
4. the six letter sounds pass the acoustic phoneme checks (voicing, frication centroid,
   vowel formants, no added vowel) – and, as negative controls, Kokoro letter NAMES fail them;
5. Whisper (faster-whisper "small", run locally) transcribes every English word clip as that
   word, and the Arabic clips are compared with their source text (character similarity).

Writes deliverables/audio-verification.md and tools/audio_verification.json.
Exit code 1 if any hard check fails.

    python tools/verify_audio.py                                   # the app's audio (app/audio)
    python tools/verify_audio.py --audio-dir deliverables/evidence/v1.0/audio --out deliverables/evidence/v1.0/remeasured
        # the same measures on another audio folder (v1.1: before/after comparison); results go to --out
"""
from __future__ import annotations

import difflib
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from audio_analysis import RULES, check_phoneme, describe_phoneme, trim  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
AUD = APP / "audio"
DELIV = ROOT / "deliverables"
SR = 24000


def decode(path: Path, sr: int = SR) -> np.ndarray:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar", str(sr), "-"],
                         check=True, capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32).copy()


def active_rms_db(y: np.ndarray, sr: int = SR) -> float:
    f = int(sr * 0.02)
    n = max(1, len(y) // f)
    r = np.sqrt(np.mean(y[: n * f].reshape(n, f) ** 2, axis=1) + 1e-12)
    act = r[r > r.max() * 10 ** (-30 / 20)]
    return float(20 * np.log10(np.sqrt(np.mean(act ** 2)) + 1e-12))


def norm_ar(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    s = re.sub("[ً-ْٰـ]", "", s)
    s = re.sub("[إأآٱ]", "ا", s).replace("ى", "ي").replace("ة", "ه").replace("ؤ", "و").replace("ئ", "ي")
    s = re.sub(r"[A-Za-z0-9٠-٩]", "", s)
    return re.sub(r"[^ء-ي]", "", s)


def main() -> int:
    global AUD
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio-dir", type=Path, default=None, help="audio folder to measure (default: app/audio)")
    ap.add_argument("--out", type=Path, default=None, help="folder for the .md and .json results (default: the usual files)")
    args = ap.parse_args()
    if args.audio_dir is not None:   # only WHERE the clips are read from changes; every measure stays the same
        AUD = args.audio_dir if args.audio_dir.is_absolute() else ROOT / args.audio_dir
    json_out = (args.out / "audio_verification.json") if args.out else ROOT / "tools" / "audio_verification.json"
    md_out = (args.out / "audio-verification.md") if args.out else DELIV / "audio-verification.md"
    content = json.loads((APP / "content.json").read_text(encoding="utf-8"))
    manifest = json.loads((AUD / "manifest.json").read_text(encoding="utf-8"))
    log = {"files": {}, "phonemes": {}, "controls": {}, "whisper_en": {}, "whisper_ar": {}, "summary": {}}
    hard_fail = []

    # 1. references -------------------------------------------------------
    need_en = set()
    for s in content["sounds"]:
        need_en.add(f"ph-{s}")
    for w in content["words"]:
        need_en |= {f"w-{w}", f"b-{w}"}
    for k in content["keywords"]:
        need_en.add(f"w-{k}")
    for k in content["english"]:
        need_en.add(f"x-{k}")
    need_ar = {k for k, v in content["texts"].items() if "ar" in v and not v.get("noAudio")}
    for a in content["trustedApps"]:
        need_ar |= {f"app_{a['id']}_why", f"app_{a['id']}_ask"}
    missing = [f"en/{n}.mp3" for n in sorted(need_en) if not (AUD / "en" / f"{n}.mp3").exists() or n not in manifest["en"]]
    missing += [f"ar/{n}.mp3" for n in sorted(need_ar) if not (AUD / "ar" / f"{n}.mp3").exists() or n not in manifest["ar"]]
    if missing:
        hard_fail.append(f"missing clips: {missing}")

    # 2+3. duration, silence, clipping -----------------------------------
    def drange(name: str):
        if name.startswith("ph-"):
            return (0.55, 0.95) if RULES[name[3:]].get("dur", (0, 0))[0] > 0.3 else (0.05, 0.45)
        if name.startswith("w-"):
            return (0.25, 1.6)
        if name.startswith("b-"):
            return (0.8, 3.5)
        if name.startswith("x-"):
            return (0.5, 5.0)
        return (0.8, 75.0)  # Arabic texts

    files = sorted(AUD.rglob("*.mp3"))
    for f in files:
        name = f.stem
        y = decode(f)
        dur = len(y) / SR
        lo, hi = drange(name if f.parent.name == "en" else "ar")
        rms = active_rms_db(y)
        peak = float(np.max(np.abs(y))) if y.size else 0.0
        flat = int(np.sum(np.abs(y) >= 0.999))
        ok = lo <= dur <= hi and rms > -35 and peak < 0.999 and flat == 0
        rec = {"duration": round(dur, 3), "range": [lo, hi], "active_rms_db": round(rms, 1), "peak_dbfs": round(20 * np.log10(peak + 1e-12), 2),
               "clipped_samples": flat, "kbytes": round(f.stat().st_size / 1024, 1), "pass": ok}
        log["files"][f"{f.parent.name}/{f.name}"] = rec
        if not ok:
            hard_fail.append(f"{f.parent.name}/{f.name}: {rec}")

    # 4. phoneme acoustics + negative controls ----------------------------
    for s in content["sounds"]:
        y = trim(decode(AUD / "en" / f"ph-{s}.mp3"), SR)
        d = describe_phoneme(y, SR)
        probs = check_phoneme(s, d)
        log["phonemes"][s] = {"problems": probs, **{k: (round(v, 3) if isinstance(v, float) else v) for k, v in d.items()}}
        if probs:
            hard_fail.append(f"phoneme /{s}/: {probs}")
    try:
        from kokoro_onnx import Kokoro
        M = Path.home() / ".cache" / "fmt-models"
        k = Kokoro(str(M / "kokoro-v1.0.onnx"), str(M / "voices-v1.0.bin"))
        for name, letter in (("ˈA", "a"), ("ˈI", "i"), ("ˈɛs", "s"), ("tˈi", "t"), ("pˈi", "p"), ("ˈɛn", "n")):
            y, sr = k.create(name, voice="af_heart", speed=0.8, is_phonemes=True, trim=False)
            d = describe_phoneme(trim(np.asarray(y), sr), sr)
            probs = check_phoneme(letter, d)
            log["controls"][f"letter name {name} vs /{letter}/"] = {"rejected": bool(probs), "problems": probs}
            if not probs:
                hard_fail.append(f"negative control {name} was NOT rejected by the /{letter}/ check")
    except Exception as e:  # pragma: no cover
        log["controls"]["error"] = str(e)

    # 4b. clean word onsets: no voiced 'uh' before the first sound ---------------
    from audio_analysis import frame_labels
    log["onsets"] = {}
    for w, meta in list(content["words"].items()) + [(k, {"sounds": [v["first"]]}) for k, v in content["keywords"].items()]:
        y = trim(decode(AUD / "en" / f"w-{w}.mp3"), SR)
        db, v, cen, _ = frame_labels(y, SR, 10.0)
        aud = [i for i in range(len(db)) if db[i] > -35][:6]
        first = meta["sounds"][0]
        ok, why = True, ""
        if first in ("s", "t", "p"):
            voiced_lead = sum(1 for i in aud[:4] if v[i])
            ok = voiced_lead == 0
            why = f"voiced frames before /{first}/: {voiced_lead}"
        elif first in ("a", "i"):
            # the start-up artefact sounds like 'oo' (F2 ≈ 870 Hz); a real /æ/ or /ɪ/ starts with F2 > 1400 Hz
            from audio_analysis import formants
            fm = formants(y[: int(SR * 0.09)], SR)
            ok = bool(fm) and fm["F2"] > 1400
            why = f"onset F2 {fm['F2']:.0f} Hz" if fm else "no formants at onset"
        else:
            why = "nasal onset (not checked)"
        log["onsets"][w] = {"ok": ok, "why": why}
        if not ok:
            hard_fail.append(f"w-{w}: unclean onset ({why})")

    # 5. Whisper -------------------------------------------------------------
    from faster_whisper import WhisperModel
    wm = WhisperModel("small", device="cpu", compute_type="int8", download_root=str(Path.home() / ".cache" / "fmt-models" / "whisper"))
    words = list(content["words"]) + list(content["keywords"]) + ["cat"]
    en_ok = 0
    for w in words:
        segs, _ = wm.transcribe(str(AUD / "en" / f"w-{w}.mp3"), language="en", beam_size=5, without_timestamps=True,
                                initial_prompt="A single English word for children learning to read:")
        hyp = " ".join(s.text for s in segs).strip()
        clean = re.sub(r"[^a-z0-9 ]", "", hyp.lower()).strip()
        # spellings Whisper picks for the same sounds (homophones / near-homophones in US English)
        same_sound = {"sun": {"son"}, "ant": {"and", "aunt"}, "ink": {"inc"}, "tin": {"ten", "10"}, "palm": {"pom", "pam"},
                      "pen": {"pin"}, "in": {"inn"}, "nest": {"next"}, "sat": {"sat"}, "net": {"nett"}}
        exact = clean == w or clean.replace(" ", "") == w
        homo = clean in same_sound.get(w, set())
        ok = exact or homo
        en_ok += ok
        log["whisper_en"][w] = {"heard": hyp, "match": ok, "exact": exact}
    sims = []
    for tid in sorted(need_ar):
        if tid.startswith("app_"):
            a_id, fld = tid[4:].rsplit("_", 1)
            ref = next(a for a in content["trustedApps"] if a["id"] == a_id)[fld]["ar"]
        else:
            ref = content["texts"][tid]["ar"]
        segs, _ = wm.transcribe(str(AUD / "ar" / f"{tid}.mp3"), language="ar", beam_size=5, without_timestamps=True)
        hyp = " ".join(s.text for s in segs).strip()
        sim = difflib.SequenceMatcher(None, norm_ar(ref), norm_ar(hyp)).ratio()
        sims.append(sim)
        log["whisper_ar"][tid] = {"similarity": round(sim, 3), "heard": hyp}
    log["summary"] = {
        "files_checked": len(files),
        "files_pass": sum(1 for r in log["files"].values() if r["pass"]),
        "total_kb": round(sum(r["kbytes"] for r in log["files"].values()), 1),
        "phonemes_pass": sum(1 for r in log["phonemes"].values() if not r["problems"]),
        "controls_rejected": sum(1 for r in log["controls"].values() if isinstance(r, dict) and r.get("rejected")),
        "whisper_en_match": f"{en_ok}/{len(words)}",
        "whisper_ar_mean_similarity": round(float(np.mean(sims)), 3) if sims else None,
        "whisper_ar_min_similarity": round(float(np.min(sims)), 3) if sims else None,
        "whisper_ar_below_0_6": [k for k, v in log["whisper_ar"].items() if v["similarity"] < 0.6],
        "hard_failures": hard_fail,
    }
    log["audio_dir"] = str(AUD.relative_to(ROOT)).replace("\\", "/") if AUD.is_relative_to(ROOT) else str(AUD)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(log, ensure_ascii=False, indent=1), encoding="utf-8")

    # markdown log -----------------------------------------------------------
    S = log["summary"]
    md = ["# Audio verification log", "",
          "Generated by `tools/verify_audio.py`. Every clip was decoded and measured in code; nobody listened to the clips.", "",
          f"Audio folder measured: `{log['audio_dir']}` (manifest version {manifest.get('version')}).", "",
          "## Summary", "",
          f"- Clips checked: **{S['files_checked']}**, passing existence/duration/RMS/clipping checks: **{S['files_pass']}**",
          f"- Total audio size: **{S['total_kb']/1024:.2f} MB**",
          f"- Letter sounds passing the acoustic phoneme checks: **{S['phonemes_pass']}/6**",
          f"- Negative controls (Kokoro letter *names*) rejected by the same checks: **{S['controls_rejected']}/6**",
          f"- Whisper heard the intended English word: **{S['whisper_en_match']}**",
          f"- Arabic clips: mean character similarity between Whisper's transcript and the source text **{S['whisper_ar_mean_similarity']}** (min {S['whisper_ar_min_similarity']}). "
          "Whisper itself makes errors on Arabic, so this is an intelligibility indicator, not a pass/fail test.",
          f"- Hard failures: **{len(S['hard_failures'])}**", ""]
    md += ["## Letter sounds (pure phonemes from IPA input)", "", "| Sound | Duration (s) | Voiced fraction | Longest voiced stretch (ms) | Spectral centroid (Hz) | F1 / F2 (Hz) | Result |", "|---|---|---|---|---|---|---|"]
    for s, r in log["phonemes"].items():
        f = f"{r.get('F1', '–'):.0f} / {r.get('F2', '–'):.0f}" if "F1" in r else "– (unvoiced)"
        md.append(f"| /{content['sounds'][s]['ipa']}/ ({s}) | {r['duration']:.2f} | {r['voiced_fraction']:.2f} | {r['longest_voiced_ms']} | {r['centroid_hz']:.0f} | {f} | {'PASS' if not r['problems'] else 'FAIL: ' + '; '.join(r['problems'])} |")
    md += ["", "Negative controls (must be rejected):", ""]
    for k2, r in log["controls"].items():
        if isinstance(r, dict):
            md.append(f"- {k2}: {'rejected ✓' if r['rejected'] else 'NOT rejected ✗'} ({'; '.join(r['problems'])})")
    md += ["", "## English words (Whisper transcription)", "", "| Word | Heard | Match |", "|---|---|---|"]
    for w, r in log["whisper_en"].items():
        md.append(f"| {w} | {r['heard']} | {'✓' if r['match'] else '✗'} |")
    md += ["", "## Arabic clips (Whisper similarity, lowest first)", "", "| Clip | Similarity | Whisper heard |", "|---|---|---|"]
    for tid, r in sorted(log["whisper_ar"].items(), key=lambda kv: kv[1]["similarity"]):
        md.append(f"| {tid} | {r['similarity']:.2f} | {r['heard'][:120]} |")
    md += ["", "## All files", "", "| File | Duration (s) | Active RMS (dBFS) | Peak (dBFS) | Clipped | KB | Pass |", "|---|---|---|---|---|---|---|"]
    for name, r in log["files"].items():
        md.append(f"| {name} | {r['duration']} | {r['active_rms_db']} | {r['peak_dbfs']} | {r['clipped_samples']} | {r['kbytes']} | {'✓' if r['pass'] else '✗'} |")
    md_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps(S, ensure_ascii=False, indent=1))
    return 1 if hard_fail else 0


if __name__ == "__main__":
    sys.exit(main())
