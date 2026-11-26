# Credits and licences – 5 Minutes Together (خمس دقائق معًا) v1.1

All illustrations (the mascot Sanad, the journey map, the 23 keyword and word pictures, the 5 stickers, the family scenes and the icons) are **original inline SVG drawings made for this app**. No photos, emoji artwork, brands, logos or existing characters are used. Sound effects (tap, chime, sticker) are **synthesised in the browser** with the Web Audio API; no recorded sound effects are used.

The app was built with AI assistance (**Claude Code**, Anthropic) under the group's direction. The v1.1 voices are AI-generated with **ElevenLabs** (see below).

## Fonts (self-hosted, no CDN)

| Font | Author | Licence | How it is used |
|---|---|---|---|
| **Andika** 7.000 (Medium) | SIL Global | SIL Open Font License 1.1, Reserved Font Names "Andika" and "SIL" | SIL's official WOFF2 webfont from the 7.000 release ([github.com/silnrsi/font-andika](https://github.com/silnrsi/font-andika/releases/tag/v7.000)), **unmodified**, because the OFL-FAQ (2.6) treats subsetting as a modification that cannot keep a Reserved Font Name. Used for every English letter and word (single-storey "a"). Licence: `app/fonts/Andika-OFL.txt`. |
| **Baloo Bhaijaan 2** (variable) | Ek Type / The Baloo 2 Project Authors | SIL Open Font License 1.1 (no Reserved Font Name) | From [google/fonts](https://github.com/google/fonts/tree/main/ofl/baloobhaijaan2), subset to Arabic characters and punctuation with fontTools (allowed by the OFL). Rounded, friendly Arabic interface font. Licence: `app/fonts/BalooBhaijaan2-OFL.txt`. |

## Voices (version 1.1) – voices: elevenlabs.io

All v1.1 audio was generated **once, on the developer's computer, at build time** with the ElevenLabs API (free plan, model
**Multilingual v2**, `eleven_multilingual_v2`). The app itself never contacts ElevenLabs: it plays the MP3 files it ships with.
**ElevenLabs free plan: non-commercial use with attribution** – this is a non-commercial university prototype, and
"elevenlabs.io" is shown in the page title and in the About screen's credits heading ("Voices: elevenlabs.io · الأصوات").

| Use | Voice | Notes |
|---|---|---|
| English words (27), keywords and Sanad's 14 phrases | ElevenLabs default voice **George** (British, male) | Chosen by the team from three default British voices after a Whisper check of the five words v1.0 got wrong (George 5/5). Each word was sent as "word." and checked for a clean onset and with Whisper. |
| Arabic parent instructions, tips, onboarding and guide (107 clips) | **"Five Minutes Together – Omani teacher (Arabic)"**, a voice made with ElevenLabs **Voice Design** on the website from the team's description (a warm Omani teacher reading simple Modern Standard Arabic) | One request per text segment, with the neighbouring text as context; English sounds and words inside an Arabic text are spliced in from the English clips, so the Arabic voice never says a letter name. Harakat were stripped (shadda kept). |
| The six letter sounds /s/ /æ/ /t/ /p/ /ɪ/ /n/ | ElevenLabs default voices **Alice** (/æ/, /ɪ/, /n/) and **George** (/s/, /t/, /p/) | Pure sounds, never letter names: each was cut from a short prompt ("Haaaaand.", "Hiiiiiss.", "Nnnnnnnnnnn…", "Sssssun.", "Too.", "Pea.") – the vowels and /n/ are natural drawn-out sounds (no looping); /s/, /t/ and /p/ were lengthened with grains of their own noise – then checked with the unchanged acoustic rules in `tools/audio_analysis.py` (before and after MP3 encoding). The team's own recordings were tried first but were not good enough. The blends are built from these sounds. |
| Fallback at run time | The device's own speech synthesis (Web Speech API) | Used only if a teacher edits an Arabic text in `content.json` and the recorded clip no longer matches (detected by a text hash), so no button ever plays nothing. |

