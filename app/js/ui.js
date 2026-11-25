// Reusable UI pieces: buttons, parent card, letter tiles, pictures, Sanad, feedback effects.

import { h, frag, sleep, FAST } from './util.js';
import { icon, picture, sanad as sanadSvg, parentBadge } from './art.js';
import { t, getLang } from './i18n.js';
import { app, T } from './ctx.js';
import * as audio from './audio.js';

export function btn(label, opts = {}) {
  const b = h('button.btn', { type: 'button', class: opts.cls || '', 'aria-label': opts.aria || null, 'data-test': opts.test || null });
  if (opts.icon && opts.iconAfter) b.append(h('span', label), frag(icon(opts.icon, opts.iconCls || '')));
  else if (opts.icon) {
    b.append(frag(icon(opts.icon, opts.iconCls || '')));
    if (label) b.append(h('span', label));
  } else b.append(h('span', label));
  if (opts.onClick) b.addEventListener('click', opts.onClick);
  return b;
}

export function iconBtn(name, aria, onClick, cls = '') {
  return btn('', { icon: name, aria, onClick, cls: 'btn-round ' + cls });
}

/** English text inside Arabic: always an isolated LTR span in Andika. */
export function en(text) {
  return h('bdi.en', { lang: 'en', dir: 'ltr' }, text);
}

/** Render content text, turning Latin words into isolated LTR spans. */
export function richText(str) {
  str = String(str);
  if (!/[؀-ۿ]/.test(str)) return [document.createTextNode(str)];
  const out = [];
  str.split(/([A-Za-z][A-Za-z0-9]*(?:\.[A-Za-z0-9]+)*(?:[ /][A-Za-z][A-Za-z0-9]*(?:\.[A-Za-z0-9]+)*)*)/).forEach((part, i) => {
    if (!part) return;
    if (i % 2 === 1) out.push(en(part));
    else out.push(document.createTextNode(part));
  });
  return out;
}

export function levelBadge(level) {
  const lv = app.content.levels[level];
  const meter = h('span.level-meter', { 'aria-hidden': 'true' }, [1, 2, 3].map((n) => h('i', { class: n <= level ? 'on' : '' })));
  return h('span.level-badge', { 'data-test': 'level-badge', title: t('level') }, meter, txt(lv.name), h('span.sr-only', ` (${t('level')} ${level}/3)`));
}

/** Text of a content entry in the parent language. */
export function txt(id) {
  const x = T(id);
  return getLang() === 'en' ? (x.en || x.ar) : x.ar;
}

/**
 * Sand-coloured parent card: small parent icon, Arabic text (English view also shows the Arabic),
 * and a speaker button that plays the Arabic audio.
 */
export function parentCard(id, opts = {}) {
  const x = opts.textOverride || T(id);
  const isEn = getLang() === 'en';
  const textEl = h('div.pc-text', { lang: isEn ? 'en' : 'ar', dir: isEn ? 'ltr' : 'rtl' }, richText(isEn ? x.en : x.ar));
  if (isEn && opts.showArabic !== false) textEl.append(h('span.pc-sub', { lang: 'ar', dir: 'rtl' }, x.ar));
  const card = h('aside.parent-card', { class: opts.cls || '', 'data-test': opts.test || 'parent-card', 'data-text': id, 'aria-label': t('forParent') });
  const say = btn('', {
    icon: 'speaker', cls: 'btn-say', aria: t('listenAr'), test: 'say-' + id,
    onClick: async () => {
      card.classList.add('speaking');
      await audio.arabic(id, x.ar);
      card.classList.remove('speaking');
    },
  });
  card.append(h('div.pc-label', frag(parentBadge()), h('span', opts.label || t('forParent')), opts.badge || null), textEl, say);
  if (opts.extra) card.append(h('div.pc-extra', opts.extra));
  return card;
}

export function letterTile(letter, opts = {}) {
  const b = h('button.tile', {
    type: 'button', class: `L-${letter} ${opts.size || ''}`, 'data-letter': letter, 'data-test': opts.test || 'tile',
    'aria-label': opts.aria || t('tapLetter', { x: letter }), lang: 'en',
  }, letter);
  if (opts.wheels) b.append(h('span.wheels', { 'aria-hidden': 'true' }, h('i'), h('i')));
  if (opts.onTap) b.addEventListener('click', () => opts.onTap(b));
  return b;
}

/** A static (non-button) letter: used in print and small labels. */
export function letterChip(letter) {
  return h('span.letter-chip', { class: `L-${letter}`, lang: 'en' }, letter);
}

export function pictureBtn(id, word, opts = {}) {
  const b = h('button.pic-btn', {
    type: 'button', 'data-word': word, 'data-test': opts.test || 'pic', 'aria-label': opts.aria || word, lang: 'en',
    class: opts.cls || '',
  });
  b.innerHTML = picture(id);
  if (opts.caption) b.append(h('span.cap', { 'aria-hidden': 'true' }, word));
  if (opts.onTap) b.addEventListener('click', () => opts.onTap(b));
  return b;
}

export function markRight(el) {
  el.classList.add('is-right');
  if (!el.querySelector('.mark')) el.append(h('span.mark', { 'aria-hidden': 'true' }, frag(icon('check'))));
}

