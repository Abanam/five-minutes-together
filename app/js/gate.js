// Parent gate: press and hold for 3 seconds (pointer, touch, or Space/Enter key).
// Guards settings, external links, and the teacher and reviewer pages.

import { h, frag, FAST } from './util.js';
import { icon } from './art.js';
import { t, num } from './i18n.js';
import { modal, parentCard, btn } from './ui.js';
import { app } from './ctx.js';
import * as audio from './audio.js';

const HOLD_MS = 3000;
const GRACE_MS = 2 * 60 * 1000; // stay unlocked for 2 minutes inside the parent area

export function gatePassed() {
  return app.tour || Date.now() < app.gateUntil;
}

export function parentGate() {
  if (gatePassed()) return Promise.resolve(true);
  return modal((box, close) => {
    const R = 70, C = 2 * Math.PI * R;
    const ring = frag(`<svg class="ring" viewBox="0 0 150 150" aria-hidden="true"><circle cx="75" cy="75" r="${R}" fill="none" stroke="#EFE6CF" stroke-width="8"/><circle class="arc" cx="75" cy="75" r="${R}" fill="none" stroke="#0F5E73" stroke-width="8" stroke-linecap="round" stroke-dasharray="${C}" stroke-dashoffset="${C}"/></svg>`);
    const arc = ring.querySelector('.arc');
    const count = h('span.count', { 'aria-hidden': 'true' }, num(3));
    const hold = h('button.hold-btn', { type: 'button', 'data-test': 'gate-hold', 'aria-label': t('gateHold') + ' (3 s)' }, ring, frag(icon('parent')), h('span', t('gateHold')), count);
    let start = 0, raf = 0, held = false;
    const tick = () => {
      const el = Date.now() - start;
      const p = Math.min(1, el / (FAST ? 300 : HOLD_MS));
      arc.setAttribute('stroke-dashoffset', String(C * (1 - p)));
      count.textContent = num(Math.max(0, Math.ceil((1 - p) * 3)));
      if (p >= 1) { held = true; audio.sfx('chime'); app.gateUntil = Date.now() + GRACE_MS; close(true); return; }
      raf = requestAnimationFrame(tick);
    };
    const down = (e) => { if (e) e.preventDefault(); if (start) return; start = Date.now(); hold.classList.add('pressed'); raf = requestAnimationFrame(tick); };
    const up = () => {
      if (held) return;
      cancelAnimationFrame(raf); start = 0; hold.classList.remove('pressed');
      arc.setAttribute('stroke-dashoffset', String(C)); count.textContent = num(3);
    };
    hold.addEventListener('pointerdown', down);
    hold.addEventListener('pointerup', up);
    hold.addEventListener('pointerleave', up);
    hold.addEventListener('pointercancel', up);
    hold.addEventListener('contextmenu', (e) => e.preventDefault());
    hold.addEventListener('keydown', (e) => { if ((e.key === ' ' || e.key === 'Enter') && !e.repeat) down(e); else if (e.key === ' ' || e.key === 'Enter') e.preventDefault(); });
    hold.addEventListener('keyup', (e) => { if (e.key === ' ' || e.key === 'Enter') up(); });
    hold.setAttribute('data-autofocus', '');
    box.append(
      h('h2', t('gateTitle')),
      parentCard('gate_hold'),
      hold,
      h('p.small.muted.center', t('gateKbd')),
      btn(t('gateCancel'), { cls: 'btn-ghost btn-wide', test: 'gate-cancel', onClick: () => close(false) }),
    );
  }, { label: t('gateTitle'), test: 'gate' });
}
