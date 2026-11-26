"""Small ElevenLabs client for the v1.1 audio build (standard library only).

Key safety: the key is read from .env at run time only. It is never printed, logged or written
to any other file; every error message is masked. Usage of every call (item id, characters,
credits before/after) is appended to deliverables/elevenlabs-usage.md.
Every audio response is cached in tools/.audio-cache/eleven/ keyed by
sha256(text|voice|model|settings|seed|previous|next), so nothing is ever paid for twice.

CLI:  python tools/eleven.py check        -> credits left (no key shown)
"""
from __future__ import annotations

import base64
import datetime as dt
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "tools" / ".audio-cache" / "eleven"
USAGE_MD = ROOT / "deliverables" / "elevenlabs-usage.md"
USAGE_JSON = CACHE / "usage.json"
API = "https://api.elevenlabs.io"
MODEL = "eleven_multilingual_v2"
SETTINGS = {"stability": 0.55, "similarity_boost": 0.75, "style": 0.0, "use_speaker_boost": True, "speed": 0.9}
_key: str | None = None
LAST_HEADERS: dict = {}   # headers of the last successful response ("character-cost" = credits charged for that call)
_balance: int | None = None   # this run's balance: one account-counter read, then minus the exact cost of each call


class ElevenError(RuntimeError):
    def __init__(self, status: int, detail: str):
        super().__init__(f"ElevenLabs HTTP {status}: {detail}")
        self.status = status
        self.detail = detail


def _load_key() -> str:
    global _key
    if _key is None:
        env = ROOT / ".env"
        val = ""
        if env.exists():
            for line in env.read_text(encoding="utf-8-sig").splitlines():
                if line.strip().startswith("ELEVENLABS_API_KEY="):
                    val = line.split("=", 1)[1].strip().strip('"').strip("'")
        if not val:
            raise SystemExit("ELEVENLABS_API_KEY is empty in .env – paste the key there and save the file.")
        _key = val
    return _key


def mask(s: str) -> str:
    k = _key
    out = str(s)
    if k:
        out = out.replace(k, "sk_***masked***")
    import re
    return re.sub(r"sk_[A-Za-z0-9]{20,}", "sk_***masked***", out)


def _request(method: str, path: str, body: dict | None = None, params: dict | None = None, raw: bool = False):
    url = API + path
    if params:
        url += "?" + "&".join(f"{k}={v}" for k, v in params.items())
    data = json.dumps(body).encode("utf-8") if body is not None else None
    for attempt in range(4):
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("xi-api-key", _load_key())
        req.add_header("Accept", "audio/mpeg" if raw else "application/json")
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                payload = r.read()
                headers = {k.lower(): v for k, v in r.headers.items()}
                LAST_HEADERS.clear()
                LAST_HEADERS.update(headers)
                return (payload, headers) if raw else (json.loads(payload.decode("utf-8")) if payload else {})
        except urllib.error.HTTPError as e:
            detail = mask(e.read().decode("utf-8", "replace")[:600])
            if e.code in (429,) or e.code >= 500:
                if attempt < 3:
                    ra = (e.headers or {}).get("Retry-After")
                    time.sleep(float(ra) if ra and ra.replace(".", "", 1).isdigit() else (10, 20, 40)[attempt])
                    continue
            raise ElevenError(e.code, detail) from None
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:   # network drops and read timeouts
            if attempt < 3:
                time.sleep((5, 20, 45)[attempt])     # ride out a short network outage
                continue
            raise ElevenError(0, mask(f"{type(e).__name__}: {e}")) from None
    raise ElevenError(0, "no response")


# ------------------------------------------------------------------ account
def subscription() -> dict:
    s = _request("GET", "/v1/user/subscription")
    return {k: s.get(k) for k in ("tier", "character_count", "character_limit", "next_character_count_reset_unix", "voice_limit", "voice_slots_used", "can_use_instant_voice_cloning")}


