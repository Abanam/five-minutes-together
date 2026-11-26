// Web Audio engine: MP3 clips (decoded once, cached), synthesised sound effects,
// iOS unlock on first tap, and an Arabic/English speech-synthesis fallback so that
// no button ever plays nothing.

import { fnv1a, FAST } from './util.js';

let ctx = null;
let master = null, speechBus = null, sfxBus = null;
let manifest = { en: {}, ar: {} };
let content = null;
let sfxOn = true;
const cache = new Map(); // url -> Promise<AudioBuffer|null>
let speechToken = 0;
let current = [];
const listeners = new Set();
export const stats = { played: 0, failed: [], fallbacks: 0 };

function makeContext() {
  if (ctx) return ctx;
  const AC = window.AudioContext || window.webkitAudioContext;
  if (!AC) return null;
  try { ctx = new AC(); } catch (e) { return null; }
  master = ctx.createGain(); master.gain.value = 1; master.connect(ctx.destination);
  speechBus = ctx.createGain(); speechBus.gain.value = 1; speechBus.connect(master);
  sfxBus = ctx.createGain(); sfxBus.gain.value = 0.45; sfxBus.connect(master);
  return ctx;
}

export function initAudio(opts) {
  manifest = opts.manifest || manifest;
  content = opts.content;
  makeContext();
  const unlockOnce = () => { unlock(); };
  ['pointerdown', 'touchend', 'keydown', 'click'].forEach((ev) => document.addEventListener(ev, unlockOnce, { capture: true, passive: true }));
}

/** Must run inside a user gesture at least once (iOS Safari). */
export function unlock() {
  const c = makeContext();
  if (!c) return;
  if (c.state === 'suspended' && c.resume) c.resume();
  try {
    const b = c.createBuffer(1, 1, 22050);
    const s = c.createBufferSource(); s.buffer = b; s.connect(c.destination); s.start(0);
  } catch (e) { /* ignore */ }
}

export function setSfx(on) { sfxOn = !!on; }
export function onSpeaking(fn) { listeners.add(fn); return () => listeners.delete(fn); }
function emit(state) { listeners.forEach((fn) => { try { fn(state); } catch (e) { /* ignore */ } }); }

// ------------------------------------------------------------------ loading
function base64ToBuffer(b64) {
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out.buffer;
}

function fetchBytes(url) {
  const emb = window.__FMT_EMBED__ && window.__FMT_EMBED__.audio;
  if (emb) {
    if (emb[url]) return Promise.resolve(base64ToBuffer(emb[url]));
    return Promise.reject(new Error('missing ' + url));
  }
  return fetch(url).then((r) => (r.ok ? r.arrayBuffer() : Promise.reject(new Error(r.status + ' ' + url))));
}

function decode(ab) {
  return new Promise((resolve, reject) => {
    try {
      const p = ctx.decodeAudioData(ab, resolve, reject);
      if (p && p.then) p.then(resolve, reject);
    } catch (e) { reject(e); }
  });
}

export function load(url) {
  if (!makeContext()) return Promise.resolve(null);
  if (!cache.has(url)) {
    cache.set(url, fetchBytes(url).then(decode).catch((e) => {
      stats.failed.push(url + ': ' + (e && e.message));
      return null;
    }));
  }
  return cache.get(url);
}
export function preload(urls) { urls.forEach((u) => load(u)); }

// ------------------------------------------------------------------ paths
export const url = {
  ph: (l) => `audio/en/ph-${l}.mp3`,
  word: (w) => `audio/en/w-${w}.mp3`,
  blend: (w) => `audio/en/b-${w}.mp3`,
  en: (k) => `audio/en/x-${k}.mp3`,
  ar: (id) => `audio/ar/${id}.mp3`,
};
export const has = {
  ph: (l) => !!manifest.en['ph-' + l],
  word: (w) => !!manifest.en['w-' + w],
  blend: (w) => !!manifest.en['b-' + w],
  en: (k) => !!manifest.en['x-' + k],
  /** Arabic clip exists AND still matches the text in content.json (teachers may edit it). */
  ar: (id, text) => !!(manifest.ar[id] && (!text || manifest.ar[id].h === fnv1a(text))),
};

// ------------------------------------------------------------------ playback
function playBuffer(buf, bus) {
  return new Promise((resolve) => {
    let done = false;
    const finish = () => { if (!done) { done = true; resolve(); } };
    try {
      const src = ctx.createBufferSource();
      src.buffer = buf;
      src.connect(bus || speechBus);
      src.onended = finish;
      src.start(0);
      current.push(src);
      stats.played++;
      // safety net if onended never fires (suspended context, background tab)
      setTimeout(finish, FAST ? 60 : buf.duration * 1000 + 250);
    } catch (e) { finish(); }
  });
}

export function stopSpeech() {
  speechToken++;
  current.forEach((s) => { try { s.stop(0); } catch (e) { /* already stopped */ } });
  current = [];
  try { if (window.speechSynthesis) window.speechSynthesis.cancel(); } catch (e) { /* ignore */ }
  emit(false);
}

function pickVoice(langPrefix) {
  try {
    const vs = window.speechSynthesis.getVoices() || [];
    return vs.find((v) => v.lang && v.lang.toLowerCase().indexOf(langPrefix) === 0) || null;
  } catch (e) { return null; }
}

