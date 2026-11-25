// Parent area (Arabic first, English toggle): home, onboarding, results, sticker book, tips, how-to, about.

import { h, frag, arDigits } from '../util.js';
import { icon, family, sticker, sanad, picture } from '../art.js';
import { t, num, getLang, setLang, SEP } from '../i18n.js';
import { app, T } from '../ctx.js';
import { settings, progress } from '../store.js';
import * as audio from '../audio.js';
import { go, render } from '../router.js';
import { status, nextDay, dayDef, days, objectives, dayOfSound, weakSounds, isDone } from '../days.js';
import { btn, iconBtn, parentCard, letterTile, letterChip, levelBadge, txt, en, richText } from '../ui.js';
import { startTour } from '../tour.js';

export function offlineBadge() {
  const b = h('span.offline-badge', { 'data-test': 'offline-badge', role: 'status', hidden: !app.offlineReady },
    frag(icon('cloud')), h('span', getLang() === 'ar' ? 'جاهز دون إنترنت ✓' : 'Ready offline ✓'));
  return b;
}

export function topbar(titleKey, opts = {}) {
  const bar = h('header.topbar');
  if (opts.home) {
    const logo = h('div.logo', { html: sanad({ anim: false }), 'aria-hidden': 'true' });
    const sub = getLang() === 'ar' ? h('bdi', { lang: 'en', dir: 'ltr' }, '5 Minutes Together') : h('bdi', { lang: 'ar', dir: 'rtl' }, 'خمس دقائق معًا');
    bar.append(h('div.brand', logo, h('div.brand-name', t('appName'), h('small', sub))));
  } else {
    bar.append(iconBtn('back', t('back'), () => (history.length > 1 ? history.back() : go('#/home')), 'btn-ghost flip-rtl back-btn'));
    bar.append(h('h1', t(titleKey)));
  }
  if (opts.home || opts.badge) bar.append(offlineBadge());
  bar.append(btn(t('langToggle'), {
    icon: 'globe', cls: 'btn-ghost lang-toggle btn-small-text', aria: t('langToggleLabel'), test: 'lang-toggle',
    onClick: () => { setLang(getLang() === 'ar' ? 'en' : 'ar'); render(); },
  }));
  return bar;
}

// ---------------------------------------------------------------- onboarding (3 screens with audio)
export function onboardingScreen(root, r) {
  const i = Math.max(1, Math.min(3, parseInt(r.params[0], 10) || 1));
  const art = i === 1 ? h('div.hero', { html: family('mother-boy') })
    : i === 2 ? stepsArt()
    : h('div', h('div.sanad.lg', { html: sanad({ eyes: 'open', mouth: 'open', anim: true }) }));
  const next = btn(i < 3 ? t('next') : t('getStarted'), { icon: 'next', iconAfter: true, iconCls: 'flip-rtl', cls: 'btn-primary btn-big btn-wide', test: 'ob-next' });
  next.addEventListener('click', () => {
    if (i < 3) go('#/onboarding/' + (i + 1));
    else { settings.set({ onboarded: true }); go('#/home'); }
  });
  const skip = btn(t('skip'), { cls: 'btn-ghost', test: 'ob-skip', onClick: () => { settings.set({ onboarded: true }); go('#/home'); } });
  const dots = h('div.progress-dots', { 'aria-label': t('stepOf', { n: i }) }, [1, 2, 3].map((k) => h('b', { class: k < i ? 'done' : k === i ? 'now' : '' }, num(k))));
  root.append(
    topbar('welcome', { home: true }),
    h('main.screen.stack', { 'data-test': 'onboarding', 'data-step': String(i) },
      art, dots, parentCard('ob' + i, { cls: 'big' }), next, h('div.center', skip)),
  );
}

function stepsArt() {
  const items = [['ear', 'st_hear'], ['tap', 'st_tapsay'], ['bubble', 'st_blend'], ['trophy', 'st_challenge']];
  return h('div.section-card.center', { 'aria-hidden': 'false' },
    h('div', { style: { fontSize: '2.2rem', fontWeight: 800, color: '#0F5E73' } }, getLang() === 'ar' ? '٥ دقائق' : '5 minutes'),
    h('div.grid2', items.map(([ic, k], n) => h('div.pill', { style: { justifyContent: 'center', padding: '10px' } }, frag(icon(ic)), num(n + 1) + '. ' + t(k)))));
}

