"""deliverables/audio-comparison-v1.0-v1.1.md (brief §8.3): v1.0 against v1.1, measured with the same unchanged
tools/verify_audio.py (v1.0 re-measured with --audio-dir). Every number is read from the measurement files.

    .venv/Scripts/python.exe tools/compare_audio_v11.py
"""
from __future__ import annotations

import json
import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
EVID = ROOT / "deliverables" / "evidence" / "v1.0"
A = json.loads((EVID / "remeasured" / "audio_verification.json").read_text(encoding="utf-8"))   # v1.0
B = json.loads((ROOT / "tools" / "audio_verification.json").read_text(encoding="utf-8"))         # v1.1
LOG = json.loads((ROOT / "tools" / "audio_build_log.json").read_text(encoding="utf-8"))
CONTENT = json.loads((ROOT / "app" / "content.json").read_text(encoding="utf-8"))
OUT = ROOT / "deliverables" / "audio-comparison-v1.0-v1.1.md"
SOUNDS = [("s", "/s/"), ("a", "/æ/"), ("t", "/t/"), ("p", "/p/"), ("i", "/ɪ/"), ("n", "/n/")]


def cache_mb(app: Path) -> float:
    s = (app / "sw-files.js").read_text(encoding="utf-8")
    files = json.loads(s.split("self.FMT_FILES = ", 1)[1].rstrip().rstrip(";"))
    return sum((app / f).stat().st_size for f in files if f != "./") / 1024 / 1024


def audio_mb(folder: Path) -> float:
    return sum(p.stat().st_size for p in folder.rglob("*.mp3")) / 1024 / 1024


def ar_stats(v: dict) -> dict:
    sims = [x["similarity"] for x in v["whisper_ar"].values()]
    dur = sum(r["duration"] for k, r in v["files"].items() if k.startswith("ar/"))
    return {"mean": statistics.mean(sims), "median": statistics.median(sims), "min": min(sims), "below": sum(s < 0.80 for s in sims),
            "n": len(sims), "seconds": dur, "argmin": min(v["whisper_ar"], key=lambda k: v["whisper_ar"][k]["similarity"])}


def ref_text(k: str) -> str:
    if k.startswith("app_"):
        a, f = k[4:].rsplit("_", 1)
        return next(x for x in CONTENT["trustedApps"] if x["id"] == a)[f]["ar"]
    return CONTENT["texts"][k]["ar"]


def no_autojunk(v: dict) -> dict:
    """Supplementary: the same similarity on the same Whisper transcripts with difflib's automatic junk heuristic off.
    (SequenceMatcher treats characters that make up more than 1 % of a text of 200+ characters as 'junk', which can
    collapse the score of a long, correctly heard clip.) verify_audio.py itself stays unchanged."""
    import difflib
    from verify_audio import norm_ar
    s = {k: difflib.SequenceMatcher(None, norm_ar(ref_text(k)), norm_ar(r["heard"]), autojunk=False).ratio() for k, r in v["whisper_ar"].items()}
    return {"per_clip": s, "mean": statistics.mean(s.values()), "median": statistics.median(s.values()), "min": min(s.values()),
            "argmin": min(s, key=s.get), "below": sum(x < 0.80 for x in s.values())}


def credits() -> dict:
    import eleven
    rows = json.loads(eleven.USAGE_JSON.read_text(encoding="utf-8")) if eleven.USAGE_JSON.exists() else []
    s = eleven.subscription()
    return {"api_calls": len(rows), "api_credits": sum(r.get("credits_used") or 0 for r in rows), "tier": s.get("tier"),
            "left": int(s["character_limit"]) - int(s["character_count"]), "reset": eleven.reset_date()}


