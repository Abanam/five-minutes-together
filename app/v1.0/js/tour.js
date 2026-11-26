// Assessor tour: unlocks all days and walks through ~12 stops in English,
// each naming the requirement it meets (R1–R5, fading support, safety, offline).

import { h, frag, sleep } from './util.js';
import { icon } from './art.js';
import { app } from './ctx.js';
import { settings } from './store.js';
import { go } from './router.js';
import { btn } from './ui.js';
import * as audio from './audio.js';

const STOPS = [
  { hash: '#/home', sel: '[data-test="today-card"]', tags: ['R1', 'R2'], title: 'Welcome, assessor',
    text: 'This tour (about 3 minutes) has unlocked all five days. The parent home shows today\'s stop with a Start button, five-day progress and the latest results. The parent area is Arabic-first (right-to-left) with an English toggle; every parent instruction has Arabic text and recorded Arabic audio (speaker button) for helpers who read little.' },
  { hash: '#/map', sel: '[data-test="map"]', tags: ['R1', 'Screen time'], title: 'Journey map',
    text: 'Five Omani stops: beach (the turtles of Ras Al Jinz), palm grove, fort, wadi, and the sea with a dhow. One stop per day: the next day unlocks on the next calendar day, so screen time stays at one 5-minute session. Finished stops light up with a star and a tick, never colour alone.' },
  { hash: '#/day/1?step=start&demo=1', sel: '.pc-wrap', tags: ['R1', 'R2', 'Fading support'], title: 'Start: Sanad and the parent card',
    text: 'Sanad, an original baby green sea turtle, greets the child and shows today\'s sounds. The sand-coloured parent card (parent icon, Arabic text, speaker button) gives one Arabic tip and shows the current support level.' },
  { hash: '#/day/1?step=hear&demo=1', sel: '[data-test="letter-card"]', tags: ['Pedagogy', 'R2'], title: 'Hear it: correct sound models',
    text: 'Tapping the letter plays the pure sound (/s/, not "ess"). All six sounds were generated from IPA phoneme input and checked acoustically, so the app models sounds a parent may not be able to produce, such as /p/, which Arabic lacks. Next come two keyword pictures ("s… sun") and "Find the sound" with instant feedback.' },
  { hash: '#/day/2?step=tapsay&demo=1', sel: '.tiles', tags: ['R1', 'Explicit phonics'], title: 'Tap and say: the sound train',
    text: 'Each letter tile plays its sound (each letter keeps one colour everywhere and always shows the letter). The sound-train button slides the tiles together, plays the whole word and reveals its picture. An Arabic "Ask your child" card with audio follows.' },
  { hash: '#/day/3?step=blend&demo=1', sel: '.judge', tags: ['R1', 'R2', 'Feedback'], title: 'Blend on your own',
    text: 'The child reads the tiles alone; the parent taps "قالها صح ✓" or "نحاول مرة ثانية ↺". A hint replays the separate sounds. Mistakes get a gentle "Let\'s listen again": no buzzer, no red cross, no lives, no timers.' },
  { hash: '#/day/5?step=start&demo=1', sel: '.pc-wrap', tags: ['Fading support (ZPD)'], title: 'Support fades across the week',
    text: 'Vygotsky\'s zone of proximal development, with the parent as the more knowledgeable other: Days 1–2 "I say, you repeat" (sounds play automatically); Days 3–4 "Ask and help" (the child taps; prompts are questions); Day 5 "You can do it" (no automatic audio; hints only on request).' },
  { hash: '#/day/5?step=challenge&demo=1', sel: '.stage', tags: ['O1', 'O2'], title: "Sanad's challenge and the final check",
    text: 'Every day ends with 3 auto-checked items (letter–sound, or blend and choose the picture). On Day 5 the final check has 6 letter–sound items (O1) and 10 blend-and-choose items (O2), scored on the first try.' },
  { hash: '#/results', sel: '[data-test="objectives"]', tags: ['O1', 'O2', 'O3'], title: 'Results for the parent',
    text: 'Completion and challenge scores for each day. After Day 5 it states whether O1 (at least 5 of 6 sounds) and O2 (at least 8 of 10 words) are met; O3 counts sessions completed with the Arabic guidance. It lists the sounds to practise again and the day to repeat.' },
  { hash: '#/apps', sel: '[data-test="apps"]', tags: ['R3', 'Safety'], title: 'Trusted free apps',
    text: 'A short list checked on official websites as free and ad-free, each with two Arabic lines and an "Ask your child" tip. External links open only after the parent gate (press and hold for 3 seconds).' },
  { hash: '#/teachers', sel: '[data-test="flyer-preview"]', tags: ['R5', 'R4'], title: 'For teachers',
    text: 'A one-minute Arabic guide, a printable A4 Arabic flyer with the QR code, printable day cards for families without a device, and a ready WhatsApp message (copy or share). Letters and words can be changed in content.json. Normally behind the parent gate.' },
  { hash: '#/about', sel: '[data-test="privacy"]', tags: ['Safety', 'R4', 'Testing'], title: 'Safe, private and offline',
    text: 'No accounts, ads, chat or tracking: nothing leaves the device (localStorage only). A service worker caches the whole small app, shown as "Ready offline ✓". Calm mode, large text and a reviewer checklist (v1.0) are in the parent area. End of the tour: all days stay unlocked.' },
];