// ---------------------------------------------------------------- home
export function homeScreen(root) {
  if (!settings.get().onboarded && !app.tour) { go('#/onboarding/1'); return; }
  const C = app.content;
  const nd = nextDay();
  const main = h('main.screen.stack', { 'data-test': 'home' });
  main.append(h('div.hero', { html: family('father-girl'), role: 'img', 'aria-label': getLang() === 'ar' ? 'أب يساعد ابنته على التعلّم' : 'A father helping his daughter learn' }));

  // today's stop + start
  const card = h('section.today-card', { 'data-test': 'today-card' });
  const mini = h('div.mini-map', { 'aria-label': t('progress5') }, days().map((d) => {
    const st = status(d.day);
    return h('span.md', { class: st, title: t('dayN', { n: d.day }) }, st === 'done' ? frag(icon('check')) : st === 'locked' ? frag(icon('lock')) : num(d.day));
  }));
  if (nd.day && nd.open) {
    const d = dayDef(nd.day);
    card.append(
      h('div.row', { style: { justifyContent: 'space-between' } }, h('div.day-title', t('dayN', { n: d.day }) + SEP + txt(C.stops[d.stop].name)), levelBadge(d.level)),
      mini,
      parentCard('home_ready'),
      h('div', { style: { marginTop: '12px' } }, btn(t('startToday'), { icon: 'play', cls: 'btn-primary btn-big btn-wide', test: 'start', onClick: () => go('#/map') })),
    );
  } else if (nd.allDone) {
    card.append(h('div.day-title', t('results')), mini, parentCard('home_all'),
      h('div.grid2', { style: { marginTop: '12px' } }, btn(t('results'), { icon: 'chart', cls: 'btn-primary', onClick: () => go('#/results') }), btn(t('map'), { icon: 'map', cls: 'btn-sand', test: 'start', onClick: () => go('#/map') })));
  } else {
    card.append(h('div.day-title', t('dayN', { n: nd.day }) + SEP + t('locked')), mini, parentCard('home_done'),
      h('div', { style: { marginTop: '12px' } }, btn(t('map'), { icon: 'map', cls: 'btn-sand btn-wide', test: 'start', onClick: () => go('#/map') })));
  }
  main.append(card);

  // latest results
  const p = progress.get();
  const last = p.last && p.days[p.last];
  main.append(h('section.section-card', { 'data-test': 'latest' },
    h('h2', t('latest')),
    last && last.challenge
      ? h('p', t('lastSession', { n: p.last, s: last.challenge.score, t: last.challenge.total }))
      : h('p.muted', t('noResults')),
    btn(t('results'), { icon: 'chart', cls: 'btn-ghost btn-wide', test: 'to-results', onClick: () => go('#/results') })));

  // links
  const L = (key, ic, hash, gated, test) => {
    const b = btn(t(key), { icon: ic, cls: 'link-btn', test, onClick: () => go(hash) });
    if (gated) b.append(h('span.lock-dot', { html: icon('lock'), 'aria-hidden': 'true' }), h('span.sr-only', ' (' + t('gateTitle') + ')'));
    return b;
  };
  main.append(h('nav.links', { 'aria-label': 'Parent menu' },
    L('howto', 'info', '#/howto', false, 'to-howto'),
    L('tips', 'speaker', '#/tips', false, 'to-tips'),
    L('apps', 'apps', '#/apps', false, 'to-apps'),
    L('stickers', 'book', '#/stickers', false, 'to-stickers'),
    L('teachers', 'teacher', '#/teachers', true, 'to-teachers'),
    L('review', 'clipboard', '#/review', true, 'to-review'),
    L('settings', 'gear', '#/settings', true, 'to-settings'),
    L('about', 'shield', '#/about', false, 'to-about')));

  main.append(h('div.center', btn(t('tour'), { icon: 'flag', cls: 'btn-ghost tour-btn', test: 'tour', onClick: () => startTour() })));
  main.append(h('p.footer-note', t('version') + SEP + t('noData')));
  root.append(topbar('appName', { home: true }), main);
}

