// 5 Minutes Together – خمس دقائق معًا · v1.0
// Boot: load content.json + audio manifest, apply settings, register routes and the service worker.

import { $$ } from './util.js';
import { app } from './ctx.js';
import { settings } from './store.js';
import { initLang } from './i18n.js';
import * as audio from './audio.js';
import { route, startRouter } from './router.js';
import { homeScreen, onboardingScreen, resultsScreen, stickersScreen, tipsScreen, howtoScreen, aboutScreen } from './screens/parent.js';
import { mapScreen } from './screens/map.js';
import { sessionScreen, dayAudioUrls } from './screens/session.js';
import { appsScreen, teachersScreen, flyerScreen, cardsScreen, reviewScreen, settingsScreen } from './screens/teacher.js';

function loadJSON(url, key) {
  const emb = window.__FMT_EMBED__;
  if (emb && emb[key]) return Promise.resolve(emb[key]);
  return fetch(url).then((r) => (r.ok ? r.json() : Promise.reject(new Error(url + ' ' + r.status))));
}

function applySettings() {
  const s = settings.get();
  const root = document.documentElement;
  root.classList.toggle('large', !!s.large);
  const reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  root.classList.toggle('calm', s.calm === null ? reduce : !!s.calm);
  if (/[?&]fast=1/.test(location.search)) root.classList.add('fast');
  audio.setSfx(s.sfx);
}

function setOfflineReady() {
  app.offlineReady = true;
  $$('.offline-badge').forEach((b) => { b.hidden = false; });
}

function registerServiceWorker() {
  // archived v1.0: no service worker (v1.0's sw.js would delete the v1.1 cache)
}

async function boot() {
  const root = document.getElementById('app');
  try {
    const [content, manifest] = await Promise.all([
      loadJSON('content.json', 'content'),
      loadJSON('audio/manifest.json', 'manifest').catch(() => ({ en: {}, ar: {} })),
    ]);
    app.content = content;
    app.manifest = manifest;
  } catch (e) {
    root.innerHTML = '<p style="padding:24px;font-size:18px">تعذّر تحميل المحتوى. افتح الرابط مرة أخرى عند توفر الإنترنت.<br><span lang="en" dir="ltr">The content could not be loaded. Please open the link again when you are online.</span></p>';
    return;
  }
  initLang();
  applySettings();
  audio.initAudio({ manifest: app.manifest, content: app.content });

  // a soft sound on every tap (and keyboard press) of a button
  document.addEventListener('pointerdown', (e) => {
    const b = e.target.closest && e.target.closest('button');
    if (b && !b.disabled && !b.classList.contains('hold-btn')) audio.sfx('tap');
  }, true);
  document.addEventListener('keydown', (e) => {
    if ((e.key === 'Enter' || e.key === ' ') && e.target.tagName === 'BUTTON' && !e.repeat && !e.target.classList.contains('hold-btn')) audio.sfx('tap');
  }, true);

  route('home', homeScreen);
  route('onboarding', onboardingScreen);
  route('map', mapScreen);
  route('day', sessionScreen);
  route('results', resultsScreen);
  route('stickers', stickersScreen);
  route('tips', tipsScreen);
  route('howto', howtoScreen);
  route('about', aboutScreen);
  route('apps', appsScreen);
  route('teachers', teachersScreen, { gated: true });
  route('flyer', flyerScreen, { gated: true });
  route('cards', cardsScreen, { gated: true });
  route('review', reviewScreen, { gated: true });
  route('settings', settingsScreen, { gated: true });
  startRouter(root);

  // after the first screen is up, warm the small Day 1 English clips so the session starts instantly
  setTimeout(() => audio.preload(dayAudioUrls(app.content.days[0]).filter((u) => u.indexOf('/en/') > 0)), 900);
  registerServiceWorker();
  window.FMT = { version: app.content.meta.version, app, audio: audio.stats };
}

boot();
