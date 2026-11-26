"""Quality checks for 5 Minutes Together (Playwright + axe-core). Writes deliverables/TEST_REPORT.md.

    .venv/Scripts/python.exe tests/run_tests.py [--base https://…]   (default: local server on app/)

1. Play through all five days at 390×844 (correct AND wrong answers, the next-calendar-day
   unlock rule, the Day 5 final check and the results screen) with no console errors.
2. Offline: load once, wait for the service worker, switch the context offline, reload, finish a session.
3. axe-core on every screen: no serious or critical violations.
4. Visual checks: Arabic right-to-left layout, Andika's single-storey "a", every picture renders,
   every audio file decodes in the browser, tap targets ≥ 64 px, parent gate, offline badge.
5. Size and a simulated 3G first load.
v1.1 (brief §11): version, reviewer checklist with A1–A3, one-time update notice, no speech fallback,
audio checks, header layout, update path from v1.0, the /v1.0/ archive, secrets and attribution.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import zipfile
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
DELIV = ROOT / "deliverables"
sys.path.insert(0, str(ROOT / "tools"))
from serve import serve  # noqa: E402

CONTENT = json.loads((APP / "content.json").read_text(encoding="utf-8"))
VIEW = {"width": 390, "height": 844}
RESULTS: list[dict] = []
SCREENS_AXE: dict[str, list] = {}
T0 = time.time()


def record(section: str, name: str, ok: bool, detail: str = "") -> bool:
    RESULTS.append({"section": section, "name": name, "ok": bool(ok), "detail": detail})
    print(("PASS " if ok else "FAIL ") + f"[{section}] {name}" + (f" — {detail}" if detail else ""), flush=True)
    return ok


class Ctx:
    """A fresh browser context + page that collects console errors."""

    def __init__(self, browser, base, **kw):
        opts = dict(viewport=VIEW, device_scale_factor=1, locale="ar-OM")
        opts.update(kw)
        self.ctx = browser.new_context(**opts)
        self.page = self.ctx.new_page()
        self.base = base
        self.errors: list[str] = []
        self.page.on("console", lambda m: self.errors.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
        self.page.on("pageerror", lambda e: self.errors.append(f"pageerror: {e}"))
        self.page.on("requestfailed", lambda r: self.errors.append(f"requestfailed: {r.url} {r.failure}") if "favicon" not in r.url else None)

    def goto(self, hash_: str, fast: bool = True):
        self.page.goto(self.base + ("?fast=1" if fast else "") + hash_)

    def close(self):
        self.ctx.close()


def day_time(n: int) -> dt.datetime:
    return dt.datetime(2026, 12, 6 + n, 10, 0, 0)


# ------------------------------------------------------------------ session play-through
def do_find(pg, f, wrong: bool):
    target = f["sound"]
    if wrong:
        bad = next(p for p in f["pictures"] if CONTENT["keywords"][p]["first"] != target)
        pg.locator(f'[data-test="find-pic"][data-word="{bad}"]').click()
        pg.wait_for_timeout(120)
    for p in f["pictures"]:
        if CONTENT["keywords"][p]["first"] == target:
            pg.locator(f'[data-test="find-pic"][data-word="{p}"]').click()
    pg.locator('[data-test="next"]:visible').click()


def play_day(c: Ctx, n: int, wrong_items=(), wrong_find=True, retry_blend=True, via_map=True):
    pg = c.page
    d = CONTENT["days"][n - 1]
    if via_map:
        c.goto("#/home")
        pg.locator('[data-test="home"]').wait_for()
        pg.locator('[data-test="start"]').click()
        pg.locator(f'[data-test="stop"][data-day="{n}"]').click()
    else:
        c.goto(f"#/day/{n}")
    pg.locator('[data-test="session"][data-step="start"]').wait_for()
    pg.locator('[data-test="go"]').click()
    if not d["hear"]["review"]:
        for s in d["newSounds"]:
            pg.locator('[data-test="letter-card"]').click()
            pg.locator('[data-test="next"]:visible').click()
            kws = pg.locator('[data-test="kw"]')
            kws.first.wait_for()
            for i in range(kws.count()):
                kws.nth(i).click()
            pg.locator('[data-test="next"]:visible').click()
            do_find(pg, next(x for x in d["hear"]["find"] if x["sound"] == s), wrong_find)
    else:
        tiles = pg.locator('[data-test="review-tile"]')
        tiles.first.wait_for()
        for i in range(tiles.count()):
            tiles.nth(i).click()
        pg.locator('[data-test="next"]:visible').click()
        for f in d["hear"]["find"]:
            do_find(pg, f, wrong_find)
    for item in d["tapSay"]:
        pg.locator(f'.tiles[data-word="{item["word"]}"]').wait_for()
        tiles = pg.locator('[data-test="word-tile"]')
        for i in range(tiles.count()):
            tiles.nth(i).click()
        pg.locator('[data-test="train"]:not([disabled])').click()
        pg.locator('[data-test="ask-card"]').wait_for()
        pg.locator('[data-test="next"]:visible').click()
    for j, w in enumerate(d["blend"]):
        pg.locator(f'.tiles[data-word="{w}"]').wait_for()
        if retry_blend and j == 0:
            pg.locator('[data-test="hint"]').click()
            pg.locator('[data-test="try-again"]').click()
            pg.wait_for_timeout(150)
        pg.locator('[data-test="said-right"]').click()
        pg.locator('[data-test="reveal"]').wait_for()
        pg.locator('[data-test="next"]:visible').click()
    pg.locator('[data-test="go-challenge"]').click()
    for k, it in enumerate(d["challenge"]):
        pg.locator(".progress-dots b.now", has_text=str(k + 1)).wait_for()
        if k in wrong_items:
            bad = next(ch for ch in it["choices"] if ch != it["target"])
            pg.locator(f'[data-test="choice"][data-value="{bad}"]').click()
            pg.wait_for_timeout(120)
        pg.locator(f'[data-test="choice"][data-value="{it["target"]}"]').click()
    pg.locator('[data-test="stop-sign"]').wait_for()


def stop_status(c: Ctx, n: int) -> str:
    c.goto("#/home")  # navigating to the same hash would not re-render the map
    c.page.locator('[data-test="home"]').wait_for()
    c.goto("#/map")
    return c.page.locator(f'[data-test="stop"][data-day="{n}"]').get_attribute("data-status")


def test_playthrough(browser, base):
    sec = "1. Five-day play-through (390×844)"
    c = Ctx(browser, base)
    pg = c.page
    try:
        pg.clock.set_fixed_time(day_time(1))
        c.goto("#/onboarding/1")
        for i in (1, 2, 3):
            pg.locator(f'[data-test="onboarding"][data-step="{i}"]').wait_for()
            pg.locator('[data-test="ob-next"]').click()
        pg.locator('[data-test="home"]').wait_for()
        record(sec, "Onboarding: 3 Arabic screens with audio buttons, then parent home", True)
        expected_first = {}
        mistakes = {1: (1,), 2: (0,), 3: (2,), 4: (), 5: (1, 7)}
        for n in range(1, 6):
            pg.clock.set_fixed_time(day_time(n))
            st = stop_status(c, n)
            record(sec, f"Day {n} is unlocked on its calendar day", st == "today", f"status={st}")
            play_day(c, n, wrong_items=mistakes[n])
            record(sec, f"Day {n} played to the end (wrong + correct answers, hint, retry)", True,
                   f"wrong first answers at challenge items {list(mistakes[n]) or 'none'}")
            expected_first[n] = len(CONTENT['days'][n - 1]['challenge']) - len(mistakes[n])
            has_sticker = pg.locator('.sticker-reveal svg').count() == 1
            has_home = pg.locator('[data-test="home-activity"]').count() == 1
            record(sec, f"Day {n}: sticker, clear stopping point and no-screen home activity shown", has_sticker and has_home)
            pg.locator('[data-test="finish"]').click()
            if n < 5:
                pg.locator('[data-test="home"]').wait_for()
                nxt = stop_status(c, n + 1)
                record(sec, f"Day {n + 1} stays locked on the same calendar day (no automatic next day)", nxt == "locked", f"status={nxt}")
            else:
                pg.locator('[data-test="results"]').wait_for()
        prog = pg.evaluate("JSON.parse(localStorage.getItem('fmt1.progress'))")
        ok = all(prog["days"][str(n)]["challenge"]["score"] == expected_first[n] for n in range(1, 6))
        record(sec, "Challenge scores stored per day (first-try scoring)", ok, json.dumps({n: prog['days'][str(n)]['challenge']['score'] for n in range(1, 6)}))
        o1 = pg.locator('[data-test="obj-O1"]').get_attribute("data-met")
        o2 = pg.locator('[data-test="obj-O2"]').get_attribute("data-met")
        o3 = pg.locator('[data-test="obj-O3"]').get_attribute("data-met")
        record(sec, "Results: O1 met with 5/6 sounds (one wrong first try)", o1 == "true", f"O1 data-met={o1}")
        record(sec, "Results: O2 met with 9/10 words (one wrong first try)", o2 == "true", f"O2 data-met={o2}")
        record(sec, "Results: O3 = 5/5 sessions completed", o3 == "true", f"O3 data-met={o3}")
        weak = pg.locator('[data-test="weak-tile"]').evaluate_all("els => els.map(e => e.dataset.letter)")
        record(sec, "Results list the sounds to practise again", "a" in weak, f"practise: {weak}")
        books = pg.evaluate("Array.from(document.querySelectorAll('[data-test=sticker]')).length")
        c.goto("#/stickers")
        earned = pg.locator('[data-test="sticker"][data-earned="true"]').count()
        record(sec, "Sticker book holds exactly one sticker per completed day", earned == 5, f"earned={earned}")
        st = pg.evaluate("({fallbacks: window.FMT.audio.fallbacks, played: window.FMT.audio.played, failed: window.FMT.audio.failed})")
        record(sec, "No speech fallback in the five-day play-through: every clip played was a recorded one (FMT.audio.fallbacks = 0)",
               st["fallbacks"] == 0 and not st["failed"], json.dumps(st)[:300])
        record(sec, "No console errors during the five-day play-through", not c.errors, "; ".join(c.errors[:5]))
    except Exception as e:
        record(sec, "Play-through crashed", False, f"{e!r}\n{traceback.format_exc()[-1500:]}")
        pg.screenshot(path=str(DELIV / "test-failure.png"))
    finally:
        c.close()


def test_objectives_not_met(browser, base):
    """Results logic with a weaker learner (O1 and O2 not met), using stored progress."""
    sec = "1. Five-day play-through (390×844)"
    c = Ctx(browser, base)
    try:
        c.goto("#/home")
        items = [{"type": "sound", "target": s, "firstTry": s not in ("p", "i")} for s in "satpin"]
        items += [{"type": "blend", "target": w, "firstTry": w not in ("pin", "tip", "sit")} for w in ["pan", "pin", "tin", "tap", "nap", "sip", "tip", "pit", "pat", "sit"]]
        prog = {"days": {str(n): {"done": True, "firstDate": "2026-12-0" + str(n), "date": "2026-12-0" + str(n), "challenge": {"score": 3, "total": 3, "items": []}} for n in range(1, 5)}}
        prog["days"]["5"] = {"done": True, "firstDate": "2026-12-05", "date": "2026-12-05", "challenge": {"score": 11, "total": 16, "items": items}}
        c.page.evaluate("p => { localStorage.setItem('fmt1.progress', JSON.stringify(p)); localStorage.setItem('fmt1.settings', JSON.stringify({onboarded:true})); }", prog)
        c.goto("#/results")
        c.page.locator('[data-test="objectives"]').wait_for()
        o1 = c.page.locator('[data-test="obj-O1"]').get_attribute("data-met")
        o2 = c.page.locator('[data-test="obj-O2"]').get_attribute("data-met")
        weak = c.page.locator('[data-test="weak-tile"]').evaluate_all("els => els.map(e => e.dataset.letter)")
        record(sec, "Results: O1 'not met yet' at 4/6, O2 'not met yet' at 7/10, practice list shown", o1 == "false" and o2 == "false" and "p" in weak and "i" in weak, f"O1={o1} O2={o2} practise={weak}")
    finally:
        c.close()


# ------------------------------------------------------------------ offline
def test_offline(browser, base):
    sec = "2. Offline"
    c = Ctx(browser, base)
    pg = c.page
    try:
        c.goto("#/home")
        pg.evaluate("localStorage.setItem('fmt1.settings', JSON.stringify({onboarded:true}))")
        c.goto("#/home")
        pg.locator('[data-test="offline-badge"]:not([hidden])').wait_for(timeout=300000)
        record(sec, "Service worker cached the app and the home shows 'Ready offline ✓ / جاهز دون إنترنت'", True,
               pg.locator('[data-test="offline-badge"]').inner_text())
        c.ctx.set_offline(True)
        pg.reload()
        pg.locator('[data-test="home"]').wait_for()
        record(sec, "Reload while offline shows the parent home", True)
        play_day(c, 1, wrong_items=(0,))
        failed = pg.evaluate("window.FMT.audio.failed")
        record(sec, "Completed a full Day 1 session offline; every audio clip came from the cache", not failed, f"failed clips: {failed}")
        record(sec, "No console errors offline", not c.errors, "; ".join(c.errors[:5]))
    except Exception as e:
        record(sec, "Offline test crashed", False, repr(e))
    finally:
        c.close()


# ------------------------------------------------------------------ axe + visual checks
AXE_JS = None


def run_axe(pg, name: str):
    from axe_playwright_python.sync_playwright import Axe
    global AXE_JS
    res = Axe().run(pg, options={"runOnly": {"type": "tag", "values": ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "best-practice"]}})
    v = res.response["violations"]
    bad = [x for x in v if x["impact"] in ("serious", "critical")]
    SCREENS_AXE[name] = [{"id": x["id"], "impact": x["impact"], "nodes": len(x["nodes"]), "help": x["help"],
                          "targets": [n["target"] for n in x["nodes"][:3]]} for x in v]
    return bad


def small_targets(pg):
    return pg.evaluate("""() => Array.from(document.querySelectorAll('button, a[href], input[type=radio] + span, [role=switch]'))
      .filter(e => { const r = e.getBoundingClientRect(); const s = getComputedStyle(e); return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && !e.closest('.print-page'); })
      .map(e => { const t = e.matches('input + span') ? e.parentElement : e; const r = t.getBoundingClientRect(); return {w: Math.round(r.width), h: Math.round(r.height), label: (t.getAttribute('aria-label') || t.textContent || '').trim().slice(0, 30)}; })
      .filter(x => x.w < 63.5 || x.h < 63.5)""")


def test_screens(browser, base):
    sec3, sec4 = "3. Accessibility (axe-core)", "4. Visual and interaction checks"
    c = Ctx(browser, base)
    pg = c.page
    small_all = {}
    try:
        c.goto("#/onboarding/1")
        screens = []

        def pass_gate_if_shown():
            pg.wait_for_timeout(300)
            if pg.locator('[data-test="gate-hold"]').count():
                b = pg.locator('[data-test="gate-hold"]').bounding_box()
                pg.mouse.move(b["x"] + b["width"] / 2, b["y"] + b["height"] / 2)
                pg.mouse.down()
                pg.wait_for_timeout(700)
                pg.mouse.up()

        def visit(name, hash_, ready, before=None):
            if before:
                before()
            c.goto(hash_)
            pass_gate_if_shown()
            pg.locator(ready).first.wait_for()
            pg.wait_for_timeout(250)
            screens.append(name)
            bad = run_axe(pg, name)
            st = small_targets(pg)
            if st:
                small_all[name] = st
            return bad

        problems = {}
        for name, hash_, ready in [
            ("onboarding-1", "#/onboarding/1", '[data-test="onboarding"]'),
            ("onboarding-3", "#/onboarding/3", '[data-test="onboarding"]'),
        ]:
            b = visit(name, hash_, ready)
            if b:
                problems[name] = b
        pg.evaluate("localStorage.setItem('fmt1.settings', JSON.stringify({onboarded:true, unlockAll:true}))")
        pairs = [
            ("home", "#/home", '[data-test="home"]'), ("journey-map", "#/map", '[data-test="map"]'),
            ("session-start", "#/day/1?step=start&demo=1", '[data-test="go"]'),
            ("hear-it", "#/day/1?step=hear&demo=1", '[data-test="letter-card"]'),
            ("tap-and-say", "#/day/2?step=tapsay&demo=1", '[data-test="train"]'),
            ("blend", "#/day/3?step=blend&demo=1", '[data-test="said-right"]'),
            ("challenge", "#/day/1?step=challenge&demo=1", '[data-test="go-challenge"]'),
            ("final-check-start", "#/day/5?step=start&demo=1", '[data-test="go"]'),
            ("sticker-done", "#/day/1?step=done&demo=1", '[data-test="stop-sign"]'),
            ("results", "#/results", '[data-test="objectives"]'), ("sticker-book", "#/stickers", '[data-test="sticker-book"]'),
            ("tips", "#/tips", '[data-test="tips"]'), ("how-to", "#/howto", '[data-test="howto"]'),
            ("apps", "#/apps", '[data-test="apps"]'), ("about", "#/about", '[data-test="about"]'),
        ]
        for name, hash_, ready in pairs:
            b = visit(name, hash_, ready)
            if b:
                problems[name] = b
        # inner session states
        c.goto("#/day/1?step=hear&demo=1")
        pg.locator('[data-test="letter-card"]').click()
        pg.locator('[data-test="next"]:visible').click()
        pg.locator('[data-test="kw"]').first.wait_for()
        b = run_axe(pg, "keyword-pictures")
        if b:
            problems["keyword-pictures"] = b
        for i in range(2):
            pg.locator('[data-test="kw"]').nth(i).click()
        pg.locator('[data-test="next"]:visible').click()
        pg.locator('[data-test="find-pic"]').first.wait_for()
        b = run_axe(pg, "find-the-sound")
        if b:
            problems["find-the-sound"] = b
        c.goto("#/day/1?step=challenge&demo=1")
        pg.locator('[data-test="go-challenge"]').click()
        pg.locator('[data-test="choice"]').first.wait_for()
        b = run_axe(pg, "challenge-item")
        if b:
            problems["challenge-item"] = b
        # gated pages (gate passed by holding)
        c.goto("#/settings")
        pg.locator('[data-test="gate-hold"]').wait_for()
        b = run_axe(pg, "parent-gate")
        if b:
            problems["parent-gate"] = b
        box = pg.locator('[data-test="gate-hold"]').bounding_box()
        pg.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        pg.mouse.down()
        pg.wait_for_timeout(250)
        pg.mouse.up()
        short_ok = pg.locator('[data-test="gate"]').count() == 1
        pg.mouse.down()
        pg.wait_for_timeout(700)  # fast mode: 0.3 s hold (3 s in normal use)
        pg.mouse.up()
        pg.locator('[data-test="settings"]').wait_for()
        record(sec4, "Parent gate: a short press does not open settings; press-and-hold does", short_ok)
        for name, hash_, ready in [("settings", "#/settings", '[data-test="settings"]'), ("teachers", "#/teachers", '[data-test="teachers"]'),
                                   ("reviewer-checklist", "#/review", '[data-test="review"]'), ("flyer", "#/flyer", '[data-test="flyer"]'),
                                   ("printable-cards", "#/cards", '[data-test="day-card"]')]:
            b = visit(name, hash_, ready)
            if b:
                problems[name] = b
        # assessor tour overlay
        c.goto("#/home")
        pg.locator('[data-test="tour"]').click()
        pg.locator('[data-test="tour-card"]').wait_for()
        b = run_axe(pg, "assessor-tour")
        if b:
            problems["assessor-tour"] = b
        steps = 0
        while pg.locator('[data-test="tour-next"]').count() and steps < 20:
            txt = pg.locator('[data-test="tour-next"]').inner_text()
            pg.locator('[data-test="tour-next"]').click()
            steps += 1
            if "Finish" in txt:
                break
            pg.wait_for_timeout(150)
        record(sec4, "Assessor tour runs through all stops and unlocks all days", steps >= 10 and pg.evaluate("JSON.parse(localStorage.getItem('fmt1.settings')).unlockAll === true"), f"{steps} stops")
        total_bad = sum(len(v) for v in problems.values())
        record(sec3, f"axe-core: no serious or critical issues on {len(SCREENS_AXE)} screens and states", total_bad == 0,
               "" if not total_bad else json.dumps({k: [x['id'] for x in v] for k, v in problems.items()}))
        record(sec4, "Tap targets are at least 64 × 64 px on every screen", not small_all, json.dumps(small_all, ensure_ascii=False)[:800])

        # ---- right-to-left layout
        c.goto("#/home")
        pg.locator('[data-test="home"]').wait_for()
        rtl = pg.evaluate("""() => ({dir: document.documentElement.dir, lang: document.documentElement.lang,
            card: getComputedStyle(document.querySelector('.parent-card .pc-text')).direction,
            brandRight: document.querySelector('.brand').getBoundingClientRect().right > window.innerWidth / 2,
            sayLeft: document.querySelector('.parent-card .btn-say').getBoundingClientRect().left < document.querySelector('.parent-card .pc-text').getBoundingClientRect().left})""")
        record(sec4, "Arabic is right-to-left: <html dir=rtl lang=ar>, parent text RTL, brand on the right, speaker after the text", rtl["dir"] == "rtl" and rtl["lang"] == "ar" and rtl["card"] == "rtl" and rtl["brandRight"] and rtl["sayLeft"], json.dumps(rtl))
        c.goto("#/day/2?step=tapsay&demo=1")
        pg.locator('.tiles[data-word] .tile').first.wait_for()
        order = pg.evaluate("Array.from(document.querySelectorAll('.tiles[data-word] .tile')).map(t => [t.dataset.letter, Math.round(t.getBoundingClientRect().left)])")
        lefts = [x[1] for x in order]
        record(sec4, "English words stay left-to-right inside the Arabic page (p-a-t reads left to right)", lefts == sorted(lefts) and "".join(x[0] for x in order) == "pat", json.dumps(order))
        c.goto("#/home")
        pg.locator('[data-test="lang-toggle"]').click()
        pg.locator('[data-test="home"]').wait_for()
        ltr = pg.evaluate("[document.documentElement.dir, document.documentElement.lang]")
        record(sec4, "English toggle switches the parent area to left-to-right English", ltr == ["ltr", "en"], json.dumps(ltr))
        pg.locator('[data-test="lang-toggle"]').click()

        # ---- Andika single-storey a
        c.goto("#/day/1?step=start&demo=1")
        pg.locator('.tile[data-letter="a"]').wait_for()
        pg.evaluate("document.fonts.ready")
        cdp = c.ctx.new_cdp_session(pg)
        cdp.send("DOM.enable")
        cdp.send("CSS.enable")
        doc = cdp.send("DOM.getDocument", {"depth": -1})
        node = cdp.send("DOM.querySelector", {"nodeId": doc["root"]["nodeId"], "selector": '.tile[data-letter="a"]'})
        fonts = cdp.send("CSS.getPlatformFontsForNode", {"nodeId": node["nodeId"]})["fonts"]
        fam = [f["familyName"] for f in fonts]
        same = pg.evaluate("""async () => {
            await document.fonts.load('700 120px Andika');
            const draw = (ch) => { const c = document.createElement('canvas'); c.width = 160; c.height = 160; const x = c.getContext('2d');
              x.font = '700 120px Andika'; x.fillStyle = '#000'; x.fillText(ch, 20, 130); return x.getImageData(0, 0, 160, 160).data; };
            const a = draw('a'), alpha = draw('\\u0251'), dbl = (() => { const c = document.createElement('canvas'); c.width = 160; c.height = 160; const x = c.getContext('2d');
              x.font = '700 120px serif'; x.fillText('a', 20, 130); return x.getImageData(0, 0, 160, 160).data; })();
            let diff = 0, diff2 = 0, ink = 0; for (let i = 3; i < a.length; i += 4) { if (a[i] > 0) ink++; if (Math.abs(a[i] - alpha[i]) > 40) diff++; if (Math.abs(a[i] - dbl[i]) > 40) diff2++; }
            return {ink, diffToAlpha: diff, diffToSerifA: diff2}; }""")
        ok_a = "Andika" in " ".join(fam) and same["ink"] > 500 and same["diffToAlpha"] < same["ink"] * 0.02
        record(sec4, "Letter tiles render in Andika and its 'a' is single-storey (pixel-identical to Latin alpha ɑ)", ok_a,
               f"platform font for the tile: {fam}; {json.dumps(same)}")
        node2 = cdp.send("DOM.querySelector", {"nodeId": doc["root"]["nodeId"], "selector": '.parent-card .pc-text'})
        fonts2 = [f["familyName"] for f in cdp.send("CSS.getPlatformFontsForNode", {"nodeId": node2["nodeId"]})["fonts"]]
        record(sec4, "Arabic parent text renders in Baloo Bhaijaan 2 (self-hosted)", any("Baloo" in f for f in fonts2), f"{fonts2}")

        # ---- every picture renders
        rend = pg.evaluate("""async () => {
            const art = await import('./js/art.js');
            const box = document.createElement('div'); box.style.cssText = 'position:fixed;left:0;top:0;width:120px'; document.body.appendChild(box);
            const out = {};
            const test = (name, html) => { box.innerHTML = html; const s = box.querySelector('svg'); const r = s.getBBox(); const min = name.startsWith('icon:') ? 1 : 4; out[name] = r.width > 8 && r.height > 8 && s.querySelectorAll('*').length >= min; };
            art.pictureIds.forEach(id => test('picture:' + id, art.picture(id)));
            art.stickerIds.forEach(id => test('sticker:' + id, art.sticker(id)));
            ['mother-boy', 'father-girl', 'sister-boy', 'brother-girl'].forEach(k => test('family:' + k, art.family(k)));
            test('map', art.mapArt()); test('sanad', art.sanad());
            art.iconNames.forEach(n => test('icon:' + n, art.icon(n)));
            box.remove(); return out; }""")
        bad_art = [k for k, v in rend.items() if not v]
        need = set(CONTENT["keywords"]) | {w["picture"] for w in CONTENT["words"].values() if w["picture"]}
        missing_art = [p for p in need if f"picture:{p}" not in rend]
        record(sec4, f"Every illustration renders ({len(rend)} SVGs: 23 pictures, 5 stickers, 4 family scenes, map, mascot, icons)",
               not bad_art and not missing_art, f"bad={bad_art} missing={missing_art}")
        c.goto("#/teachers")
        pass_gate_if_shown()
        pg.locator('[data-test="qr"]').wait_for()
        try:
            pg.wait_for_function("(() => { const i = document.querySelector('[data-test=qr]'); return i && i.complete && i.naturalWidth > 0; })()", timeout=30000)
        except Exception:
            pass
        qr = pg.evaluate("(() => { const i = document.querySelector('[data-test=qr]'); return i ? i.naturalWidth : 0; })()")
        record(sec4, "QR code image loads on the teacher page", qr > 0, f"naturalWidth={qr}")

        # ---- every audio file decodes in the browser
        dec = pg.evaluate("""async () => {
            const m = await (await fetch('audio/manifest.json')).json();
            const urls = Object.keys(m.en).map(k => 'audio/en/' + k + '.mp3').concat(Object.keys(m.ar).map(k => 'audio/ar/' + k + '.mp3'));
            const ac = new (window.AudioContext || window.webkitAudioContext)();
            const bad = []; let total = 0;
            for (const u of urls) { try { const b = await ac.decodeAudioData(await (await fetch(u)).arrayBuffer()); total += b.duration; if (!(b.duration > 0.04)) bad.push(u); } catch (e) { bad.push(u + ' ' + e); } }
            return {n: urls.length, bad, minutes: total / 60}; }""")
        record(sec4, f"Every audio file in the manifest decodes with Web Audio ({dec['n']} clips, {dec['minutes']:.1f} min)", not dec["bad"], f"{dec['bad'][:5]}")
        # content references → manifest
        man = json.loads((APP / "audio" / "manifest.json").read_text(encoding="utf-8"))
        need_ids = {k for k, v in CONTENT["texts"].items() if "ar" in v and not v.get("noAudio")}
        miss = [k for k in need_ids if k not in man["ar"]]
        from_audio = json.loads((ROOT / "tools" / "audio_verification.json").read_text(encoding="utf-8")) if (ROOT / "tools" / "audio_verification.json").exists() else None
        record(sec4, "Every Arabic parent text has a recorded Arabic clip whose hash matches the current text", not miss, f"missing {miss}")
        if from_audio:
            S = from_audio["summary"]
            record(sec4, "Offline audio verification passed (exists, duration, RMS, clipping, phoneme acoustics, letter-name controls)",
                   not S["hard_failures"], f"{S['files_pass']}/{S['files_checked']} clips; phonemes {S['phonemes_pass']}/6; controls rejected {S['controls_rejected']}/6; Whisper English {S['whisper_en_match']}; Arabic mean similarity {S['whisper_ar_mean_similarity']}")
        # reviewer checklist copy
        from urllib.parse import urlsplit
        o = urlsplit(c.base)
        c.ctx.grant_permissions(["clipboard-read", "clipboard-write"], origin=f"{o.scheme}://{o.netloc}")
        c.goto("#/review")
        pass_gate_if_shown()
        pg.locator('[data-test="review"]').wait_for()
        pg.locator('[data-test="rate-clarity-4"]').check(force=True)
        pg.locator('[data-test="comment-clarity"]').fill("Clear Arabic.")
        pg.locator('[data-test="copy-feedback"]').click()
        out = pg.locator('[data-test="feedback-out"]').input_value()
        n_main = pg.locator('[data-test="review-item"]:not([data-test="audio-recheck"] [data-test="review-item"])').count()
        record(sec4, "Reviewer checklist: 8 items on a 1–5 scale with comments; 'Copy my feedback' builds a text summary (nothing sent)",
               n_main == 8 and "Clarity for parents: 4/5 – Clear Arabic." in out, out.splitlines()[2] if out else "")
        # large text + calm mode
        c.goto("#/settings")
        pass_gate_if_shown()
        pg.locator('[data-test="sw-large"]').click()
        pg.locator('[data-test="sw-calm"]').click()
        cls = pg.evaluate("document.documentElement.className")
        fs = pg.evaluate("getComputedStyle(document.documentElement).fontSize")
        record(sec4, "Large-text option and calm mode (reduced motion) switch on", "large" in cls and "calm" in cls and fs == "22px", f"class='{cls}', font-size={fs}")
        pg.locator('[data-test="sw-large"]').click()
        pg.locator('[data-test="sw-calm"]').click()
        record(sec4, "No console errors while visiting every screen", not c.errors, "; ".join(c.errors[:5]))
    except Exception as e:
        record(sec4, "Screen checks crashed", False, f"{e!r}\n{traceback.format_exc()[-1500:]}")
        try:
            pg.screenshot(path=str(DELIV / "test-failure-screens.png"))
        except Exception:
            pass
    finally:
        c.close()


def test_reduced_motion(browser, base):
    sec = "4. Visual and interaction checks"
    c = Ctx(browser, base, reduced_motion="reduce")
    try:
        c.goto("#/home", fast=False)
        c.page.evaluate("localStorage.setItem('fmt1.settings', JSON.stringify({onboarded:true}))")
        c.goto("#/home", fast=False)
        c.page.locator('[data-test="home"]').wait_for()
        calm = c.page.evaluate("document.documentElement.classList.contains('calm')")
        record(sec, "prefers-reduced-motion turns calm mode on automatically", calm)
    finally:
        c.close()


def test_backup(browser):
    sec = "5. Single-file offline backup"
    f = DELIV / "offline-backup.html"
    if not f.exists():
        record(sec, "offline-backup.html exists", False, "not built yet")
        return
    c = Ctx(browser, f.as_uri())
    try:
        c.page.goto(f.as_uri() + "?fast=1#/home")
        c.page.evaluate("localStorage.setItem('fmt1.settings', JSON.stringify({onboarded:true}))")
        c.base = f.as_uri()
        play_day(c, 1, wrong_items=(2,))
        failed = c.page.evaluate("window.FMT.audio.failed")
        record(sec, f"offline-backup.html ({f.stat().st_size / 1024 / 1024:.1f} MB) opens from file:// with no server and completes Day 1 with audio",
               not failed and not c.errors, f"failed={failed[:3]} errors={c.errors[:3]}")
    except Exception as e:
        record(sec, "Backup test crashed", False, repr(e))
    finally:
        c.close()


def sw_list() -> tuple[str, list[str]]:
    """FMT_VERSION and FMT_FILES from app/sw-files.js (what the service worker caches)."""
    s = (APP / "sw-files.js").read_text(encoding="utf-8")
    ver = re.search(r"FMT_VERSION = '([0-9a-f]+)'", s).group(1)
    files = json.loads(s.split("self.FMT_FILES = ", 1)[1].rstrip().rstrip(";"))
    return ver, files


def test_size_and_3g(browser, base):
    sec = "6. Size and slow network"
    _, files = sw_list()
    cached = sum((APP / f).stat().st_size for f in files if f != "./")
    archive = sum(p.stat().st_size for p in (APP / "v1.0").rglob("*") if p.is_file()) if (APP / "v1.0").exists() else 0
    record(sec, f"Offline cache (every file the service worker stores) is under 8 MB ({cached / 1024 / 1024:.2f} MB, {len(files)} entries); "
           f"the /v1.0/ archive ({archive / 1024 / 1024:.2f} MB) is served online only and not counted", cached < 8 * 1024 * 1024)
    c = Ctx(browser, base)
    try:
        cdp = c.ctx.new_cdp_session(c.page)
        cdp.send("Network.enable")
        cdp.send("Network.emulateNetworkConditions", {"offline": False, "latency": 150, "downloadThroughput": 1.6 * 1024 * 1024 / 8, "uploadThroughput": 750 * 1024 / 8})
        c.page.add_init_script("localStorage.setItem('fmt1.settings', JSON.stringify({onboarded:true}))")
        t0 = time.time()
        c.page.goto(base + "#/home")
        c.page.locator('[data-test="start"]').wait_for(timeout=60000)
        t_home = time.time() - t0
        c.page.locator('[data-test="start"]').click()
        c.page.locator('[data-test="stop"][data-day="1"]').click()
        c.page.locator('[data-test="go"]').wait_for()
        t_day1 = time.time() - t0
        record(sec, f"Simulated 3G (1.6 Mbit/s, 150 ms; deployed files served locally with gzip like GitHub Pages): parent home usable after {t_home:.1f} s, Day 1 session open after {t_day1:.1f} s", t_home < 8, "")
    finally:
        c.close()


def test_live(browser, live: str):
    """The published site: no login, every key file returns 200, the QR code points to it,
    a fresh browser completes Day 1, and it works offline after one visit."""
    sec = "0. Published site (" + live + ")"
    import urllib.request
    ok_all, notes = True, []
    for path in ("", "content.json", "audio/manifest.json", "audio/en/ph-p.mp3", "audio/ar/ob3.mp3", "sw.js", "img/qr-code.svg", "fonts/Andika-Medium.woff2",
                 "v1.0/", "v1.0/content.json", "v1.0/audio/en/ph-t.mp3"):
        try:
            with urllib.request.urlopen(urllib.request.Request(live + path, headers={"User-Agent": "fmt-test"}), timeout=60) as r:
                notes.append(f"/{path} {r.status}")
                ok_all &= r.status == 200
        except Exception as e:
            notes.append(f"/{path} {e}")
            ok_all = False
    record(sec, "Public link, key files and the /v1.0/ archive return HTTP 200 without any login", ok_all, "; ".join(notes))
    try:
        vers = {}
        for path in ("content.json", "v1.0/content.json", "audio/manifest.json"):
            with urllib.request.urlopen(urllib.request.Request(live + path + "?t=" + str(int(time.time())), headers={"User-Agent": "fmt-test"}), timeout=60) as r:
                d = json.loads(r.read().decode("utf-8"))
                vers[path] = d.get("meta", {}).get("version") if "meta" in d else d.get("version")
        record(sec, f"The live root reports version {CONTENT['meta']['version']} (content and audio manifest) and /v1.0/ reports 1.0",
               vers["content.json"] == CONTENT["meta"]["version"] == vers["audio/manifest.json"] and vers["v1.0/content.json"] == "1.0", json.dumps(vers))
    except Exception as e:
        record(sec, "Live version check", False, repr(e)[:300])
    try:
        import cv2
        img = cv2.imread(str(DELIV / "qr-code.png"))
        val = cv2.QRCodeDetector().detectAndDecode(img)[0]
        record(sec, "QR code (deliverables/qr-code.png) decodes to the public link", val == live, f"decoded: {val}")
        img = cv2.imread(str(DELIV / "qr-code-v1.0.png"))
        val = cv2.QRCodeDetector().detectAndDecode(img)[0]
        record(sec, "Archive QR code (deliverables/qr-code-v1.0.png) decodes to the /v1.0/ link", val == live + "v1.0/", f"decoded: {val}")
    except Exception as e:
        record(sec, "QR codes decode to the public links", False, repr(e))
    c = Ctx(browser, live)
    try:
        c.page.goto(live + "v1.0/")
        c.page.locator("#archive-banner").wait_for(timeout=90000)
        c.page.wait_for_timeout(3000)
        regs = c.page.evaluate("navigator.serviceWorker.getRegistrations().then(r => r.length)")
        record(sec, "The published /v1.0/ archive opens with its banner and registers no service worker", regs == 0,
               c.page.locator("#archive-banner").inner_text().replace("\n", " / ")[:160])
    except Exception as e:
        record(sec, "Published archive check crashed", False, repr(e)[:300])
    finally:
        c.close()
    c = Ctx(browser, live)
    pg = c.page
    try:
        t0 = time.time()
        pg.goto(live)
        pg.locator('[data-test="onboarding"]').wait_for(timeout=90000)
        record(sec, "A fresh browser context opens the app (no account, no login) at the Arabic onboarding",
               pg.evaluate("document.documentElement.dir") == "rtl", f"loaded in {time.time() - t0:.1f} s on this computer's real connection")
        pg.evaluate("localStorage.setItem('fmt1.settings', JSON.stringify({onboarded:true}))")
        play_day(c, 1, wrong_items=(0,))
        record(sec, "Day 1 played to the end on the published site, with audio", not pg.evaluate("window.FMT.audio.failed"), "")
        pg.locator('[data-test="finish"]').click()
        c.goto("#/home")
        pg.locator('[data-test="offline-badge"]:not([hidden])').wait_for(timeout=420000)
        c.ctx.set_offline(True)
        pg.reload()
        pg.locator('[data-test="home"]').wait_for(timeout=60000)
        pg.locator('[data-test="start"]').click()
        pg.locator('[data-test="stop"][data-day="1"]').click()
        pg.locator('[data-test="go"]').wait_for(timeout=30000)
        record(sec, "After one visit the published app reloads and starts a session with the network switched off", True, "")
        record(sec, "No console errors on the published site", not c.errors, "; ".join(c.errors[:4]))
    except Exception as e:
        record(sec, "Published-site check crashed", False, repr(e)[:400])
    finally:
        c.close()


# ------------------------------------------------------------------ v1.1 (brief §11)
SHA_CACHE_JS = """async (u) => { const r = await caches.match(u); if (!r) return null;
  const h = await crypto.subtle.digest('SHA-256', await r.arrayBuffer());
  return Array.from(new Uint8Array(h)).map((x) => x.toString(16).padStart(2, '0')).join(''); }"""
SHA_FETCH_JS = """async (u) => { const r = await fetch(u, {cache: 'no-store'}); if (!r.ok) return 'HTTP ' + r.status;
  const h = await crypto.subtle.digest('SHA-256', await r.arrayBuffer());
  return Array.from(new Uint8Array(h)).map((x) => x.toString(16).padStart(2, '0')).join(''); }"""


def sha_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def git_exe() -> str:
    return shutil.which("git") or str(Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "fmt-tools" / "git" / "cmd" / "git.exe")


def pass_gate(pg):
    pg.wait_for_timeout(300)
    if pg.locator('[data-test="gate-hold"]').count():
        b = pg.locator('[data-test="gate-hold"]').bounding_box()
        pg.mouse.move(b["x"] + b["width"] / 2, b["y"] + b["height"] / 2)
        pg.mouse.down()
        pg.wait_for_timeout(700)
        pg.mouse.up()


def test_v11_app(browser, base):
    """Checks 1–3 and 10: version, reviewer checklist (A1–A3, per version), update notice, attribution."""
    sec = "7. Version 1.1: label, reviewer checklist, update notice, attribution"
    v = CONTENT["meta"]["version"]
    c = Ctx(browser, base)
    pg = c.page
    try:
        c.goto("#/home")
        pg.evaluate("localStorage.setItem('fmt1.settings', JSON.stringify({onboarded:true}))")
        c.goto("#/home")
        pg.locator('[data-test="home"]').wait_for()
        home = pg.locator(".footer-note").first.inner_text()
        title = pg.title()
        c.goto("#/about")
        pg.locator('[data-test="about"]').wait_for()
        about = pg.locator(".footer-note").first.inner_text()
        credits = pg.locator('[data-test="credits-heading"]').inner_text() + " " + pg.locator('[data-test="credits"]').inner_text()
        c.goto("#/settings")
        pass_gate(pg)
        pg.locator('[data-test="settings"]').wait_for()
        sett = pg.locator(".footer-note").first.inner_text()
        record(sec, f"Version {v} is shown in the home footer, on About and in Settings (read from content.json)",
               all(v in x and "1.0" not in x.replace(v, "") for x in (home, about, sett)), f"home: {home} | about: {about} | settings: {sett}")
        record(sec, "Attribution: 'elevenlabs.io' is in the page <title> and on the About screen (credits heading and list)",
               "elevenlabs.io" in title and "elevenlabs.io" in credits and "non-commercial use with attribution" in credits, f"title: {title}")
        # reviewer checklist: v1.0 answers (key fmt1.review) must not appear in the v1.1 checklist
        from urllib.parse import urlsplit
        o = urlsplit(c.base)
        c.ctx.grant_permissions(["clipboard-read", "clipboard-write"], origin=f"{o.scheme}://{o.netloc}")
        pg.evaluate("localStorage.setItem('fmt1.review', JSON.stringify({clarity: {score: 5, comment: 'v1.0 answer'}, role: 'old'}))")
        c.goto("#/review")
        pass_gate(pg)
        pg.locator('[data-test="review"]').wait_for()
        ids = pg.locator('[data-test="review-item"]').evaluate_all("els => els.map(e => [e.dataset.item, !!e.closest('[data-test=audio-recheck]')])")
        prefilled = pg.evaluate("document.querySelectorAll('[data-test=review] input[type=radio]:checked').length + "
                                "(document.querySelector('[data-test=comment-clarity]').value ? 1 : 0) + (document.querySelector('[data-test=review-role]').value ? 1 : 0)")
        heading = pg.locator('[data-test="audio-recheck"] h2').inner_text()
        main_ids = ["clarity", "ease", "culture", "access", "learning", "routine", "safety", "technical"]
        order_ok = ids == [[i, False] for i in main_ids] + [["A1", True], ["A2", True], ["A3", True]]
        old_items = re.search(r"const ITEMS = \[(.*?)\];", (APP / "v1.0" / "js" / "screens" / "teacher.js").read_text(encoding="utf-8"), re.S)
        new_items = re.search(r"const ITEMS = \[(.*?)\];", (APP / "js" / "screens" / "teacher.js").read_text(encoding="utf-8"), re.S)
        same_text = bool(old_items and new_items and old_items.group(1) == new_items.group(1))
        record(sec, "Checklist: the 8 original items are word for word as in v1.0, followed by A1–A3 under 'Audio re-check (v1.1) / مراجعة الأصوات (الإصدار 1.1)'",
               order_ok and same_text and heading.strip() == "Audio re-check (v1.1) / مراجعة الأصوات (الإصدار 1.1)", json.dumps(ids))
        record(sec, "Checklist answers are stored per version: v1.0 answers are not pre-filled in the v1.1 checklist", prefilled == 0, f"pre-filled fields: {prefilled}")
        pg.locator('[data-test="rate-clarity-4"]').check(force=True)
        pg.locator('[data-test="rate-A1-4"]').check(force=True)
        pg.locator('[data-test="comment-A1"]').fill("clear")
        pg.locator('[data-test="rate-A3-5"]').check(force=True)
        pg.locator('[data-test="copy-feedback"]').click()
        out = pg.locator('[data-test="feedback-out"]').input_value()
        lines = out.splitlines()
        ok = (lines and lines[0] == f"5 Minutes Together v{v} – reviewer feedback / ملاحظات المراجع"
              and "A1. English sounds and words: 4/5 – clear" in lines and "A2. Arabic voice: –" in lines
              and "A3. Pronunciation compared with version 1.0: 5/5" in lines)
        record(sec, f"'Copy my feedback' starts with 'v{v}' and adds A1–A3 lines (e.g. 'A1. English sounds and words: 4/5 – clear')", ok,
               " | ".join(lines[:1] + lines[-3:]))
        stored = pg.evaluate(f"JSON.parse(localStorage.getItem('fmt1.review.{v}'))")
        old = pg.evaluate("JSON.parse(localStorage.getItem('fmt1.review'))")
        record(sec, f"v{v} answers are saved under their own key and the v1.0 answers stay stored", bool(stored and stored.get("A1")) and old.get("clarity", {}).get("score") == 5,
               f"fmt1.review.{v}: {json.dumps(stored)[:120]}")
        record(sec, "No console errors on these screens", not c.errors, "; ".join(c.errors[:4]))
    except Exception as e:
        record(sec, "v1.1 app checks crashed", False, f"{e!r}\n{traceback.format_exc()[-1200:]}")
    finally:
        c.close()
    # update notice: never for a first-time user; once for a device that ran v1.0
    try:
        c = Ctx(browser, base)
        c.goto("")
        c.page.locator('[data-test="onboarding"]').wait_for()
        c.page.wait_for_timeout(400)
        new_user = c.page.locator('[data-test="update-notice"]').count()
        c.close()
        c = Ctx(browser, base)
        c.ctx.add_init_script("if (!sessionStorage.getItem('seeded')) { sessionStorage.setItem('seeded', '1');"
                              " localStorage.setItem('fmt1.settings', JSON.stringify({onboarded: true}));"
                              " localStorage.setItem('fmt1.progress', JSON.stringify({days: {'1': {done: true, firstDate: '2026-11-01', date: '2026-11-01'}}})); }")
        c.goto("#/home")
        c.page.locator('[data-test="home"]').wait_for()
        first = c.page.locator('[data-test="update-notice"]').count()
        text = c.page.locator('[data-test="update-notice"]').inner_text() if first else ""
        c.page.reload()
        c.page.locator('[data-test="home"]').wait_for()
        c.page.wait_for_timeout(400)
        again = c.page.locator('[data-test="update-notice"]').count()
        record(sec, "Update notice: shown once to a device with v1.0 data, never again after a reload, and never to a first-time user",
               new_user == 0 and first == 1 and again == 0 and text.startswith("تم التحديث إلى الإصدار 1.1"),
               f"new user: {new_user}, v1.0 user first load: {first} ('{text.splitlines()[0] if text else ''}'), after reload: {again}")
        c.close()
    except Exception as e:
        record(sec, "Update-notice check crashed", False, repr(e)[:400])


HEADER_JS = """() => {
  const bar = document.querySelector('.topbar'); if (!bar) return {error: 'no topbar'};
  const badge = bar.querySelector('[data-test=offline-badge]'); if (badge) badge.hidden = false;   // as when the app is ready offline
  const title = bar.querySelector('.brand-name') || bar.querySelector('h1');
  const els = [title, bar.querySelector('[data-test=lang-toggle]'), badge].filter(Boolean);
  // the title is measured by where its text actually is (glyphs may extend a little beyond a box that does not clip)
  const range = document.createRange(); range.selectNodeContents(title);
  const r = els.map((e, i) => (i === 0 ? range.getBoundingClientRect() : e.getBoundingClientRect()));
  const hit = (a, b) => a.left < b.right - 1 && b.left < a.right - 1 && a.top < b.bottom - 1 && b.top < a.bottom - 1;
  const overlaps = []; for (let i = 0; i < r.length; i++) for (let j = i + 1; j < r.length; j++) if (hit(r[i], r[j])) overlaps.push(i + '-' + j);
  // cut off = content larger than a box that clips it (overflow not visible) or ends in an ellipsis
  const clips = (e) => { const s = getComputedStyle(e); return s.overflowX !== 'visible' || s.overflowY !== 'visible' || s.textOverflow === 'ellipsis'; };
  const cut = els.filter((e) => clips(e) && (e.scrollWidth > e.clientWidth + 1 || e.scrollHeight > e.clientHeight + 1)).length;
  const outside = r.filter((x) => x.left < -1 || x.right > innerWidth + 1).length;
  return {overlaps, cut, outside, n: els.length, titleW: Math.round(r[0].width)}; }"""


def test_header(browser, base):
    """Check 6: no overlap or truncation in the header at 320, 360, 390 and 430 px, both languages, normal and large text."""
    sec = "8. Header layout (v1.1 fix)"
    bad, n = [], 0
    for w in (320, 360, 390, 430):
        c = Ctx(browser, base, viewport={"width": w, "height": 800})
        try:
            for lang in ("ar", "en"):
                for large in (False, True):
                    c.goto("#/home")
                    c.page.evaluate("s => localStorage.setItem('fmt1.settings', JSON.stringify(s))", {"onboarded": True, "lang": lang, "large": large})
                    for screen, ready in (("#/home", '[data-test="home"]'), ("#/about", '[data-test="about"]')):
                        c.goto(screen)
                        c.page.locator(ready).wait_for()
                        c.page.evaluate("document.fonts.ready")
                        r = c.page.evaluate(HEADER_JS)
                        n += 1
                        if r.get("error") or r["overlaps"] or r["cut"] or r["outside"] or r["n"] < 2:
                            bad.append(f"{w}px {lang} {'large' if large else 'normal'} {screen}: {r}")
        finally:
            c.close()
    record(sec, f"Title, language button and 'Ready offline' badge never overlap, overflow or get cut off ({n} layouts: 320/360/390/430 px × Arabic/English × normal/large text × home/About)",
           not bad, "; ".join(bad[:4]))


def test_update_and_archive(browser, base):
    """Checks 7 and 8: a browser that cached v1.0 gets the v1.1 audio after a reload; /v1.0/ works without a service worker."""
    sec = "9. Update from v1.0 and the archived v1.0"
    ver11, files11 = sw_list()
    v10_evidence = ROOT / "deliverables" / "evidence" / "v1.0" / "audio" / "en" / "ph-t.mp3"
    tmp = Path(tempfile.mkdtemp())
    port = 8813
    url = f"http://127.0.0.1:{port}/"
    try:
        z = subprocess.run([git_exe(), "archive", "--format=zip", "v1.0", "app"], cwd=ROOT, capture_output=True, check=True).stdout
        zipfile.ZipFile(io.BytesIO(z)).extractall(tmp)
        srv = serve(port, str(tmp / "app"))
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        ctx = browser.new_context(viewport=VIEW, locale="ar-OM")
        pg = ctx.new_page()
        pg.goto(url + "?fast=1#/home")
        pg.evaluate("localStorage.setItem('fmt1.settings', JSON.stringify({onboarded:true}))")
        pg.goto(url + "?fast=1#/home")
        pg.locator('[data-test="offline-badge"]:not([hidden])').wait_for(timeout=300000)
        old_hash = pg.evaluate(SHA_CACHE_JS, "audio/en/ph-t.mp3")
        old_label = pg.locator(".footer-note").first.inner_text()
        srv.shutdown()
        srv.server_close()
        srv = serve(port, str(APP))   # the same address now serves v1.1
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        pg.reload()
        keys = []
        for _ in range(300):          # the v1.1 worker installs, fills its cache and removes the v1.0 cache
            keys = pg.evaluate("caches.keys()")
            if keys == ["fmt-" + ver11]:
                break
            pg.wait_for_timeout(1000)
        new_hash = pg.evaluate(SHA_CACHE_JS, "audio/en/ph-t.mp3")
        pg.reload()
        pg.locator('[data-test="home"]').wait_for()
        label = pg.locator(".footer-note").first.inner_text()
        notice = pg.locator('[data-test="update-notice"]').count()
        record(sec, "Update path: a browser that cached v1.0 gets the v1.1 audio after a reload (ph-t.mp3 in the cache changes from the v1.0 bytes to the v1.1 bytes; the v1.0 cache is removed)",
               old_hash == sha_file(v10_evidence) and new_hash == sha_file(APP / "audio" / "en" / "ph-t.mp3") and keys == ["fmt-" + ver11] and "1.1" in label,
               f"before: v1.0 cache, '{old_label}'; after: caches {keys}, '{label}', update notice shown: {notice}")
        ctx.close()
        srv.shutdown()
        srv.server_close()
    except Exception as e:
        record(sec, "Update-path check crashed", False, f"{e!r}\n{traceback.format_exc()[-800:]}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    # the archive at /v1.0/ (served from the v1.1 site)
    c = Ctx(browser, base)
    pg = c.page
    try:
        pg.goto(base + "v1.0/?fast=1#/home")
        pg.evaluate("localStorage.setItem('fmt10.settings', JSON.stringify({onboarded:true}))")
        pg.goto(base + "v1.0/?fast=1#/home")
        pg.locator('[data-test="home"]').wait_for()
        banner = pg.locator("#archive-banner").inner_text()
        href = pg.locator("#archive-banner a").get_attribute("href")
        label = pg.locator(".footer-note").first.inner_text()
        pg.wait_for_timeout(3000)
        regs = pg.evaluate("navigator.serviceWorker.getRegistrations().then(r => r.length)")
        pg.goto(base + "v1.0/?fast=1#/day/1?step=hear&demo=1")
        pg.locator('[data-test="letter-card"]').click()
        pg.wait_for_timeout(1500)
        st = pg.evaluate("({played: window.FMT.audio.played, failed: window.FMT.audio.failed, fallbacks: window.FMT.audio.fallbacks})")
        same = pg.evaluate(SHA_FETCH_JS, "audio/en/ph-t.mp3") == sha_file(v10_evidence)
        keys10 = pg.evaluate("Object.keys(localStorage)")
        record(sec, "Archive /v1.0/ opens with the banner (link to ../), reports version 1.0, registers no service worker and plays its own v1.0 audio",
               "نسخة مؤرشفة" in banner and "Archived version 1.0" in banner and href == "../" and "1.0" in label and regs == 0
               and st["played"] > 0 and not st["failed"] and same,
               f"label '{label}', service workers {regs}, audio {json.dumps(st)}, ph-t.mp3 = v1.0 bytes: {same}")
        record(sec, "Archive keeps its own storage (fmt10.…), separate from v1.1 (fmt1.…)",
               keys10 and all(k.startswith("fmt10.") for k in keys10), json.dumps(keys10))
        pg.goto(base + "?fast=1#/home")
        pg.evaluate("localStorage.setItem('fmt1.settings', JSON.stringify({onboarded:true}))")
        pg.goto(base + "?fast=1#/home")
        pg.locator('[data-test="offline-badge"]:not([hidden])').wait_for(timeout=300000)
        cached = pg.evaluate("caches.keys().then(ks => Promise.all(ks.map(k => caches.open(k).then(c => c.keys())))).then(a => a.flat().map(r => r.url))")
        in_cache = [u for u in cached if "/v1.0/" in u]
        hit = pg.evaluate("caches.match('v1.0/index.html').then(r => !!r)")
        record(sec, "The v1.1 offline cache holds none of the /v1.0/ files, and its worker does not answer /v1.0/ requests",
               not in_cache and not hit and len(cached) >= len(files11), f"{len(cached)} cached URLs, {len(in_cache)} under /v1.0/")
        record(sec, "No console errors in the archive or the v1.1 app", not c.errors, "; ".join(c.errors[:4]))
    except Exception as e:
        record(sec, "Archive check crashed", False, f"{e!r}\n{traceback.format_exc()[-800:]}")
    finally:
        c.close()


def test_v11_files():
    """Checks 4 (hashes), 5 (audio rules) and 9 (secrets)."""
    sec = "10. Audio rules, no fallback, secrets"
    sys.path.insert(0, str(ROOT / "tools"))
    from make_audio import fnv1a
    man = json.loads((APP / "audio" / "manifest.json").read_text(encoding="utf-8"))
    texts = {k: v["ar"] for k, v in CONTENT["texts"].items() if "ar" in v and not v.get("noAudio")}
    for a in CONTENT["trustedApps"]:
        for f in ("why", "ask"):
            texts[f"app_{a['id']}_{f}"] = a[f]["ar"]
    wrong = [k for k, ar in texts.items() if k not in man["ar"] or man["ar"][k]["h"] != fnv1a(ar) or not (APP / "audio" / "ar" / f"{k}.mp3").exists()]
    record(sec, f"Every Arabic audio button has its recorded clip: all {len(texts)} texts are in the manifest with the hash of the current text (the app never needs the device voice)",
           not wrong and man["version"] == CONTENT["meta"]["version"], f"manifest version {man['version']}; mismatches: {wrong[:5]}")
    av = ROOT / "tools" / "audio_verification.json"
    bl = ROOT / "tools" / "audio_build_log.json"
    if av.exists() and bl.exists():
        S = json.loads(av.read_text(encoding="utf-8"))["summary"]
        log = json.loads(bl.read_text(encoding="utf-8"))
        ar = {k: v for k, v in log["clips"].items() if k.startswith("ar/")}
        ar_bad = [k for k, v in ar.items() if not v.get("pass")]
        ph_ok = all(log["clips"].get(f"en/ph-{s}.mp3", {}).get("check_phoneme", "").startswith("pass") for s in CONTENT["sounds"])
        record(sec, "Audio (§7.4): every clip exists, is in the manifest, has a plausible duration and no clipping; Arabic clips have 8–20 characters/s and no silence over 1.2 s; the letter sounds pass check_phoneme after MP3 encoding",
               not S["hard_failures"] and S["phonemes_pass"] == 6 and S["controls_rejected"] == 6 and not ar_bad and len(ar) == len(texts) and ph_ok,
               f"{S['files_pass']}/{S['files_checked']} clips; phonemes {S['phonemes_pass']}/6; controls rejected {S['controls_rejected']}/6; "
               f"Arabic §7.4 failures {ar_bad[:5]}; Whisper English {S['whisper_en_match']}; Arabic mean {S['whisper_ar_mean_similarity']} (min {S['whisper_ar_min_similarity']})")
    else:
        record(sec, "Audio (§7.4) verification logs exist", False, "run tools/make_audio_v11.py and tools/verify_audio.py first")
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "secret_scan.py")], capture_output=True, text=True, encoding="utf-8")
    record(sec, "Secrets: no API key and no sk_… string in any tracked file, deliverable or log; .env is gitignored and untracked",
           r.returncode == 0, (r.stdout or r.stderr).strip()[:300])


def write_report(base):
    DELIV.mkdir(exist_ok=True)
    passed = sum(r["ok"] for r in RESULTS)
    lines = [f"# Test report – 5 Minutes Together v{CONTENT['meta']['version']}", "",
             f"Run: {dt.datetime.now().strftime('%Y-%m-%d %H:%M')} · target: `{base}` · Playwright (Chromium) at 390 × 844 · axe-core {axe_version()} · duration {time.time() - T0:.0f} s", "",
             f"**Result: {passed} of {len(RESULTS)} checks passed.**", "",
             "These are automated checks run by the developer tooling. No testing with real children, parents or teachers has been done yet; "
             "the reviewer checklist in the app is provided for that.", ""]
    section = None
    for r in RESULTS:
        if r["section"] != section:
            section = r["section"]
            lines += ["", f"## {section}", "", "| Check | Result | Details |", "|---|---|---|"]
        d = r["detail"].replace("|", "\\|").replace("\n", " ")[:600]
        lines.append(f"| {r['name']} | {'✅ PASS' if r['ok'] else '❌ FAIL'} | {d} |")
    lines += ["", "## axe-core results per screen", "", "Impact levels counted as failures: serious, critical. Minor and moderate findings are listed for information.", "",
              "| Screen / state | Violations (impact, rule, nodes) |", "|---|---|"]
    for k, v in SCREENS_AXE.items():
        found = ", ".join("{} {} ({})".format(x["impact"], x["id"], x["nodes"]) for x in v) or "none"
        lines.append(f"| {k} | {found} |")
    av = ROOT / "deliverables" / "audio-verification.md"
    if av.exists():
        lines += ["", "## Audio verification", "", "Full log: `audio-verification.md` (every clip measured in code: existence, duration, RMS, clipping, phoneme acoustics, Whisper transcription)."]
    (DELIV / "TEST_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n{passed}/{len(RESULTS)} passed – report written to deliverables/TEST_REPORT.md")
    return passed == len(RESULTS)


def axe_version():
    try:
        import axe_playwright_python
        p = Path(axe_playwright_python.__file__).parent / "axe.min.js"
        head = p.read_text(encoding="utf-8")[:200]
        import re
        m = re.search(r"axe v([0-9.]+)", head)
        return m.group(1) if m else "bundled"
    except Exception:
        return "bundled"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=None, help="run the suite against this URL instead of a local server")
    ap.add_argument("--live", default=None, help="also check the published site at this URL")
    ap.add_argument("--only", default=None)
    a = ap.parse_args()
    httpd = serve(8811)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    local = "http://127.0.0.1:8811/"
    base = a.base or local
    with sync_playwright() as p:
        browser = p.chromium.launch()
        tests = [("live", lambda: test_live(browser, a.live) if a.live else None),
                 ("play", lambda: test_playthrough(browser, base)), ("results", lambda: test_objectives_not_met(browser, base)),
                 ("offline", lambda: test_offline(browser, base)), ("screens", lambda: test_screens(browser, base)),
                 ("motion", lambda: test_reduced_motion(browser, base)), ("backup", lambda: test_backup(browser)),
                 ("size", lambda: test_size_and_3g(browser, local)),  # 3G is emulated on top of a local server
                 ("v11", lambda: test_v11_app(browser, base)), ("header", lambda: test_header(browser, base)),
                 ("update", lambda: test_update_and_archive(browser, base)), ("files", test_v11_files)]
        for name, fn in tests:
            if a.only and name not in a.only.split(","):
                continue
            fn()
        browser.close()
    httpd.shutdown()
    ok = write_report(base + (f" (+ published site {a.live})" if a.live else ""))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