// ---------------------------------------------------------------- results
export function resultsScreen(root) {
  const C = app.content;
  const main = h('main.screen.stack', { 'data-test': 'results' });
  main.append(parentCard('res_intro'));
  const list = h('section.section-card', h('h2', t('results')));
  days().forEach((d) => {
    const r = progress.day(d.day);
    const st = status(d.day);
    const done = st === 'done';
    list.append(h('div.result-row', { 'data-test': 'result-day', 'data-day': String(d.day) },
      h('span.status', { class: done ? 'done' : '', html: icon(done ? 'check' : st === 'locked' ? 'lock' : 'play') }),
      h('div', h('b', t('dayN', { n: d.day }) + SEP + txt(C.stops[d.stop].name)),
        h('div.small.muted', done ? [t('doneDay') + SEP, h('bdi', { dir: 'ltr' }, getLang() === 'ar' ? arDigits(r.date) : r.date)] : t(st === 'locked' ? 'locked' : 'openDay')),
        done && r.blend && r.blend.total ? h('div.small', t('blendScore') + ': ' + t('ofN', { s: r.blend.right, t: r.blend.total })) : null),
      h('span.score', done && r.challenge ? t('ofN', { s: r.challenge.score, t: r.challenge.total }) : '—')));
  });
  main.append(list);

  // objectives
  const ob = objectives();
  const obj = h('section.stack.objectives', { 'data-test': 'objectives' }, h('h2', t('objectives')));
  const objBox = (key, textId, data, metId, notId) => {
    const pending = !data;
    const met = data && data.met;
    const box = h('div.objective', { class: pending ? '' : met ? 'met' : 'not', 'data-test': 'obj-' + key, 'data-met': pending ? 'pending' : String(!!met) },
      h('div.obj-head', h('span', key), h('span.obj-state', frag(icon(pending ? 'hint' : met ? 'check' : 'retry')), t(pending ? 'pending' : met ? 'met' : 'notMet'))),
      h('p.small', richText(txt(textId))));
    if (data) {
      box.append(h('div.meter', h('span', { style: { width: Math.round((100 * data.score) / data.of) + '%' } })),
        h('p', h('b', t('ofN', { s: data.score, t: data.of }))));
    }
    if (metId && data) box.append(parentCard(met ? metId : notId));
    return box;
  };
  obj.append(objBox('O1', 'obj_o1', ob.final ? ob.O1 : null, 'res_o1_met', 'res_o1_not'));
  obj.append(objBox('O2', 'obj_o2', ob.final ? ob.O2 : null, 'res_o2_met', 'res_o2_not'));
  obj.append(objBox('O3', 'obj_o3', ob.O3, null, null));
  obj.querySelector('[data-test="obj-O3"]').append(parentCard('res_o3'));
  if (!ob.final) obj.append(parentCard('res_before'));
  main.append(obj);

  // what to practise again
  const weak = ob.final ? ob.missSounds.concat(ob.fromWords.filter((x) => ob.missSounds.indexOf(x) < 0)) : weakSounds();
  const prac = h('section.section-card.stack', { 'data-test': 'practise' }, h('h2', t('practise')));
  if (weak.length) {
    prac.append(parentCard('res_practise'));
    prac.append(h('div.row', { style: { flexWrap: 'wrap', direction: 'ltr', justifyContent: 'center' } },
      weak.map((l) => letterTile(l, { size: 'sm', onTap: () => audio.phoneme(l), test: 'weak-tile' }))));
    const daysToRepeat = [];
    weak.forEach((l) => { const dn = dayOfSound(l); if (daysToRepeat.indexOf(dn) < 0) daysToRepeat.push(dn); });
    prac.append(h('div.grid2', daysToRepeat.sort().map((dn) => btn(t('repeatDayN', { n: dn }), { icon: 'retry', cls: 'btn-sand', onClick: () => go('#/day/' + dn) }))));
    if (ob.final && ob.missWords.length) prac.append(h('p', t('practise') + ': ', ob.missWords.map((w) => en(w + ' '))));
  } else if (ob.final || days().some((d) => isDone(d.day))) {
    prac.append(parentCard('res_good'));
  } else {
    prac.append(h('p.muted', t('noResults')));
  }
  main.append(prac);
  root.append(topbar('results'), main);
}

// ---------------------------------------------------------------- sticker book
export function stickersScreen(root) {
  const C = app.content;
  const grid = h('div.sticker-grid', { 'data-test': 'sticker-book' });
  days().forEach((d) => {
    const got = isDone(d.day);
    const name = txt(C.stickers[d.sticker].name);
    const letters = d.newSounds.length ? d.newSounds : d.reviewSounds;
    grid.append(h('div.sticker-slot', { class: got ? '' : 'locked', 'data-test': 'sticker', 'data-earned': String(got) },
      h('div', { html: sticker(d.sticker, { earned: got }), role: 'img', 'aria-label': got ? name : t('locked') + ' – ' + t('dayN', { n: d.day }) }),
      h('b', got ? name : t('dayN', { n: d.day })),
      h('div.letters', letters.map((l) => letterChip(l))),
      got ? null : h('div.small.muted', frag(icon('lock', 'inline')), t('locked'))));
  });
  root.append(topbar('stickers'), h('main.screen.stack', parentCard('stickers_intro'), grid));
}