// ------------------------------------------------------------------ Sanad
export function sanadEl(size = '', opts = {}) {
  const wrap = h('div.sanad', { class: size + (opts.idle === false ? '' : ' idle'), role: 'img', 'aria-label': 'Sanad / سند' });
  wrap.innerHTML = sanadSvg({ eyes: opts.eyes || 'open', mouth: opts.mouth || 'smile', anim: true });
  return wrap;
}
function replay(el, cls, ms) {
  if (!el) return;
  el.classList.remove(cls);
  void el.offsetWidth;
  el.classList.add(cls);
  setTimeout(() => el.classList.remove(cls), ms);
}
export const sanadDo = {
  hop: (el) => replay(el, 'hop', 700),
  nod: (el) => replay(el, 'nod', 900),
  wave: (el) => replay(el, 'wave', 1500),
};

// ------------------------------------------------------------------ feedback
export function burst(target) {
  if (document.documentElement.classList.contains('calm') || FAST) return;
  const r = target.getBoundingClientRect();
  const b = h('div.burst', { 'aria-hidden': 'true', style: { left: r.left + r.width / 2 + 'px', top: r.top + r.height / 2 + 'px' } });
  for (let i = 0; i < 10; i++) {
    const a = (i / 10) * Math.PI * 2;
    const d = 70 + (i % 3) * 22;
    const s = frag(icon('starFill'));
    s.style.setProperty('--dx', Math.cos(a) * d + 'px');
    s.style.setProperty('--dy', Math.sin(a) * d + 'px');
    s.style.animationDelay = (i % 3) * 40 + 'ms';
    b.append(s);
  }
  document.body.append(b);
  setTimeout(() => b.remove(), 1100);
}

/** Correct: short synthesised chime, Sanad hops, stars burst. */
export function celebrate(target, sanadNode) {
  audio.sfx('chime');
  if (sanadNode) sanadDo.hop(sanadNode);
  if (target) burst(target);
}

/** Wrong: gentle "Let's listen again" — no buzzer, no red cross, no lost lives. */
export async function gentleRetry(target, sanadNode) {
  audio.sfx('soft');
  if (target) { target.classList.remove('wiggle'); void target.offsetWidth; target.classList.add('wiggle'); }
  if (sanadNode) sanadDo.nod(sanadNode);
  await audio.english('again');
}

export function toast(msg, ms = 2600) {
  const el = h('div.toast', { role: 'status' }, msg);
  document.body.append(el);
  setTimeout(() => el.remove(), ms);
}

/** Accessible modal; resolves with the value passed to close(). */
export function modal(build, opts = {}) {
  return new Promise((resolve) => {
    const prev = document.activeElement;
    const back = h('div.modal-back', { 'data-test': opts.test || 'modal' });
    const box = h('div.modal', { role: 'dialog', 'aria-modal': 'true', 'aria-label': opts.label || '' });
    back.append(box);
    const close = (v) => {
      back.remove();
      document.removeEventListener('keydown', onKey, true);
      if (prev && prev.focus) prev.focus();
      resolve(v);
    };
    const onKey = (e) => {
      if (e.key === 'Escape') { e.preventDefault(); close(null); }
      if (e.key === 'Tab') {
        const f = Array.prototype.filter.call(box.querySelectorAll('button, [href], input, textarea, [tabindex]'), (x) => !x.disabled);
        if (!f.length) return;
        const first = f[0], last = f[f.length - 1];
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    };
    build(box, close);
    document.body.append(back);
    document.addEventListener('keydown', onKey, true);
    const first = box.querySelector('[data-autofocus]') || box.querySelector('button');
    if (first) first.focus();
  });
}

export function confirmBox(message, yes, no) {
  return modal((box, close) => {
    box.append(h('p', message), h('div.grid2', btn(no, { cls: 'btn-ghost', onClick: () => close(false) }), btn(yes, { cls: 'btn-primary', test: 'confirm-yes', onClick: () => close(true) })));
  }, { label: message });
}

// ------------------------------------------------------------------ step bar
export const STEPS = [
  { id: 'start', icon: 'flag', key: 'st_start' },
  { id: 'hear', icon: 'ear', key: 'st_hear' },
  { id: 'tapsay', icon: 'tap', key: 'st_tapsay' },
  { id: 'blend', icon: 'bubble', key: 'st_blend' },
  { id: 'challenge', icon: 'trophy', key: 'st_challenge' },
  { id: 'done', icon: 'sticker', key: 'st_done' },
];
export function stepBar(currentId, final) {
  const idx = STEPS.findIndex((s) => s.id === currentId);
  return h('ol.steps', { 'aria-label': 'Steps', 'data-test': 'steps' }, STEPS.map((s, i) =>
    h('li.st', { class: i < idx ? 'done' : i === idx ? 'on' : '', 'aria-current': i === idx ? 'step' : null },
      h('i', { html: i < idx ? icon('check') : icon(s.icon) }),
      h('span', t(final && s.id === 'challenge' ? 'st_final' : s.key)))));
}

/** Little helper that waits for one click on any of the given elements. */
export function waitTap(els) {
  return new Promise((resolve) => {
    const list = Array.isArray(els) ? els : [els];
    const handlers = list.map((el) => {
      const fn = () => { list.forEach((e, i) => e.removeEventListener('click', handlers[i])); resolve(el); };
      el.addEventListener('click', fn);
      return fn;
    });
  });
}

export { sleep };