### Used in version 1.0 (no longer shipped in v1.1)

Version 1.0 (archived at …/v1.0/) used only local, open-licensed engines:
- **Kokoro-82M v1.0** (hexgrad, Apache-2.0), voice `af_heart`, run with kokoro-onnx 0.6.1 (MIT) and ONNX Runtime (MIT): English words, phrases and five letter sounds from IPA phoneme input. Kokoro is still used at build time in v1.1, only to make the letter-*name* negative controls that the letter-sound check must reject.
- **espeak-ng** phoneme mode (GPL-3.0 engine; the audio output is not covered by the GPL): the v1.0 /t/, and text-to-phoneme conversion for Kokoro.
- **Meta MMS-TTS Arabic** (`facebook/mms-tts-ara`, CC BY-NC 4.0) via Hugging Face Transformers 4.46.3 and PyTorch: the Arabic instructions.
- Considered and not used: the Piper Arabic voice `ar_JO-kareem` (its training dataset has no licence).

## Tools used to build and check the app (not shipped in the app)

| Tool | Licence | Purpose |
|---|---|---|
| Python 3.11, NumPy, SciPy, soundfile | PSF, BSD-3 | Audio processing and acoustic checks |
| FFmpeg 7.1 (gyan.dev essentials build) with LAME MP3 encoder | GPL-3 build / LAME LGPL | Mono MP3 encoding and decoding |
| faster-whisper 1.2.1 with OpenAI Whisper "small" | MIT / MIT | Verification only: transcribes every English word clip and Arabic clip |
| ElevenLabs API (free plan), Multilingual v2 | ElevenLabs terms (free plan: non-commercial, attribution) | v1.1 voices, generated once at build time (`tools/eleven.py`, `tools/make_audio_v11.py`, `tools/letters_v11.py`); the API key stays in a local, git-ignored `.env` |
| Local studio page (`tools/studio/`, Python standard library) | – | Choosing the voices and the letter sounds (local only, never published) |
| Matplotlib 3.9.2 | PSF-based (Matplotlib licence) | Report figures comparing v1.0 and v1.1 |
| fontTools 4.68 + Brotli | MIT | Arabic font subsetting to WOFF2 |
| segno 1.6.6 | BSD-3-Clause | QR code |
| Playwright 1.65 (Chromium) | Apache-2.0 | Automated tests, screenshots, PDF printing, icon rendering |
| axe-core 4.14.0 (via axe-playwright-python 0.1.9) | MPL-2.0 / MIT | Accessibility scan |
| MinGit 2.56.1, GitHub CLI 2.105.0 | GPL-2.0 / MIT | Publishing to GitHub Pages |

## Trusted free apps – checked on official websites on 25 November 2026

Only apps that could be confirmed as **free and ad-free** on their official websites are listed in the app.

| App | Official page checked | Evidence found (25 Nov 2026) |
|---|---|---|
| **Khan Academy Kids** | https://www.khanacademy.org/kids | "100% free - forever. No ads, no subscriptions" (a separate paid plan exists only for schools). |
| **Duolingo ABC** | https://abc.duolingo.com/ and https://www.duolingo.com/abc-privacy | Home page: "100% free"; Duolingo ABC privacy policy: "Duolingo ABC does not display advertising of any kind". |
| **Read Along by Google** | https://readalong.google/ and its official Google Play listing | Official FAQ: "available free of charge as a mobile app and web experience", works offline, supports several users on a shared phone; Google's Play listing: "Zero cost with no ads or upsells … no in-app purchases". |

Checked and **not included**: British Council LearnEnglish Kids (free, but its cookie notice mentions tracking used to tailor advertisements, so "ad-free" could not be confirmed); Teach Your Monster to Read (free only on computers and needs an account; the persona's family shares one phone); StoryWeaver (its page did not render readable text in the checking browser, so it could not be confirmed).
