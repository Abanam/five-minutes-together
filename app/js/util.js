// Small helpers shared by every module.

export const FAST = /[?&]fast=1/.test(location.search) || window.FMT_FAST === true;

/** Create an element: h('div.card#id', {attrs}, children...) */
export function h(tag, attrs, ...kids) {
  const m = /^([a-z0-9-]+)?((?:[.#][^.#]+)*)$/i.exec(tag) || [];
  const el = document.createElement(m[1] || 'div');
  (m[2] || '').replace(/([.#])([^.#]+)/g, (_, k, v) => {
    if (k === '.') el.classList.add(v); else el.id = v;
    return '';
  });
  if (attrs && (typeof attrs !== 'object' || attrs instanceof Node || Array.isArray(attrs))) {
    kids.unshift(attrs);
    attrs = null;
  }
  if (attrs) {
    for (const k of Object.keys(attrs)) {
      const v = attrs[k];
      if (v === null || v === undefined || v === false) continue;
      if (k === 'html') el.innerHTML = v;
      else if (k === 'text') el.textContent = v;
      else if (k.slice(0, 2) === 'on' && typeof v === 'function') el.addEventListener(k.slice(2), v);
      else if (k === 'style' && typeof v === 'object') Object.assign(el.style, v);
      else if (k === 'class') el.className += ' ' + v;
      else el.setAttribute(k, v === true ? '' : v);
    }
  }
  append(el, kids);
  return el;
}

export function append(el, kids) {
  for (const k of kids) {
    if (k === null || k === undefined || k === false) continue;
    if (Array.isArray(k)) append(el, k);
    else if (k instanceof Node) el.appendChild(k);
    else el.appendChild(document.createTextNode(String(k)));
  }
  return el;
}

export function frag(html) {
  const t = document.createElement('template');
  t.innerHTML = html.trim();
  return t.content.firstElementChild;
}

export const $ = (sel, root = document) => root.querySelector(sel);
export const $$ = (sel, root = document) => Array.prototype.slice.call(root.querySelectorAll(sel));

export function sleep(ms) {
  return new Promise((r) => setTimeout(r, FAST ? Math.min(ms, 30) : ms));
}

/** 32-bit FNV-1a over UTF-16 code units of the NFC text (matches tools/make_audio.py). */
export function fnv1a(s) {
  s = s.normalize ? s.normalize('NFC') : s;
  let h = 0x811c9dc5;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  return ('0000000' + h.toString(16)).slice(-8);
}

/** Local calendar date as YYYY-MM-DD. */
export function today(d) {
  d = d || new Date();
  const p = (n) => (n < 10 ? '0' : '') + n;
  return d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate());
}

export function arDigits(n) {
  return String(n).replace(/[0-9]/g, (d) => '٠١٢٣٤٥٦٧٨٩'[+d]);
}

export function once(el, type) {
  return new Promise((res) => el.addEventListener(type, res, { once: true }));
}

export function clamp(v, a, b) {
  return Math.max(a, Math.min(b, v));
}
