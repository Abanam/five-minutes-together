"""Take the report screenshots at 390×844 (2× scale) from REAL app states (the days are actually
played with a fake calendar). Writes deliverables/screenshots/NN-name.png plus extra screens for
the all-screens backup PDF (deliverables/screenshots/extra/).

    python tools/screenshots.py [--base https://…] [--out deliverables/screenshots-v1.1]

v1.1 adds extra screens: About credits with the attribution, the reviewer audio re-check block, the one-time
update notice, the fixed English home header (390 and 320 px) and the /v1.0/ archive banner.
"""
import argparse
import datetime as dt
import json
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))
from serve import serve  # noqa: E402
from run_tests import Ctx, play_day, day_time, CONTENT  # noqa: E402

OUT = ROOT / "deliverables" / "screenshots"
EXTRA = OUT / "extra"
SHOTS = []  # (file, title) in order, for the PDF


def shot(pg, name, title, extra=False, full=False):
    d = EXTRA if extra else OUT
    d.mkdir(parents=True, exist_ok=True)
    pg.wait_for_timeout(350)
    path = d / f"{name}.png"
    pg.screenshot(path=str(path), full_page=full)
    SHOTS.append((str(path.relative_to(ROOT / "deliverables")).replace("\\", "/"), title))
    print("shot", name)


