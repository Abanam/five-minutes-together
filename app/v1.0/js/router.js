// Tiny hash router: #/name/param?key=value

import { parentGate } from './gate.js';
import * as audio from './audio.js';

const routes = {};
let currentDestroy = null;
let root = null;
let lastHash = '';
const afterRender = new Set();

export function route(name, render, opts = {}) {
  routes[name] = { render, gated: !!opts.gated };
}

export function parse(hash) {
  const raw = (hash || location.hash || '').replace(/^#\/?/, '');
  const [path, query] = raw.split('?');
  const parts = (path || 'home').split('/').filter(Boolean);
  const q = {};
  (query || '').split('&').forEach((kv) => { if (kv) { const [k, v] = kv.split('='); q[decodeURIComponent(k)] = decodeURIComponent(v || ''); } });
  return { name: parts[0] || 'home', params: parts.slice(1), query: q };
}

export function go(hash) {
  if (!hash.startsWith('#')) hash = '#/' + hash.replace(/^\//, '');
  if (location.hash === hash) render();
  else location.hash = hash;
}

export function onRendered(fn) { afterRender.add(fn); return () => afterRender.delete(fn); }

export async function render() {
  const r = parse(location.hash);
  let def = routes[r.name] || routes.home;
  if (def.gated) {
    const ok = await parentGate();
    if (!ok) {
      // stay where we were
      if (lastHash && lastHash !== location.hash) { history.replaceState(null, '', lastHash); return; }
      location.hash = '#/home';
      return;
    }
  }
  audio.stopSpeech();
  if (currentDestroy) { try { currentDestroy(); } catch (e) { /* ignore */ } }
  currentDestroy = null;
  root.innerHTML = '';
  window.scrollTo(0, 0);
  const res = def.render(root, r);
  currentDestroy = res && typeof res === 'function' ? res : null;
  lastHash = location.hash;
  const h1 = root.querySelector('h1, h2');
  if (h1 && !root.querySelector('[data-autofocus]')) { h1.setAttribute('tabindex', '-1'); }
  afterRender.forEach((fn) => { try { fn(r); } catch (e) { /* ignore */ } });
  document.dispatchEvent(new CustomEvent('fmt:rendered', { detail: r }));
}

export function startRouter(el) {
  root = el;
  window.addEventListener('hashchange', render);
  render();
}
