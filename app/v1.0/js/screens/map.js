// Journey map: five Omani stops (beach, palm grove, fort, wadi, sea with a dhow). One stop per day.

import { h, frag } from '../util.js';
import { icon, mapArt, MAP_STOPS, sanad } from '../art.js';
import { t, num } from '../i18n.js';
import { app } from '../ctx.js';
import * as audio from '../audio.js';
import { go } from '../router.js';
import { status, days } from '../days.js';
import { iconBtn, parentCard, toast, txt } from '../ui.js';

export function mapScreen(root) {
  const C = app.content;
  const wrap = h('div.map-wrap', { 'data-test': 'map' });
  wrap.innerHTML = mapArt();
  let sanadAt = null;
  days().forEach((d, i) => {
    const pos = MAP_STOPS.find((s) => s.id === d.stop) || MAP_STOPS[i];
    const st = status(d.day);
    const name = txt(C.stops[d.stop].name);
    const label = `${t('dayN', { n: d.day })}: ${name} — ${t(st === 'done' ? 'doneDay' : st === 'today' ? 'todayDay' : st === 'open' ? 'openDay' : 'locked')}`;
    const b = h('button.stop-btn', {
      type: 'button', class: st, 'data-test': 'stop', 'data-day': String(d.day), 'data-status': st, 'aria-label': label,
      style: { left: (pos.x / 360) * 100 + '%', top: (pos.y / 640) * 100 + '%' },
    }, h('span', num(d.day)), frag(icon(st === 'locked' ? 'lock' : st === 'done' ? 'starFill' : 'play')));
    if (st === 'done') b.append(h('span.badge', { 'aria-hidden': 'true' }, frag(icon('check'))));
    b.addEventListener('click', () => {
      if (st === 'locked') {
        toast(t('locked'));
        audio.english('sleep');
        pcWrap.innerHTML = '';
        pcWrap.append(parentCard('locked'));
        return;
      }
      go('#/day/' + d.day);
    });
    wrap.append(b);
    if (st === 'today' || (!sanadAt && st === 'open')) sanadAt = pos;
  });
  if (!sanadAt) {
    const last = days().filter((d) => status(d.day) === 'done').pop();
    if (last) sanadAt = MAP_STOPS.find((s) => s.id === last.stop);
  }
  if (sanadAt) {
    const s = h('div.map-sanad', { 'aria-hidden': 'true', style: { left: (sanadAt.x / 360) * 100 + '%', top: (sanadAt.y / 640) * 100 + '%' } });
    s.innerHTML = sanad({ anim: false });
    wrap.append(s);
  }
  const legend = h('div.map-legend', { 'aria-hidden': 'true' },
    h('span', h('i', { style: { background: '#FFD166' }, html: icon('check') }), t('doneDay')),
    h('span', h('i', { style: { background: '#FF8A3D' }, html: icon('play') }), t('todayDay')),
    h('span', h('i', { style: { background: '#EFEAE0' }, html: icon('lock') }), t('locked')));
  const pcWrap = h('div');
  pcWrap.append(parentCard('map_hint'));
  root.append(h('div.screen-child',
    h('div.s-top', iconBtn('home', t('exit'), () => go('#/home'), 'btn-ghost'), h('h1.sr-only', t('map'))),
    wrap, legend, pcWrap));
}