def main():
    global OUT, EXTRA
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=None)
    ap.add_argument("--out", default=None, help="folder for the screenshots (default deliverables/screenshots)")
    a = ap.parse_args()
    if a.out:
        OUT = (ROOT / a.out) if not Path(a.out).is_absolute() else Path(a.out)
        EXTRA = OUT / "extra"
    httpd = None
    base = a.base
    if not base:
        httpd = serve(8821)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        base = "http://127.0.0.1:8821/"
    for old in list(OUT.glob("*.png")) + list(EXTRA.glob("*.png")):
        old.unlink()
    with sync_playwright() as p:
        b = p.chromium.launch()
        c = Ctx(b, base, device_scale_factor=2)
        pg = c.page
        pg.clock.set_fixed_time(day_time(1))
        # onboarding (fresh device)
        c.goto("#/onboarding/1")
        pg.locator('[data-test="onboarding"]').wait_for()
        shot(pg, "02-onboarding", "Onboarding 1 of 3 – what the app is (Arabic text + audio)")
        c.goto("#/onboarding/2")
        pg.locator('[data-test="onboarding"][data-step="2"]').wait_for()
        shot(pg, "onboarding-2", "Onboarding 2 of 3 – how 5 minutes a day works", extra=True)
        c.goto("#/onboarding/3")
        pg.locator('[data-test="onboarding"][data-step="3"]').wait_for()
        shot(pg, "onboarding-3", "Onboarding 3 of 3 – “You don't need to know English”", extra=True)
        pg.locator('[data-test="ob-next"]').click()
        pg.locator('[data-test="home"]').wait_for()
        shot(pg, "home-day1", "Parent home on the first day", extra=True)
        # really play Day 1 and Day 2 on their calendar days
        play_day(c, 1, wrong_items=())
        pg.locator('[data-test="finish"]').click()
        pg.clock.set_fixed_time(day_time(2))
        play_day(c, 2, wrong_items=())
        pg.locator('[data-test="finish"]').click()
        pg.locator('[data-test="home"]').wait_for()
        shot(pg, "home-locked", "Parent home after Day 2 – the next day opens tomorrow", extra=True)
        c.goto("#/map")
        pg.locator('[data-test="stop"][data-day="3"]').click()
        pg.locator('.toast').wait_for()
        shot(pg, "locked-day", "Locked stop: “This day opens tomorrow” (screen-time limit)", extra=True)
        # Day 3 (normal speed so animations and audio-driven states are real)
        pg.clock.set_fixed_time(day_time(3))
        c.goto("#/home", fast=False)
        pg.locator('[data-test="home"]').wait_for()
        shot(pg, "01-parent-home", "Parent home – today's stop, Start button, 5-day progress, latest results, links")
        pg.locator('[data-test="start"]').click()
        pg.locator('[data-test="map"]').wait_for()
        shot(pg, "03-journey-map", "Journey map – beach, palm grove, fort, wadi, sea with a dhow; finished stops light up")
        pg.locator('[data-test="stop"][data-day="3"]').click()
        pg.locator('[data-test="go"]').wait_for()
        shot(pg, "session-start", "Session start – Sanad greets the child; parent tip and support level", extra=True)
        pg.locator('[data-test="go"]').click()
        pg.locator('[data-test="letter-card"]').wait_for()
        pg.locator('[data-test="letter-card"]').click()
        pg.wait_for_timeout(900)
        shot(pg, "04-hear-it", "Hear it – tap the letter to hear the pure sound; Arabic parent card with pronunciation tip")
        pg.locator('[data-test="next"]:visible').click()
        pg.locator('[data-test="kw"]').first.wait_for()
        for i in range(2):
            pg.locator('[data-test="kw"]').nth(i).click()
            pg.wait_for_timeout(1900)
        shot(pg, "keyword-pictures", "Hear it – keyword pictures (“i… insect”, “i… ink”)", extra=True)
        pg.locator('[data-test="next"]:visible').click()
        f = CONTENT["days"][2]["hear"]["find"][0]
        pg.locator('[data-test="find-pic"]').first.wait_for()
        pg.wait_for_timeout(2500)
        good = [x for x in f["pictures"] if CONTENT["keywords"][x]["first"] == f["sound"]]
        pg.locator(f'[data-test="find-pic"][data-word="{good[0]}"]').click()
        pg.wait_for_timeout(250)
        shot(pg, "find-the-sound", "Find the sound – instant feedback: chime, Sanad hops, stars, tick", extra=True)
        pg.wait_for_timeout(900)
        pg.locator(f'[data-test="find-pic"][data-word="{good[1]}"]').click()
        pg.locator('[data-test="next"]:visible').click()
        # tap and say
        w = CONTENT["days"][2]["tapSay"][1]["word"]
        pg.locator('.tiles[data-word="it"]').wait_for()
        for i in range(pg.locator('[data-test="word-tile"]').count()):
            pg.locator('[data-test="word-tile"]').nth(i).click()
            pg.wait_for_timeout(700)
        pg.locator('[data-test="ask-card"], [data-test="train"]:not([disabled])').first.wait_for()
        pg.locator('[data-test="train"]').click()
        pg.locator('[data-test="ask-card"]').wait_for()
        pg.locator('[data-test="next"]:visible').click()
        pg.locator(f'.tiles[data-word="{w}"]').wait_for()
        tiles = pg.locator('[data-test="word-tile"]')
        tiles.nth(0).click()
        pg.wait_for_timeout(800)
        shot(pg, "05-tap-and-say", "Tap and say – each letter tile plays its sound; the sound train joins them")
        for i in range(1, tiles.count()):
            tiles.nth(i).click()
            pg.wait_for_timeout(800)
        pg.locator('[data-test="train"]:not([disabled])').click()
        pg.locator('[data-test="ask-card"]').wait_for()
        pg.wait_for_timeout(1500)
        shot(pg, "06-ask-your-child", "Ask your child – Arabic question card with audio after the word is revealed")
        for item in CONTENT["days"][2]["tapSay"][2:]:
            pg.locator('[data-test="next"]:visible').click()
            pg.locator(f'.tiles[data-word="{item["word"]}"]').wait_for()
            for i in range(pg.locator('[data-test="word-tile"]').count()):
                pg.locator('[data-test="word-tile"]').nth(i).click()
                pg.wait_for_timeout(450)
            pg.locator('[data-test="train"]:not([disabled])').click()
            pg.locator('[data-test="ask-card"]').wait_for()
        pg.locator('[data-test="next"]:visible').click()
        # blend on your own
        pg.locator('[data-test="said-right"]').wait_for()
        pg.wait_for_timeout(600)
        shot(pg, "07-blend-on-your-own", "Blend on your own – the child reads; the parent taps “قالها صح ✓” or “نحاول مرة ثانية ↺”")
        for j, bw in enumerate(CONTENT["days"][2]["blend"]):
            pg.locator(f'.tiles[data-word="{bw}"]').wait_for()
            if j == 1:
                pg.locator('[data-test="try-again"]').click()
                pg.wait_for_timeout(700)
                shot(pg, "blend-try-again", "“Let's try again”: gentle “Let's listen again” and the sounds replay – no buzzer or red cross", extra=True)
            pg.locator('[data-test="said-right"]').click()
            pg.locator('[data-test="reveal"]').wait_for()
            pg.locator('[data-test="next"]:visible').click()
        # challenge
        pg.locator('[data-test="go-challenge"]').click()
        items = CONTENT["days"][2]["challenge"]
        for k, it in enumerate(items):
            pg.locator(".progress-dots b.now", has_text=str(k + 1)).wait_for()
            pg.wait_for_timeout(1200 if it["type"] == "sound" else 3000)
            if k == 1:
                shot(pg, "09-sanads-challenge", "Sanad's challenge – hear the separate sounds, choose the matching picture")
            pg.locator(f'[data-test="choice"][data-value="{it["target"]}"]').click()
            if k == 1:
                pg.wait_for_timeout(260)
                shot(pg, "08-correct-feedback", "Correct answer – synthesised chime, Sanad hops, stars burst, tick on the picture")
        pg.locator('[data-test="stop-sign"]').wait_for()
        pg.wait_for_timeout(1200)
        shot(pg, "10-sticker-reward", "Sticker reward – one sticker per day, “See you tomorrow”, clear stopping point and home activity")
        shot(pg, "sticker-reward-full", "Celebration screen (full page) with the no-screen home activity", extra=True, full=True)
        pg.locator('[data-test="to-stickers"]').click()
        pg.locator('[data-test="sticker-book"]').wait_for()
        shot(pg, "sticker-book", "Sticker book – three stickers earned after Day 3", extra=True)
        # Days 4 and 5 (Day 5 = final check)
        pg.clock.set_fixed_time(day_time(4))
        play_day(c, 4, wrong_items=())
        pg.locator('[data-test="finish"]').click()
        pg.clock.set_fixed_time(day_time(5))
        c.goto("#/day/5?step=start&demo=1")
        pg.locator('[data-test="go"]').wait_for()
        shot(pg, "day5-you-can-do-it", "Day 5 – support level “You can do it”: no automatic audio, hints on request", extra=True)
        play_day(c, 5, wrong_items=(4,))
        pg.wait_for_timeout(400)
        pg.locator('[data-test="finish"]').click()
        pg.locator('[data-test="results"]').wait_for()
        pg.locator('[data-test="objectives"]').scroll_into_view_if_needed()
        shot(pg, "11-parent-results", "Parent results – O1 and O2 after the Day 5 final check, O3 sessions, what to practise")
        c.goto("#/results")
        pg.locator('[data-test="results"]').wait_for()
        shot(pg, "results-full", "Results (full page)", extra=True, full=True)
        c.goto("#/tips")
        pg.locator('[data-test="tips"]').wait_for()
        shot(pg, "12-pronunciation-tips", "Pronunciation tips – the brief's Arabic tips as text and audio, with the sound itself")
        c.goto("#/apps")
        pg.locator('[data-test="apps"]').wait_for()
        shot(pg, "13-trusted-apps", "Trusted free apps – checked free and ad-free; links behind the parent gate")
        c.goto("#/howto")
        pg.locator('[data-test="howto"]').wait_for()
        shot(pg, "how-to-use", "How to use – Arabic guidance with audio for each part", extra=True)
        c.goto("#/about")
        pg.locator('[data-test="about"]').wait_for()
        pg.locator('[data-test="privacy"]').scroll_into_view_if_needed()
        shot(pg, "about-privacy", f"About and privacy – “No data leaves this device”, credits, v{CONTENT['meta']['version']}, AI note", extra=True)
        pg.evaluate("document.querySelector('[data-test=credits-heading]').scrollIntoView({block: 'start'}); window.scrollBy(0, -96)")
        shot(pg, "v11-about-credits", "About – voice credits “Voices: elevenlabs.io · الأصوات” (ElevenLabs free plan: non-commercial use with attribution)", extra=True)
        # parent gate and gated pages
        c.goto("#/teachers")
        pg.locator('[data-test="gate-hold"]').wait_for()
        shot(pg, "parent-gate", "Parent gate – press and hold for 3 seconds (Arabic instruction with audio)", extra=True)
        box = pg.locator('[data-test="gate-hold"]').bounding_box()
        pg.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        pg.mouse.down()
        pg.wait_for_timeout(3400)
        pg.mouse.up()
        pg.locator('[data-test="teachers"]').wait_for()
        pg.locator('[data-test="flyer-preview"]').scroll_into_view_if_needed()
        shot(pg, "14-teacher-page", "For teachers – 1-minute Arabic guide, flyer with QR code, WhatsApp message, printable cards")
        c.goto("#/teachers")
        pg.locator('[data-test="teachers"]').wait_for()
        shot(pg, "teacher-page-full", "For teachers (full page)", extra=True, full=True)
        c.goto("#/review")
        pg.locator('[data-test="review"]').wait_for()
        shot(pg, "15-reviewer-checklist", "Reviewer checklist – 8 items, 1–5 scale, comments, “Copy my feedback”; nothing is sent")
        if pg.locator('[data-test="audio-recheck"]').count():
            pg.evaluate("document.querySelector('[data-test=audio-recheck]').scrollIntoView({block: 'start'}); window.scrollBy(0, -96)")
            shot(pg, "v11-review-audio-recheck", "Reviewer checklist – the v1.1 audio re-check block (A1–A3)", extra=True)
        c.goto("#/settings")
        pg.locator('[data-test="settings"]').wait_for()
        shot(pg, "settings", "Settings – language, large text, calm mode, sounds, unlock all days, reset", extra=True)
        c.goto("#/home")
        pg.locator('[data-test="lang-toggle"]').click()
        pg.locator('[data-test="home"]').wait_for()
        pg.evaluate("document.querySelectorAll('[data-test=offline-badge]').forEach(b => { b.hidden = false; })")  # as when ready offline
        shot(pg, "home-english", "English view of the parent area (left-to-right); v1.1 header: the title uses the full width, the badge sits below", extra=True)
        pg.set_viewport_size({"width": 320, "height": 700})
        pg.wait_for_timeout(300)
        shot(pg, "v11-home-english-320px", "v1.1 header fix at 320 px (English): nothing is squeezed, cut off or covered", extra=True)
        pg.set_viewport_size({"width": 390, "height": 844})
        pg.locator('[data-test="lang-toggle"]').click()
        pg.locator('[data-test="home"]').wait_for()
        pg.locator('[data-test="tour"]').click()
        pg.locator('[data-test="tour-card"]').wait_for()
        pg.wait_for_timeout(600)
        shot(pg, "16-assessor-tour", "Assessor tour – English overlay; each stop names the requirement it meets")
        c.close()
        if CONTENT["meta"]["version"] != "1.0":
            # the one-time update notice, as a device that used v1.0 sees it after the update
            c = Ctx(b, base, device_scale_factor=2)
            c.ctx.add_init_script("if (!sessionStorage.getItem('seeded')) { sessionStorage.setItem('seeded', '1');"
                                  " localStorage.setItem('fmt1.settings', JSON.stringify({onboarded: true}));"
                                  " localStorage.setItem('fmt1.progress', JSON.stringify({days: {'1': {done: true, firstDate: '2026-11-24', date: '2026-11-24'}}})); }")
            c.goto("#/home")
            c.page.locator('[data-test="update-notice"]').wait_for()
            shot(c.page, "v11-update-notice", "One-time update notice (only on a device that used v1.0): “تم التحديث إلى الإصدار 1.1 …”", extra=True)
            c.close()
            # the archived v1.0 at …/v1.0/
            c = Ctx(b, base, device_scale_factor=2)
            c.page.goto(base + "v1.0/?fast=1#/home")
            c.page.evaluate("localStorage.setItem('fmt10.settings', JSON.stringify({onboarded:true}))")
            c.page.goto(base + "v1.0/?fast=1#/home")
            c.page.locator("#archive-banner").wait_for()
            c.page.locator('[data-test="home"]').wait_for()
            shot(c.page, "v11-archive-banner", "The archived version 1.0 at …/v1.0/ with its banner linking to the current version", extra=True)
            c.close()
        b.close()
    if httpd:
        httpd.shutdown()
    (OUT / "order.json").write_text(json.dumps(SHOTS, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(SHOTS)} screenshots")


if __name__ == "__main__":
    main()