def main() -> None:
    a, b = ar_stats(A), ar_stats(B)
    ja, jb = no_autojunk(A), no_autojunk(B)
    cr = credits()
    words = list(CONTENT["words"]) + list(CONTENT["keywords"]) + ["cat"]
    voices = json.loads((ROOT / "tools" / "voices.json").read_text(encoding="utf-8"))
    letters = {s: LOG["clips"].get(f"en/ph-{s}.mp3", {}) for s, _ in SOUNDS}
    letter_src = "; ".join(f"{ipa} {letters[s].get('voice', '?')} ({letters[s].get('kind', '?')} “{letters[s].get('text_sent', '?')}”)" for s, ipa in SOUNDS)
    d = lambda v, s: v["phonemes"][s]["duration"]  # noqa: E731  (trimmed duration, as measured by describe_phoneme)
    wa, wb = A["summary"]["whisper_en_match"], B["summary"]["whisper_en_match"]
    md = ["# Audio comparison: version 1.0 and version 1.1", "",
          "Both versions were measured with the same, unchanged `tools/verify_audio.py` (Whisper \"small\", the same prompt, "
          "homophone list and similarity measure). Version 1.0 was re-measured from `deliverables/evidence/v1.0/audio` with the new "
          "`--audio-dir` option, which changes only where the clips are read from. Nobody judged the clips by ear for these numbers.", "",
          "## Main table", "", "| Measure | Version 1.0 | Version 1.1 |", "|---|---|---|",
          f"| Letter sounds passing the acoustic checks | {A['summary']['phonemes_pass']}/6 | {B['summary']['phonemes_pass']}/6 |"]
    for s, ipa in SOUNDS:
        md.append(f"| Duration of {ipa} (s, trimmed) | {d(A, s):.2f} | {d(B, s):.2f} |")
    md += [f"| Negative controls (letter names) rejected | {A['summary']['controls_rejected']}/6 | {B['summary']['controls_rejected']}/6 |",
           f"| Whisper heard the intended word (27 words) | {wa} | {wb} |",
           f"| Hard failures in `verify_audio.py` | {'; '.join(A['summary']['hard_failures']) or 'none'} | {'; '.join(B['summary']['hard_failures']) or 'none'} |",
           f"| Arabic Whisper similarity: mean / median / min (n = {b['n']}) | {a['mean']:.3f} / {a['median']:.3f} / {a['min']:.3f} | {b['mean']:.3f} / {b['median']:.3f} / {b['min']:.3f} |",
           f"| Arabic clips below 0.80 | {a['below']} | {b['below']} |",
           f"| Lowest Arabic clip | {a['argmin']} ({a['min']:.3f}) | {b['argmin']} ({b['min']:.3f}) |",
           f"| *Supplementary:* the same similarity with difflib's autojunk off – mean / median / min | {ja['mean']:.3f} / {ja['median']:.3f} / {ja['min']:.3f} ({ja['argmin']}) | {jb['mean']:.3f} / {jb['median']:.3f} / {jb['min']:.3f} ({jb['argmin']}) |",
           f"| *Supplementary:* clips below 0.80 with autojunk off | {ja['below']} | {jb['below']} |",
           f"| Total Arabic duration (s) | {a['seconds']:,.0f} | {b['seconds']:,.0f} |",
           f"| Total audio size (MB) | {audio_mb(EVID / 'audio'):.2f} | {audio_mb(ROOT / 'app' / 'audio'):.2f} |",
           f"| Offline cache (MB) | {cache_mb(ROOT / 'app' / 'v1.0'):.2f} | {cache_mb(ROOT / 'app'):.2f} |",
           "| Sources and voices | English: Kokoro-82M (af_heart); /t/: espeak-ng; Arabic: Meta MMS-TTS (16 kHz) | "
           f"ElevenLabs Multilingual v2. Words and phrases: {voices['english']['name']} (default voice). Arabic: "
           f"\"{voices['arabic']['name']}\" (Voice Design). Letter sounds: {letter_src} |",
           f"| ElevenLabs credits used | – | {cr['api_credits']:,} through the API ({cr['api_calls']} calls, exact per-call charges, "
           f"see `elevenlabs-usage.md`), plus Voice Design on the ElevenLabs website. Free plan (10,000 credits) until the account "
           f"owner upgraded it to {str(cr['tier']).capitalize()} during the build; balance now {cr['left']:,} credits, renewing {cr['reset'][:10]} |", ""]
    md += ["## English words (Whisper \"small\")", "", "| Word | v1.0 heard | v1.1 heard |", "|---|---|---|"]
    for w in words:
        x, y = A["whisper_en"].get(w, {}), B["whisper_en"].get(w, {})
        md.append(f"| {w} | {x.get('heard', '–')} {'✓' if x.get('match') else '✗'} | {y.get('heard', '–')} {'✓' if y.get('match') else '✗'} |")
    md += ["", "## Arabic clips (sorted by the v1.0 similarity)", "",
           "Official measure (unchanged `verify_audio.py`); the last two columns are the supplementary measure with difflib's autojunk off.", "",
           "| Clip | v1.0 | v1.1 | Change | v1.0 (autojunk off) | v1.1 (autojunk off) |", "|---|---|---|---|---|---|"]
    for k in sorted(A["whisper_ar"], key=lambda k: A["whisper_ar"][k]["similarity"]):
        x = A["whisper_ar"][k]["similarity"]
        y = B["whisper_ar"].get(k, {}).get("similarity")
        extra = f" {ja['per_clip'][k]:.3f} | {jb['per_clip'].get(k, float('nan')):.3f} |"
        md.append(f"| {k} | {x:.3f} | {y:.3f} | {y - x:+.3f} |" + extra if y is not None else f"| {k} | {x:.3f} | – | – |" + extra)
    md += ["", "### Why two v1.1 clips score low", "",
           f"- **{b['argmin']}** ({b['min']:.3f} official): Whisper's transcript matches the text almost word for word "
           f"(\"{B['whisper_ar'][b['argmin']]['heard'][:90]}…\"). The score collapses because difflib's `SequenceMatcher` "
           f"(default `autojunk=True`) ignores the most common letters of a text of 200 or more characters; with autojunk "
           f"off the same transcript scores {jb['per_clip'][b['argmin']]:.3f}. The same effect lowered `about_purpose` in v1.0 "
           f"({A['whisper_ar']['about_purpose']['similarity']:.3f} official, {ja['per_clip']['about_purpose']:.3f} with autojunk off).",
           f"- **ask_d4_in** ({B['whisper_ar']['ask_d4_in']['similarity']:.3f}): the clip contains the English word *in* and the held "
           f"sounds /ɪ/ and /n/; Whisper (asked for Arabic) writes them as Arabic letters (\"{B['whisper_ar']['ask_d4_in']['heard']}\"), "
           "while the reference text loses its Latin letters before the comparison. A new Arabic take would not change this.",
           "- No retake was made for these two clips: neither is a pronunciation fault of the Arabic voice.", ""]
    md += ["", "## Widened phoneme ranges", "",
           "None. All six v1.1 letter sounds pass `audio_analysis.RULES` unchanged, before and after MP3 encoding.", "",
           "## Notes on method", "",
           "- Letter sounds: the team's recordings failed the checks (a noisy room; every /t/ take failed), so at the user's request "
           "the six sounds were made with ElevenLabs. Each sound was cut from a short prompt or word; continuous sounds shorter than "
           "0.6 s were lengthened to 0.72 s as in v1.0, and a stop shorter than 0.12 s could have its natural aspiration continued "
           "to 0.15 s (see `tools/audio_build_log.json` for each sound's source and method).",
           "- Arabic speaking rate = characters sent (letters, spaces, punctuation; no harakat) per second of speech.",
           "- \"pan\": five ElevenLabs tries (the brief's two retakes plus two approved by the team). Two were heard as \"pan\" "
           "but their /p/ has almost no aspiration (voicing starts about 10 ms after the burst), so they fail the unchanged "
           "onset check; three had a clear /p/ but were heard as \"pun\"/\"pum\". The app uses try 0 (heard as \"pan\").",
           "- The optional check with a large Whisper model (§8.1.3) was not run: on this PC's CPU it would take well over "
           "30 minutes for both versions.", ""]
    para = (f"Version 1.1 replaced the synthetic voices of version 1.0 with ElevenLabs voices (Multilingual v2). With the same "
            f"unchanged checks, Whisper recognised {wb.split('/')[0]} of 27 English words (v1.0: {wa.split('/')[0]}). "
            f"{B['summary']['phonemes_pass']} of 6 letter sounds passed the acoustic checks (v1.0: {A['summary']['phonemes_pass']}), "
            f"and {B['summary']['controls_rejected']} of 6 letter-name controls were rejected. /t/ and /p/ now last "
            f"{d(B, 't'):.2f} s and {d(B, 'p'):.2f} s (v1.0: {d(A, 't'):.2f} s and {d(A, 'p'):.2f} s). The mean Whisper similarity "
            f"of the {b['n']} Arabic clips changed from {a['mean']:.3f} to {b['mean']:.3f}, and clips below 0.80 from {a['below']} to "
            f"{b['below']}; the lowest v1.1 score ({b['min']:.3f}) is a scoring artefact, as Whisper's transcript of that clip matches "
            f"the text. The total Arabic duration changed from {a['seconds']:,.0f} s to {b['seconds']:,.0f} s.")
    n = len(re.findall(r"\S+", para))
    md += ["## Paragraph for the report", "", para, "", f"({n} words)", ""]
    OUT.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}; paragraph {n} words")
    if n > 120:
        print("WARNING: the paragraph is longer than 120 words")


if __name__ == "__main__":
    main()
