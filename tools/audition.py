"""Voice audition for v1.1 (results are shown in the studio page, "Voices" tab).

    python tools/audition.py english          # 3 default British voices x the 5 words that failed in v1.0, + Whisper
    python tools/audition.py arabic-design    # Voice Design: 3 Arabic previews (one run)
    python tools/audition.py arabic-lines     # after the choice: save the voice, make hear_L1 and tip_p

Every clip uses exactly the text, seed and settings of the final build, so the chosen voice's clips are reused
(nothing is paid for twice). The choices are written to tools/voices.json (names, IDs, model, settings; never the key).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import eleven  # noqa: E402
from v11_common import ENGLISH_PROMPT, seed_for, whisper_word_ok  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "tools" / "studio" / "state.json"
VOICES = ROOT / "tools" / "voices.json"
SHORTLIST = [  # default (premade) voices, British English, adult, clear (GET /v1/voices, category "premade")
    {"name": "Alice", "voice_id": "Xb7hH8MSUJpSbSDYk0k2", "gender": "female", "about": "British, female, middle-aged – \"Clear, Engaging Educator\""},
    {"name": "George", "voice_id": "JBFqnCBsd6RMkjVDRZzb", "gender": "male", "about": "British, male, middle-aged – \"Warm, Captivating Storyteller\""},
    {"name": "Daniel", "voice_id": "onwK4e9ZLuTAKqWW03F9", "gender": "male", "about": "British, male, middle-aged – \"Steady Broadcaster\""},
]
WORDS = ["sat", "sip", "tip", "sun", "sand"]
AR_DESCRIPTION = ("A warm, kind Omani woman in her early thirties, an experienced Grade 1 teacher in Oman, speaking gently "
                  "to parents at home. Native Omani Gulf Arabic accent while reading clear, simple Modern Standard Arabic. "
                  "Calm, reassuring and encouraging; moderate, slightly slow pace; very clear consonants; clean studio "
                  "recording with no background noise or music.")
AR_PREVIEW_TEXT = ("مرحبًا بكم. في خمس دقائق كل يوم، يتعلّم طفلك أصوات الحروف الإنجليزية معك في البيت. "
                   "اسأل طفلك: ما أول صوت في الكلمة؟ ضع يدك أمام فمك لتشعر بالهواء، وشجّعه بعد كل محاولة.")
AR_VOICE_NAME = "Five Minutes Together – Omani teacher (Arabic)"


def load_state() -> dict:
    return json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}


def save_state(s: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")


def media(p: Path) -> str:
    return "/media/" + str(Path(p).resolve().relative_to(ROOT)).replace("\\", "/")


def write_voices_json(state: dict) -> None:
    """tools/voices.json: what the build uses. Names, IDs, model and settings only – never the key."""
    out = json.loads(VOICES.read_text(encoding="utf-8")) if VOICES.exists() else {}
    out.update({"model": eleven.MODEL, "output_format": "mp3_44100_128"})
    en = state.get("english", {})
    if en.get("chosen"):
        v = next(x for x in en["voices"] if x["voice_id"] == en["chosen"])
        out["english"] = {"name": v["name"], "voice_id": v["voice_id"], "category": "premade (default voice)", "about": v["about"],
                          "model": eleven.MODEL, "settings": eleven.SETTINGS,
                          "audition": {"words": WORDS, "whisper_score": f"{v['score']}/{len(WORDS)}"}}
    ar = state.get("arabic", {})
    if ar.get("voice_id") and ar.get("mode") == "website":
        info = ar.get("voice_info") or {}
        out["arabic"] = {"name": info.get("name") or AR_VOICE_NAME, "voice_id": ar["voice_id"],
                         "category": f"{info.get('category') or 'generated'} (Voice Design on the ElevenLabs website)",
                         "how": WEBSITE_NOTE, "description": ar["description"], "preview_text": ar["preview_text"],
                         "model": eleven.MODEL, "settings": eleven.SETTINGS, "approved": bool(ar.get("approved"))}
    elif ar.get("voice_id"):
        out["arabic"] = {"name": AR_VOICE_NAME, "voice_id": ar["voice_id"], "category": "generated (Voice Design)",
                         "design_model": ar.get("design_model", "eleven_multilingual_ttv_v2"), "description": ar["description"],
                         "preview_text": ar["preview_text"], "chosen_preview": ar["chosen_preview"],
                         "generated_voice_id": next(p["generated_voice_id"] for p in ar["previews"] if p["n"] == ar["chosen_preview"]),
                         "model": eleven.MODEL, "settings": eleven.SETTINGS, "approved": bool(ar.get("approved"))}
    VOICES.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")


def english() -> None:
    from make_audio_v11 import process_english, whisper   # the same processing and Whisper settings as the final build
    state = load_state()
    chars = sum(len(w) + 1 for w in WORDS) * len(SHORTLIST)
    print(f"Credits left before: {eleven.credits_left()} – this batch sends at most {chars} characters (cached clips cost nothing)")
    voices = []
    for v in SHORTLIST:
        clips = []
        for w in WORDS:
            src, cached, used = eleven.tts(f"w-{w}", f"{w}.", v["voice_id"], seed_for(f"w-{w}"))
            mp3, onset = process_english(src, w, out_name=f"audition-{v['name']}-{w}")
            heard = whisper(mp3, "en", ENGLISH_PROMPT)
            ok, exact = whisper_word_ok(heard, w)
            clips.append({"word": w, "url": media(mp3), "raw": media(src), "heard": heard, "match": ok, "exact": exact,
                          "onset_ok": onset, "credits": used, "cached": cached})
            print(f"  {v['name']:7} {w:5} heard {heard!r:18} match={ok} onset_ok={onset} credits={used}{' (cached)' if cached else ''}")
        voices.append(dict(v, clips=clips, score=sum(bool(c["match"] and c["onset_ok"]) for c in clips),
                           exact=sum(bool(c["exact"]) for c in clips)))
    best = max(voices, key=lambda x: (x["score"], x["exact"]))
    state["english"] = {"voices": voices, "recommended": best["voice_id"], "chosen": state.get("english", {}).get("chosen")}
    save_state(state)
    print(f"Credits left after: {eleven.credits_left()} – best Whisper score: {best['name']} ({best['score']}/5)")


def arabic_design(model: str = "eleven_multilingual_ttv_v2", run: int = 1) -> None:
    state = load_state()
    print(f"Credits left before: {eleven.credits_left()} – Voice Design charges the preview text once ({len(AR_PREVIEW_TEXT)} characters)")
    previews = eleven.design_voice(AR_DESCRIPTION, AR_PREVIEW_TEXT, seed=seed_for(f"arabic-voice-design-{run}" if run > 1 else "arabic-voice-design"),
                                   model=model)
    state["arabic"] = dict(state.get("arabic", {}), description=AR_DESCRIPTION, preview_text=AR_PREVIEW_TEXT, design_model=model,
                           previews=[dict(p, url="/media/" + p["file"]) for p in previews])
    save_state(state)
    print(f"Credits left after: {eleven.credits_left()} – {len(previews)} previews saved")


WEBSITE_NOTE = ("The Voice Design API was refused on the free plan (HTTP 403 feature_not_available: \"Creating a voice "
                "through the API is only available on a paid plan.\"), so the voice is designed on the website with the same "
                "description and preview text (brief §5), and its voice ID is pasted into the studio page.")


def arabic_website_mode() -> None:
    """Brief §5 fallback: the voice is made on the website; the studio page shows the texts and takes the voice ID."""
    state = load_state()
    state["arabic"] = dict(state.get("arabic", {}), mode="website", description=AR_DESCRIPTION, preview_text=AR_PREVIEW_TEXT,
                           design_model="website Voice Design", api_refused=WEBSITE_NOTE, voice_name=AR_VOICE_NAME)
    save_state(state)


def check_voice(voice_id: str) -> dict:
    """GET /v1/voices/{id}: the voice must exist in this account (made on the website)."""
    v = eleven._request("GET", f"/v1/voices/{voice_id}")
    return {k: v.get(k) for k in ("voice_id", "name", "category", "description")}


def arabic_lines_for(voice_id: str) -> dict:
    """Website mode: check the pasted voice ID, then make hear_L1 and tip_p with it (for the final OK)."""
    from make_audio_v11 import build_arabic_clip, load_content
    state = load_state()
    ar = state["arabic"]
    info = check_voice(voice_id)
    ar.update(voice_id=voice_id, voice_info=info, approved=False)
    save_state(state)
    content = load_content()
    lines = []
    for tid in ("hear_L1", "tip_p"):
        t = content["texts"][tid]
        out, report = build_arabic_clip(tid, t.get("say") or t["ar"], voice_id, english_dir=None)
        keep = ROOT / "tools" / ".audio-cache" / "v11" / "audition" / f"{tid}-{voice_id}.mp3"
        keep.parent.mkdir(parents=True, exist_ok=True)
        keep.write_bytes(out.read_bytes())
        lines.append({"id": tid, "text": t["ar"], "url": media(keep), "report": report})
    ar["lines"] = lines
    save_state(state)
    write_voices_json(state)
    return state


def arabic_lines(state: dict | None = None) -> dict:
    """Save the chosen preview as a voice (one of the 3 custom slots), then make two real app lines with it."""
    from make_audio_v11 import build_arabic_clip, load_content
    state = state or load_state()
    ar = state["arabic"]
    if not ar.get("voice_id") or ar.get("voice_preview") != ar["chosen_preview"]:
        gid = next(p["generated_voice_id"] for p in ar["previews"] if p["n"] == ar["chosen_preview"])
        ar["voice_id"] = eleven.save_designed_voice(AR_VOICE_NAME, AR_DESCRIPTION, gid)
        ar["voice_preview"] = ar["chosen_preview"]
        save_state(state)
        print("Saved the designed voice:", ar["voice_id"])
    content = load_content()
    lines = []
    for tid in ("hear_L1", "tip_p"):
        t = content["texts"][tid]
        out, report = build_arabic_clip(tid, t.get("say") or t["ar"], ar["voice_id"], english_dir=None)
        keep = Path(ROOT / "tools" / ".audio-cache" / "v11" / "audition" / f"{tid}-preview{ar['chosen_preview']}.mp3")
        keep.parent.mkdir(parents=True, exist_ok=True)
        keep.write_bytes(out.read_bytes())
        lines.append({"id": tid, "text": t["ar"], "url": media(keep), "report": report})
        print(f"  {tid}: {report['seconds']} s, {report['chars_per_s']} chars/s, pass={report['pass']}")
    ar["lines"] = lines
    save_state(state)
    write_voices_json(state)
    print(f"Credits left: {eleven.credits_left()}")
    return state


if __name__ == "__main__":
    {"english": english, "arabic-design": arabic_design, "arabic-lines": arabic_lines}[sys.argv[1]]()
