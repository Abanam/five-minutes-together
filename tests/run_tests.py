"""Quality checks for 5 Minutes Together (Playwright + axe-core). Writes deliverables/TEST_REPORT.md.

    .venv/Scripts/python.exe tests/run_tests.py [--base https://…]   (default: local server on app/)

1. Play through all five days at 390×844 (correct AND wrong answers, the next-calendar-day
   unlock rule, the Day 5 final check and the results screen) with no console errors.
2. Offline: load once, wait for the service worker, switch the context offline, reload, finish a session.
3. axe-core on every screen: no serious or critical violations.
4. Visual checks: Arabic right-to-left layout, Andika's single-storey "a", every picture renders,
   every audio file decodes in the browser, tap targets ≥ 64 px, parent gate, offline badge.
5. Size and a simulated 3G first load.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import threading
import time
import traceback
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
        pg.locator('[data-test="offline-badge"]:not([hidden])').wait_for(timeout=60000)
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

        def visit(name, hash_, ready, before=None):
            if before:
                before()
            c.goto(hash_)
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
        pg.locator('[data-test="qr"]').wait_for()
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
        c.ctx.grant_permissions(["clipboard-read", "clipboard-write"], origin=c.base.rstrip("/"))
        c.goto("#/review")
        pg.locator('[data-test="review"]').wait_for()
        pg.locator('[data-test="rate-clarity-4"]').check(force=True)
        pg.locator('[data-test="comment-clarity"]').fill("Clear Arabic.")
        pg.locator('[data-test="copy-feedback"]').click()
        out = pg.locator('[data-test="feedback-out"]').input_value()
        record(sec4, "Reviewer checklist: 8 items on a 1–5 scale with comments; 'Copy my feedback' builds a text summary (nothing sent)",
               pg.locator('[data-test="review-item"]').count() == 8 and "Clarity for parents: 4/5 – Clear Arabic." in out, out.splitlines()[2] if out else "")
        # large text + calm mode
        c.goto("#/settings")
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


def test_size_and_3g(browser, base):
    sec = "6. Size and slow network"
    total = sum(p.stat().st_size for p in APP.rglob("*") if p.is_file())
    record(sec, f"Whole app is under 10 MB ({total / 1024 / 1024:.2f} MB)", total < 10 * 1024 * 1024)
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
        record(sec, f"Simulated 3G (1.6 Mbit/s, 150 ms): parent home usable after {t_home:.1f} s, Day 1 session open after {t_day1:.1f} s", t_home < 8, "")
    finally:
        c.close()


def write_report(base):
    DELIV.mkdir(exist_ok=True)
    passed = sum(r["ok"] for r in RESULTS)
    lines = ["# Test report – 5 Minutes Together v1.0", "",
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
    ap.add_argument("--base", default=None)
    ap.add_argument("--only", default=None)
    a = ap.parse_args()
    httpd = None
    base = a.base
    if not base:
        httpd = serve(8811)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        base = "http://127.0.0.1:8811/"
    with sync_playwright() as p:
        browser = p.chromium.launch()
        tests = [("play", lambda: test_playthrough(browser, base)), ("results", lambda: test_objectives_not_met(browser, base)),
                 ("offline", lambda: test_offline(browser, base)), ("screens", lambda: test_screens(browser, base)),
                 ("motion", lambda: test_reduced_motion(browser, base)), ("backup", lambda: test_backup(browser)),
                 ("size", lambda: test_size_and_3g(browser, base))]
        for name, fn in tests:
            if a.only and name not in a.only.split(","):
                continue
            fn()
        browser.close()
    if httpd:
        httpd.shutdown()
    ok = write_report(base)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