let active = null;

export function startTour() {
  if (active) return;
  app.tour = true;
  settings.set({ unlockAll: true, onboarded: true });
  const layer = h('div.tour-layer', { role: 'dialog', 'aria-modal': 'true', 'aria-label': 'Assessor tour', 'data-test': 'tour', lang: 'en', dir: 'ltr' });
  const blocker = h('div.tour-block');
  const spot = h('div.tour-spot', { 'aria-hidden': 'true' });
  const card = h('div.tour-card', { 'data-test': 'tour-card' });
  layer.append(blocker, spot, card);
  document.body.append(layer);
  active = { layer, i: 0 };

  const onKey = (e) => {
    if (e.key === 'Escape') end();
    else if (e.key === 'ArrowRight') step(active.i + 1);
    else if (e.key === 'ArrowLeft') step(active.i - 1);
  };
  document.addEventListener('keydown', onKey);

  function end() {
    document.removeEventListener('keydown', onKey);
    layer.remove();
    active = null;
    app.tour = false;
    audio.stopSpeech();
    go('#/home');
  }

  async function step(k) {
    if (k < 0 || k >= STOPS.length) { if (k >= STOPS.length) end(); return; }
    active.i = k;
    const s = STOPS[k];
    if (location.hash !== s.hash) go(s.hash);
    let el = null;
    for (let n = 0; n < 50 && !el; n++) { await sleep(80); el = document.querySelector(s.sel); }
    audio.stopSpeech();
    if (el) {
      el.scrollIntoView({ block: 'center' });
      await sleep(200);
      const r = el.getBoundingClientRect();
      Object.assign(spot.style, { display: 'block', left: r.left - 6 + 'px', top: r.top - 6 + 'px', width: r.width + 12 + 'px', height: r.height + 12 + 'px' });
      const below = r.top + r.height / 2 < window.innerHeight / 2;
      card.style.top = below ? '' : '12px';
      card.style.bottom = below ? '12px' : '';
    } else {
      spot.style.display = 'none';
      card.style.top = ''; card.style.bottom = '12px';
    }
    card.innerHTML = '';
    const prev = btn('Back', { icon: 'back', cls: 'btn-ghost', test: 'tour-back', onClick: () => step(k - 1) });
    prev.disabled = k === 0;
    const last = k === STOPS.length - 1;
    const next = btn(last ? 'Finish' : 'Next', { icon: last ? 'check' : 'next', iconAfter: true, cls: 'btn-primary', test: 'tour-next', onClick: () => step(k + 1) });
    card.append(
      h('div', s.tags.map((x) => h('span.req', x))),
      h('h2', s.title),
      h('p', s.text),
      h('div.tour-nav', prev, h('span.tour-count', `${k + 1} / ${STOPS.length}`), next),
      h('div.center', btn('Close tour', { icon: 'close', cls: 'btn-ghost btn-small-text', test: 'tour-close', onClick: end })),
    );
    next.focus();
  }
  step(0);
}

export const tourStops = STOPS.length;
