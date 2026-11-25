# 5 Minutes Together – خمس دقائق معًا

**Live app:** https://abanam.github.io/five-minutes-together/

A free, offline-ready web app (PWA) that gives Omani families a **5-minute daily English letter–sound routine** for Grade 1–2 children. The app says the sounds; the parent, who does not need to know English, follows short Arabic instructions (text and audio), encourages and asks. Prototype for EDEN4233 *Technology for Initial Language Literacy*, Rustaq College of Education (UTAS), Oman. Version **1.0**.

- Five days: **s a t** · **p** · **i** · **n** · review, with the same steps every day: Hear it → Tap and say → Blend on your own → Sanad's challenge → sticker and stop.
- Support fades across the week (Vygotsky's zone of proximal development): "I say, you repeat" → "Ask and help" → "You can do it".
- Measurable objectives O1–O3 with a parent results page.
- No accounts, ads, chat or tracking. Nothing leaves the device.

## Use it

Open the live link on any phone or computer; no login. On a phone, "Add to Home Screen" installs it. After the first visit it works **without internet** ("Ready offline ✓ / جاهز دون إنترنت"). Teachers: the "For teachers" page (press and hold for 3 seconds) has a printable Arabic flyer with a QR code, printable day cards for families without a device and a ready WhatsApp message.

Assessors: press **"Assessor tour / جولة للمقيّم"** on the parent home. It unlocks all five days and explains each feature and the requirement it meets.

## Change the content (teachers)

All learning content is in **`app/content.json`**: sounds, words, pictures, the five days, the challenge items, and every Arabic text (`ar` shown in the app, `en` for the English view, `say` = the script used to record the audio).

- New words made from the six existing sounds work at once: the app joins the letter sounds itself, and the device voice says the whole word if there is no recording.
- If you change an Arabic text, the app notices that the recording no longer matches (a text hash) and reads the new text with the device's Arabic voice until the audio is rebuilt.
- New letters need new sound recordings (`tools/make_audio.py`).
- Editing `content.json` on GitHub and committing is enough: the site redeploys by itself (`.github/workflows/pages.yml`).

## Project structure

```
app/                  the published app (plain HTML, CSS and JavaScript modules; no framework, no CDN, no build step)
  index.html  manifest.webmanifest  sw.js  sw-files.js  content.json
  css/app.css  js/*.js  js/screens/*.js  fonts/  icons/  img/  audio/en  audio/ar  audio/manifest.json
tools/                asset scripts (not needed to run the app)
  make_fonts.py       self-hosted fonts (official Andika webfont, Arabic subset of Baloo Bhaijaan 2)
  make_audio.py       all audio: Kokoro (English, IPA input), MMS-TTS (Arabic); trims, normalises, MP3
  audio_analysis.py   acoustic checks for pure phonemes; verify_audio.py runs every audio check + Whisper
  make_icons.py       app icons from the mascot; build_sw_list.py offline cache list; build_offline.py single-file backup
  make_qr.py  screenshots.py  make_pdfs.py  serve.py (local test server)
tests/run_tests.py    Playwright + axe-core quality checks → deliverables/TEST_REPORT.md
```

## Run and test locally

```
python tools/serve.py 8765          # then open http://127.0.0.1:8765/
python tests/run_tests.py           # needs: pip install playwright axe-playwright-python ; playwright install chromium
```

After changing files in `app/`, run `python tools/build_sw_list.py` so phones download the update.

## Credits and licences

See [CREDITS.md](CREDITS.md). Fonts: Andika (SIL, OFL) and Baloo Bhaijaan 2 (OFL). Voices: Kokoro-82M (Apache-2.0) and Meta MMS-TTS Arabic (CC BY-NC 4.0). All pictures are original. Built with AI assistance (Claude Code) under the group's direction. Changes: [CHANGELOG.md](CHANGELOG.md).
