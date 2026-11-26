"""Shared helpers for the v1.1 audio build (audition, studio page and make_audio_v11.py).

Text rules follow make_audio.arabic_plan ("…" -> "،", brackets removed, no Latin letters or digits
reach the voice), with two v1.1 differences from the brief:
  * one request per segment between {ph:x}/{w:x} markers (not per comma phrase), and
  * harakat and tanween are stripped but SHADDA IS KEPT.
"""
from __future__ import annotations

import hashlib
import re

MARK = re.compile(r"\{(ph|w):([a-z]+)\}")
# fatha/damma/kasra + tanween (064B–0650), sukun (0652), dagger alef (0670), small high marks, tatweel; NOT shadda (0651)
HARAKAT = re.compile("[ً-ِْٰۡـ]")
ENGLISH_PROMPT = "A single English word for children learning to read:"
# identical to the homophone list in tools/verify_audio.py
SAME_SOUND = {"sun": {"son"}, "ant": {"and", "aunt"}, "ink": {"inc"}, "tin": {"ten", "10"}, "palm": {"pom", "pam"},
              "pen": {"pin"}, "in": {"inn"}, "nest": {"next"}, "sat": {"sat"}, "net": {"nett"}}


def seed_for(item: str, retake: int = 0) -> int:
    """Fixed seed per item; a retake gets a new seed."""
    return (int(hashlib.sha1(item.encode("utf-8")).hexdigest()[:8], 16) + 7919 * retake) % 2_147_483_647


def clean_ar(text: str) -> str:
    """Prepare one Arabic segment for the voice (rules above)."""
    t = text.replace("…", "،").replace("...", "،").replace("«", "").replace("»", "")
    t = t.replace("(", "").replace(")", "").replace("–", "،").replace("—", "،")
    t = t.replace("\r", "").replace("\n", ". ")
    t = HARAKAT.sub("", t)
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"^[،,.؛:\s]+", "", t)          # a segment never starts with punctuation
    t = re.sub(r"\s+([،,.؟?!:؛])", r"\1", t)    # no space before punctuation
    return t.strip()


def plan(say: str) -> list[tuple[str, str]]:
    """[('ar', segment) | ('ph', letter) | ('w', word)] for one say-script."""
    out: list[tuple[str, str]] = []
    pos = 0
    for m in list(MARK.finditer(say)) + [None]:
        chunk = say[pos: m.start()] if m else say[pos:]
        seg = clean_ar(chunk)
        if re.search(r"[ء-ي]", seg):    # only segments with Arabic letters are spoken
            if re.search(r"[A-Za-z0-9٠-٩]", seg):
                raise ValueError(f"Latin letters or digits would reach the Arabic voice: {seg!r}")
            out.append(("ar", seg))
        if m:
            out.append((m.group(1), m.group(2)))
            pos = m.end()
    return out


def whisper_word_ok(heard: str, word: str) -> tuple[bool, bool]:
    """(match, exact) with exactly the rule used by tools/verify_audio.py."""
    clean = re.sub(r"[^a-z0-9 ]", "", heard.lower()).strip()
    exact = clean == word or clean.replace(" ", "") == word
    return exact or clean in SAME_SOUND.get(word, set()), exact


def norm_ar(s: str) -> str:
    """Identical to verify_audio.norm_ar (letters only, alef/ya/ta-marbuta folded)."""
    import unicodedata
    s = unicodedata.normalize("NFKC", s)
    s = re.sub("[ً-ْٰـ]", "", s)
    s = re.sub("[إأآٱ]", "ا", s).replace("ى", "ي").replace("ة", "ه").replace("ؤ", "و").replace("ئ", "ي")
    s = re.sub(r"[A-Za-z0-9٠-٩]", "", s)
    return re.sub(r"[^ء-ي]", "", s)