def credits_left(fresh: bool = False) -> int:
    """Credits left. The account counter is read once per run (or when fresh=True); after that each paid call
    subtracts its exact cost, so a long batch does not hit the API's rate limit with extra counter reads."""
    global _balance
    if fresh or _balance is None:
        s = subscription()
        _balance = int(s["character_limit"]) - int(s["character_count"])
    return _balance


def reset_date() -> str:
    s = subscription()
    ts = s.get("next_character_count_reset_unix")
    return dt.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M") if ts else "unknown"


def list_voices() -> list[dict]:
    v = _request("GET", "/v1/voices")
    return v.get("voices", [])


# ------------------------------------------------------------------ usage log
def _log_usage(row: dict) -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    rows = json.loads(USAGE_JSON.read_text(encoding="utf-8")) if USAGE_JSON.exists() else []
    rows.append(row)
    USAGE_JSON.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    write_usage_md(rows)


def write_usage_md(rows: list[dict] | None = None) -> None:
    rows = rows if rows is not None else (json.loads(USAGE_JSON.read_text(encoding="utf-8")) if USAGE_JSON.exists() else [])
    USAGE_MD.parent.mkdir(parents=True, exist_ok=True)
    used = sum(r.get("credits_used") or 0 for r in rows)
    chars = sum(r.get("chars") or 0 for r in rows)
    lines = ["# ElevenLabs usage log (v1.1 audio build)", "",
             "Every paid call, in order. **Used** is the exact charge ElevenLabs returns with each call (the `character-cost` "
             "response header). In the first rows (up to the English words) *before/after* are readings of the account counter "
             "(`GET /v1/user/subscription`), which lags several calls behind; later rows use one counter reading per run minus "
             "each call's exact cost (reading the counter around every call hit the API's rate limit). Credits spent on the "
             "ElevenLabs website (Voice Design) are not API calls and appear only in the account total. "
             "Cached results are re-used and cost nothing. The API key is never written here.", "",
             f"**Calls: {len(rows)} · characters sent: {chars} · credits used: {used}**", "",
             "| # | Time | Kind | Item | Characters | Counter before | Counter after | Used | Notes |", "|---|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(rows, 1):
        lines.append(f"| {i} | {r.get('time', '')} | {r.get('kind', '')} | {r.get('item', '')} | {r.get('chars', '')} | "
                     f"{r.get('before', '')} | {r.get('after', '')} | {r.get('credits_used', '')} | {r.get('note', '')} |")
    USAGE_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _paid_call(kind: str, item: str, chars: int, fn, note: str = ""):
    """Credits charged = the "character-cost" response header (exact, per call). Before/after = this run's balance
    (one account-counter read, then minus each exact cost). Bookkeeping never raises after a paid call succeeded,
    so a paid result is never lost."""
    global _balance
    before = credits_left()
    if before < chars:
        raise ElevenError(402, f"quota_exceeded: {before} credits left, this call needs about {chars}")
    out = fn()
    cost = LAST_HEADERS.get("character-cost")
    used = int(cost) if cost and str(cost).isdigit() else chars    # measured rate: 1 credit per character
    _balance = before - used
    try:
        _log_usage({"time": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "kind": kind, "item": item, "chars": chars,
                    "before": before, "after": _balance, "credits_used": used,
                    "cost_source": "character-cost header" if cost else "1 credit per character", "note": note})
    except Exception as e:  # noqa: BLE001
        print("usage log not written:", mask(str(e)))
    return out, used


def recover_from_history(text: str, voice_id: str):
    """A paid result lost on this PC can be downloaded again from the ElevenLabs History at no cost (brief §4.3).
    Returns (mp3 bytes, history item) for the newest item with exactly this text and voice, or None."""
    h = _request("GET", "/v1/history", params={"page_size": 20, "voice_id": voice_id})
    for it in h.get("history", []):
        if it.get("text") == text:
            payload, _ = _request("GET", f"/v1/history/{it['history_item_id']}/audio", raw=True)
            return payload, {k: it.get(k) for k in ("history_item_id", "date_unix", "character_count_change_from", "character_count_change_to")}
    return None


# ------------------------------------------------------------------ text to speech
def tts_key(text: str, voice_id: str, seed: int, settings: dict | None = None, previous_text: str | None = None,
            next_text: str | None = None, model: str = MODEL) -> str:
    s = json.dumps(settings or SETTINGS, sort_keys=True)
    blob = "|".join([text, voice_id, model, s, str(seed), previous_text or "", next_text or ""])
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def tts(item: str, text: str, voice_id: str, seed: int, settings: dict | None = None, previous_text: str | None = None,
        next_text: str | None = None, model: str = MODEL) -> tuple[Path, bool, int]:
    """Return (mp3 path, from_cache, credits used). Never regenerates a cached item."""
    key = tts_key(text, voice_id, seed, settings, previous_text, next_text, model)
    path = CACHE / "tts" / f"{key}.mp3"
    if path.exists() and path.stat().st_size > 0:
        return path, True, 0
    body = {"text": text, "model_id": model, "voice_settings": settings or SETTINGS, "seed": seed}
    if previous_text:
        body["previous_text"] = previous_text
    if next_text:
        body["next_text"] = next_text
    (payload, headers), used = _paid_call(
        "tts", item, len(text),
        lambda: _request("POST", f"/v1/text-to-speech/{voice_id}", body, {"output_format": "mp3_44100_128"}, raw=True),
        note=("ctx " if (previous_text or next_text) else "") + (f"seed {seed}"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    meta = {"item": item, "text": text, "voice_id": voice_id, "model": model, "settings": settings or SETTINGS, "seed": seed,
            "previous_text": previous_text, "next_text": next_text, "credits_used": used,
            "character_cost_header": headers.get("character-cost") or headers.get("x-character-count"),
            "request_id": headers.get("request-id"), "history_item_id": headers.get("history-item-id")}
    (CACHE / "tts" / f"{key}.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    return path, False, used


# ------------------------------------------------------------------ voice design
def design_voice(description: str, text: str, seed: int, model: str = "eleven_multilingual_ttv_v2") -> list[dict]:
    """Run Voice Design once (3 previews). Cached by description|text|seed|model."""
    key = hashlib.sha256("|".join([description, text, str(seed), model]).encode("utf-8")).hexdigest()
    folder = CACHE / "design" / key
    meta = folder / "previews.json"
    if meta.exists():
        return json.loads(meta.read_text(encoding="utf-8"))
    res, used = _paid_call("voice-design", "arabic-voice", len(text),
                           lambda: _request("POST", "/v1/text-to-voice/design",
                                            {"voice_description": description, "text": text, "model_id": model, "seed": seed},
                                            {"output_format": "mp3_44100_128"}),
                           note=f"3 previews, seed {seed}")
    folder.mkdir(parents=True, exist_ok=True)
    out = []
    for i, p in enumerate(res.get("previews", []), 1):
        f = folder / f"preview{i}.mp3"
        f.write_bytes(base64.b64decode(p["audio_base_64"]))
        out.append({"n": i, "generated_voice_id": p["generated_voice_id"], "file": str(f.relative_to(ROOT)).replace("\\", "/"),
                    "duration": p.get("duration_secs"), "language": p.get("language")})
    meta.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def save_designed_voice(name: str, description: str, generated_voice_id: str) -> str:
    res = _request("POST", "/v1/text-to-voice", {"voice_name": name, "voice_description": description,
                                                 "generated_voice_id": generated_voice_id})
    return res["voice_id"]


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        try:
            s = subscription()
            print(json.dumps({"tier": s["tier"], "credits_used": s["character_count"], "credit_limit": s["character_limit"],
                              "credits_left": int(s["character_limit"]) - int(s["character_count"]),
                              "resets": reset_date(), "voice_slots_used": s.get("voice_slots_used"), "voice_limit": s.get("voice_limit")}))
        except ElevenError as e:
            print(f"ERROR {e.status}: {e.detail}")
            sys.exit(1)
