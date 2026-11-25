# Changelog

All notable changes to **5 Minutes Together – خمس دقائق معًا** are recorded here.
Versions follow `MAJOR.MINOR`; the version label shown in the app (Settings, About, home footer) matches the latest entry.
Feedback from reviewers (the in-app checklist) should be added under a new "Unreleased" heading before the next version.

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