// ---------------------------------------------------------------- pronunciation tips
export function tipsScreen(root) {
  const C = app.content;
  const main = h('main.screen.stack', { 'data-test': 'tips' }, parentCard('tip_general', { cls: 'ask' }));
  Object.keys(C.sounds).forEach((l) => {
    const s = C.sounds[l];
    main.append(h('div.tip-row', { 'data-test': 'tip-row', 'data-letter': l },
      h('div.tip-head',
        letterTile(l, { size: '', onTap: () => audio.phoneme(l), test: 'tip-tile' }),
        h('div.kw', s.keywords.map((w) => h('button.pic-btn.pic-mini', { type: 'button', 'aria-label': w + ' (' + l + ')', html: picture(C.keywords[w].picture), onclick: () => audio.keyword(w, l) })))),
      parentCard(s.tip, { label: [getLang() === 'ar' ? 'صوت ' : 'Sound ', en(l)] })));
  });
  root.append(topbar('tips'), main);
}

// ---------------------------------------------------------------- how to use
export function howtoScreen(root) {
  const main = h('main.screen.stack', { 'data-test': 'howto' }, h('div.hero', { html: family('sister-boy'), role: 'img', 'aria-label': getLang() === 'ar' ? 'أخت كبيرة تساعد أخاها' : 'An older sister helping her little brother' }));
  for (let i = 1; i <= 6; i++) main.append(parentCard('howto_' + i, { label: t('forParent'), badge: null }));
  main.append(h('div.section-card.stack', h('h2', t('level')), [1, 2, 3].map((lv) => h('div', levelBadge(lv), h('p.small', richText(txt(app.content.levels[lv].desc)))))));
  root.append(topbar('howto'), main);
}

// ---------------------------------------------------------------- about & privacy
export function aboutScreen(root) {
  const C = app.content;
  const both = (id) => h('div.section-card', h('p', { lang: 'ar', dir: 'rtl' }, richText(T(id).ar)), h('p', { lang: 'en', dir: 'ltr', class: 'en-block' }, T(id).en));
  const main = h('main.screen.stack', { 'data-test': 'about' },
    h('h2', t('purpose')), both('about_purpose'),
    h('h2', t('learningObjectives')), both('obj_o1'), both('obj_o2'), both('obj_o3'),
    h('h2', t('privacy')), h('div.section-card', { 'data-test': 'privacy' }, h('p', h('b', 'لا تغادر أي بيانات هذا الجهاز — No data leaves this device')), h('p', { lang: 'ar', dir: 'rtl' }, T('about_privacy').ar), h('p', { lang: 'en', dir: 'ltr' }, T('about_privacy').en)),
    parentCard('about_privacy'),
    h('h2', t('credits')), h('div.section-card', { lang: 'en', dir: 'ltr', style: { textAlign: 'left' } },
      h('p', 'Fonts: Andika by SIL Global (SIL Open Font License 1.1, official webfonts, unmodified); Baloo Bhaijaan 2 by Ek Type / The Baloo 2 Project Authors (SIL Open Font License 1.1, Arabic subset).'),
      h('p', 'English voice: Kokoro-82M v1.0 (hexgrad, Apache-2.0), voice "af_heart", run locally with kokoro-onnx. Letter sounds were made from IPA phoneme input and checked acoustically.'),
      h('p', 'Arabic voice: Meta MMS-TTS Arabic (facebook/mms-tts-ara, CC BY-NC 4.0), run locally. Used here for non-commercial education.'),
      h('p', 'All pictures, the mascot Sanad, the map and the stickers are original drawings made for this app. Sound effects are synthesised in the browser. No photos, brands or existing characters.'),
      h('p', 'Full list: CREDITS.md in the project.')),
    h('h2', t('aiNote')), both('about_ai'),
    h('p.footer-note', t('version') + SEP + t('noData')));
  root.append(topbar('about', { badge: true }), main);
}
