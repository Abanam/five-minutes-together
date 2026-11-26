# Changelog

All notable changes to **5 Minutes Together – خمس دقائق معًا** are recorded here.
Versions follow `MAJOR.MINOR`; the version label shown in the app (Settings, About, home footer) matches the latest entry.
Feedback from reviewers (the in-app checklist) should be added under a new "Unreleased" heading before the next version.

## [1.1] – 2026-11-26

**Why:** four outside reviewers checked v1.0 with the in-app checklist. The one aspect to improve was pronunciation: the English letter sounds and words, and the Arabic voice.

### What changed
- **New voices (ElevenLabs, Multilingual v2, generated once at build time; the app still makes no network requests):**
  - English words and Sanad's phrases: the default British voice "George", chosen by the team after a Whisper check of the five words v1.0 got wrong. "pan" joins the natural /p/ (burst and aspiration) of one try to the vowel and /n/ of another try of the same word, chosen by the team by ear: the tries heard as "pan" had almost no aspiration, and Whisper heard most versions with a clear /p/ as "pun".
  - Arabic instructions: a voice made with ElevenLabs Voice Design ("a warm Omani teacher reading simple Modern Standard Arabic"), one request per text segment with the neighbouring text as context; English sounds and words are still spliced in, so the Arabic voice never says a letter name.
  - Letter sounds: cut to the pure sound from ElevenLabs prompts (Alice for /æ/ /ɪ/ /n/, George for /s/ /t/ /p/) and checked with the unchanged acoustic rules; the vowels and /n/ are natural drawn-out sounds (no looping). The team's own recordings were tried first and were not good enough.
- **A local studio page** (`tools/studio/`, never published) to choose the voices and letter sounds by ear and to record takes.
- **Checks:** every clip passes existence, duration, loudness and clipping; Arabic clips also need 8–20 characters per second and no silence over 1.2 s (three slow segments were made again with a new seed); `verify_audio.py` gained `--audio-dir` so v1.0 could be re-measured with the same, unchanged measures.
- **Reviewer checklist:** the eight items are unchanged; an "Audio re-check (v1.1)" block adds A1–A3, included in "Copy my feedback". Answers are stored per version.
- **One-time update notice** for devices that used v1.0 (never for new users).
- **Voice credits and attribution:** "elevenlabs.io" in the page title and the About credits ("Voices: elevenlabs.io · الأصوات").
- **Header fix:** the title uses the full width; the "Ready offline" badge has its own line; on screens up to 380 px the language button moves next to the badge (checked at 320–430 px, both languages, normal and large text).
- **Version 1.0 stays online** at …/v1.0/ (its own storage, no service worker, not in the v1.1 offline cache, with an archive banner).
- Version 1.1 shown everywhere (read from `content.json`).

### Before and after (measured with the same, unchanged `tools/verify_audio.py`)
| Measure | v1.0 | v1.1 |
|---|---|---|
| English words Whisper heard as intended | 22/27 | 27/27 |
| Letter sounds passing the acoustic checks / letter-name controls rejected | 6/6 / 6/6 | 6/6 / 6/6 |
| /t/ and /p/ (trimmed length) | 0.09 s / 0.12 s | 0.15 s / 0.15 s (natural burst 0.078 / 0.088 s, aspiration continued) |
| Arabic Whisper similarity, mean / median (n = 107) | 0.856 / 0.878 | 0.949 / 0.979 |
| Arabic clips below 0.80 | 22 | 2 |
| Arabic similarity with difflib's autojunk off (supplementary), mean / min | 0.859 / 0.375 | 0.958 / 0.750 |
| Total Arabic duration | 1,248 s | 896 s |
| Total audio / offline cache | 5.86 MB / 6.60 MB | 5.72 MB / 6.46 MB |

Not met: the lowest official v1.1 Arabic score is 0.050 (`about_purpose`), a scoring artefact – Whisper's transcript matches the text (0.975 with autojunk off); `ask_d4_in` scores 0.750 because Whisper writes the held English sounds as Arabic letters. Note on "pan": Whisper heard most versions with a clear /p/ as "pun", so the team chose the clip by ear; Whisper heard it as "pan" in the official run, but its answer for this word changes from run to run. Details: `deliverables/audio-comparison-v1.0-v1.1.md` (local).