/** Device speech synthesis (used only when a recorded clip is missing or outdated). */
export function speakTTS(text, lang) {
  stats.fallbacks++;
  return new Promise((resolve) => {
    if (!('speechSynthesis' in window) || !text) { chimeSoft(); resolve(false); return; }
    try {
      const u = new SpeechSynthesisUtterance(text.replace(/\{(ph|w):([a-z]+)\}/g, '$2'));
      u.lang = lang === 'ar' ? 'ar-SA' : 'en-GB';
      const v = pickVoice(lang === 'ar' ? 'ar' : 'en');
      if (v) u.voice = v;
      else if (lang === 'ar') { chimeSoft(); }
      u.rate = 0.9;
      let done = false;
      const fin = (ok) => { if (!done) { done = true; resolve(ok); } };
      u.onend = () => fin(true);
      u.onerror = () => fin(false);
      window.speechSynthesis.cancel();
      window.speechSynthesis.speak(u);
      setTimeout(() => fin(true), FAST ? 60 : 1500 + text.length * 90);
    } catch (e) { chimeSoft(); resolve(false); }
  });
}

/**
 * Play a speech sequence. items: [{url} | {gap: seconds} | {tts, lang}]
 * Starting a new sequence stops the previous one. Resolves when finished (or stopped).
 */
export async function say(items) {
  stopSpeech();
  const my = ++speechToken;
  if (!makeContext()) {
    const t = items.find((i) => i.tts);
    if (t) await speakTTS(t.tts, t.lang);
    return;
  }
  if (ctx.state === 'suspended' && ctx.resume) { try { await ctx.resume(); } catch (e) { /* ignore */ } }
  emit(true);
  for (const it of items) {
    if (my !== speechToken) return;
    if (it.gap) { await new Promise((r) => setTimeout(r, FAST ? 10 : it.gap * 1000)); continue; }
    if (it.url) {
      const buf = await load(it.url);
      if (my !== speechToken) return;
      if (buf) { await playBuffer(buf, speechBus); continue; }
      if (it.tts) { await speakTTS(it.tts, it.lang); continue; }
      chimeSoft();
      continue;
    }
    if (it.tts) await speakTTS(it.tts, it.lang);
  }
  if (my === speechToken) emit(false);
}

// convenience wrappers ------------------------------------------------
export function phoneme(l) { return say([{ url: url.ph(l) }]); }

export function word(w) {
  return say([has.word(w) || !content ? { url: url.word(w), tts: w, lang: 'en' } : { tts: w, lang: 'en' }]);
}

/** "s … sun": first sound, then the keyword. */
export function keyword(w, l) {
  return say([{ url: url.ph(l) }, { gap: 0.35 }, { url: url.word(w), tts: w, lang: 'en' }]);
}

/** Segmented blend p … a … n (pre-built clip, or joined at run time for teacher-made words). */
export function blendItems(w, sounds) {
  if (has.blend(w)) return [{ url: url.blend(w) }];
  const items = [];
  sounds.forEach((s, i) => { if (i) items.push({ gap: 0.4 }); items.push({ url: url.ph(s) }); });
  return items;
}
export function blend(w, sounds) { return say(blendItems(w, sounds)); }

export function english(key) {
  const text = content && content.english[key];
  return say([{ url: url.en(key), tts: text, lang: 'en' }]);
}

/** Arabic parent text by id (recorded clip if it matches the current text, else device voice). */
export function arabic(id, text) {
  if (has.ar(id, text)) return say([{ url: url.ar(id), tts: text, lang: 'ar' }]);
  return say([{ tts: text, lang: 'ar' }]);
}

// ------------------------------------------------------------------ synthesised effects (no recorded SFX)
function tone(freq, start, dur, type, gain, endFreq) {
  const o = ctx.createOscillator();
  const g = ctx.createGain();
  o.type = type || 'sine';
  o.frequency.setValueAtTime(freq, start);
  if (endFreq) o.frequency.exponentialRampToValueAtTime(endFreq, start + dur);
  g.gain.setValueAtTime(0.0001, start);
  g.gain.exponentialRampToValueAtTime(gain, start + 0.012);
  g.gain.exponentialRampToValueAtTime(0.0001, start + dur);
  o.connect(g); g.connect(sfxBus);
  o.start(start); o.stop(start + dur + 0.02);
}
function ready() { return sfxOn && makeContext() && ctx.state !== 'closed'; }

export function sfx(name) {
  if (!ready()) return;
  if (ctx.state === 'suspended' && ctx.resume) ctx.resume();
  const t = ctx.currentTime + 0.005;
  if (name === 'tap') tone(660, t, 0.08, 'sine', 0.18, 360);
  else if (name === 'chime') { tone(1046.5, t, 0.35, 'sine', 0.22); tone(1318.5, t + 0.07, 0.35, 'sine', 0.2); tone(1568, t + 0.14, 0.5, 'triangle', 0.18); }
  else if (name === 'sticker') { [523.3, 659.3, 784, 1046.5, 1318.5].forEach((f, i) => tone(f, t + i * 0.09, 0.45, 'triangle', 0.18)); }
  else if (name === 'soft') { tone(392, t, 0.22, 'sine', 0.12); tone(330, t + 0.16, 0.3, 'sine', 0.1); }
  else if (name === 'whoosh') tone(240, t, 0.5, 'triangle', 0.08, 720);
}
export function chimeSoft() { sfx('soft'); }
