# Credits and licences – 5 Minutes Together (خمس دقائق معًا) v1.0

All illustrations (the mascot Sanad, the journey map, the 23 keyword and word pictures, the 5 stickers, the family scenes and the icons) are **original inline SVG drawings made for this app**. No photos, emoji artwork, brands, logos or existing characters are used. Sound effects (tap, chime, sticker) are **synthesised in the browser** with the Web Audio API; no recorded sound effects are used.

The app was built with AI assistance (**Claude Code**, Anthropic) under the group's direction.

## Fonts (self-hosted, no CDN)

| Font | Author | Licence | How it is used |
|---|---|---|---|
| **Andika** 7.000 (Medium) | SIL Global | SIL Open Font License 1.1, Reserved Font Names "Andika" and "SIL" | SIL's official WOFF2 webfont from the 7.000 release ([github.com/silnrsi/font-andika](https://github.com/silnrsi/font-andika/releases/tag/v7.000)), **unmodified**, because the OFL-FAQ (2.6) treats subsetting as a modification that cannot keep a Reserved Font Name. Used for every English letter and word (single-storey "a"). Licence: `app/fonts/Andika-OFL.txt`. |
| **Baloo Bhaijaan 2** (variable) | Ek Type / The Baloo 2 Project Authors | SIL Open Font License 1.1 (no Reserved Font Name) | From [google/fonts](https://github.com/google/fonts/tree/main/ofl/baloobhaijaan2), subset to Arabic characters and punctuation with fontTools (allowed by the OFL). Rounded, friendly Arabic interface font. Licence: `app/fonts/BalooBhaijaan2-OFL.txt`. |

## Voices and speech engines (all run locally; no paid API, no account)

| Use | Engine / model | Licence | Notes |
|---|---|---|---|
| English words, keywords, praise and retry phrases | **Kokoro-82M v1.0** (hexgrad), voice **`af_heart`**, run with **kokoro-onnx** 0.6.1 (thewh1teagle) and ONNX Runtime | Kokoro model and voices: **Apache-2.0**; kokoro-onnx: MIT; ONNX Runtime: MIT | Words were generated from hand-written IPA phoneme input (e.g. `sˈæt`). The name "Sanad" is given as IPA `sˈɑnɑd`. |
| The six letter sounds /s/ /æ/ /t/ /p/ /ɪ/ /n/ | **Kokoro-82M v1.0** from IPA phoneme input | Apache-2.0 | Pure phonemes, never letter names: /s/ = the frication cut from Kokoro "ðə sˈʌn" and lengthened with noise grains; /t/ and /p/ = burst + aspiration cut before voicing from "ðə tˈæp" / "ðə pˈʌn"; /æ/ and /ɪ/ = steady vowel frames selected by formants from Kokoro carrier words and sustained; /n/ = Kokoro "nnn". Each passed acoustic checks (`tools/audio_analysis.py`); the espeak-ng phoneme-mode fallback was not needed. |
| Arabic parent instructions, tips, onboarding and guide | **Meta MMS-TTS Arabic** (`facebook/mms-tts-ara`, VITS) via Hugging Face Transformers 4.46.3 and PyTorch | Model: **CC BY-NC 4.0** (non-commercial use with attribution – this is a non-commercial university prototype); Transformers: Apache-2.0; PyTorch: BSD-3 | Synthesised phrase by phrase with real pauses; English sounds and words inside an Arabic text (e.g. "قل (سسس)", "كما في cat") are spliced in from the English clips so the Arabic voice never says a letter name. |
| English text-to-phoneme for the praise phrases | **espeak-ng** (via `espeakng-loader` 0.2.4 and `phonemizer`) | GPL-3.0 (engine); audio output is not covered by the GPL | Only converts text to phonemes for Kokoro. |
| Fallback at run time | The device's own speech synthesis (Web Speech API) | – | Used only if a teacher edits an Arabic text in `content.json` and the recorded clip no longer matches (detected by a text hash), so no button ever plays nothing. |

**Considered and not used:** the Piper Arabic voice `ar_JO-kareem`: its model card points to a training dataset with no licence, so it did not meet the "open-licensed voices" rule.

## Tools used to build and check the app (not shipped in the app)

| Tool | Licence | Purpose |
|---|---|---|
| Python 3.11, NumPy, SciPy, soundfile | PSF, BSD-3 | Audio processing and acoustic checks |
| FFmpeg 7.1 (gyan.dev essentials build) with LAME MP3 encoder | GPL-3 build / LAME LGPL | Mono MP3 encoding and decoding |
| faster-whisper 1.2.1 with OpenAI Whisper "small" | MIT / MIT | Verification only: transcribes every English word clip and Arabic clip |
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