## [1.0] – 2026-11-25

First complete, published prototype for EDEN4233 (Technology for Initial Language Literacy).

### Learning content and pedagogy
- Five daily sessions (Days 1–5: s a t · p · i · n · review) with exactly the words in the brief, defined in the editable `app/content.json`.
- The same routine every day: Start → Hear it (اسمع) → Tap and say (انقر وقل) → Blend on your own (ادمج وحدك) → Sanad's challenge (تحدّي سند) → sticker and stop.
- Fading support shown to the parent: Days 1–2 "I say, you repeat" (automatic audio), Days 3–4 "Ask and help" (child taps, question prompts), Day 5 "You can do it" (no automatic audio, hints on request).
- Measurable objectives O1–O3: three auto-checked challenge items each day; Day 5 final check with 6 letter–sound and 10 blend-and-choose items (first-try scoring); parent results page with "met / not met yet" and what to practise again.
- Pure letter sounds generated from IPA phoneme input and verified acoustically; segmented blends with 0.4 s gaps; the brief's Arabic pronunciation tips as text and audio.

### Parents, teachers, reviewers, assessors
- Arabic-first parent area (right-to-left) with an English toggle; sand-coloured parent cards with Arabic text and recorded Arabic audio on every instruction; "Ask your child" cards.
- Three-screen Arabic onboarding with audio; parent home with today's stop, Start, five-day progress and latest results.
- Next day unlocks on the next calendar day; completed days can be repeated; no automatic start of the next day.
- Parent gate (press and hold for 3 seconds) on settings, external links, and the teacher and reviewer pages.
- Trusted free apps (Khan Academy Kids, Duolingo ABC, Read Along by Google), checked as free and ad-free on 25 Nov 2026.
- For teachers: one-minute Arabic guide, printable A4 Arabic flyer with QR code, printable day cards for families without a device, ready WhatsApp message (copy / share).
- Reviewer checklist (8 items, 1–5 scale, comments, "Copy my feedback"; nothing is sent).
- Assessor tour (12 stops in English, each naming the requirement it meets) and "Unlock all days" in settings.

### Design, accessibility and safety
- Original mascot Sanad (baby green sea turtle of Ras Al Jinz) with blink, wave, hop and nod; Omani journey map (beach, palm grove, fort, wadi, sea with a dhow); 23 original pictures; 5 stickers; family scenes showing mothers, fathers and older siblings helping girls and boys.
- Andika (single-storey "a") for English and Baloo Bhaijaan 2 for Arabic, self-hosted.
- Tap targets ≥ 64 px, bouncy press, a sound on every tap, synthesised chime, stars and hop for correct answers; a gentle "Let's listen again" for mistakes (no buzzer, red cross, lives or timers).
- Large-text option, calm mode (also follows the device's reduced-motion setting), WCAG 2.1 AA contrast, colour never used alone.
- No accounts, ads, chat or tracking; localStorage only; strict Content-Security-Policy (no third-party requests).
- Offline PWA (service worker caches the whole app, "Ready offline ✓ / جاهز دون إنترنت"), about 6.6 MB, works on a shared phone; single-file offline backup.

### Quality
- Automated Playwright test suite (five-day play-through, offline, axe-core, RTL, font, images, audio, gate, size, 3G, and checks on the published site) – see `deliverables/TEST_REPORT.md`.
- Audio verification in code (existence, duration, loudness, clipping, phoneme acoustics with letter-name negative controls, clean word onsets, Whisper transcription).

### Fixed before the v1.0 tag (found by the automated checks)
- English word clips no longer start with the speech engine's short "uh" (onset check + Whisper-checked candidates); /t/ now uses espeak-ng phoneme mode because Kokoro's /t/ was too hissy.
- Hidden "Next" buttons could show early; the parent gate timer now uses a monotonic clock.
- Offline caching survives dropped connections on weak data (per-file retries, resumes on the next visit).
- Flyer and day cards each fit exactly one A4 page; blending examples on the cards read left to right.
- Published with GitHub Actions in two jobs (build, deploy) to avoid an intermittent artifact race.
