// The daily 5-minute session: Start → Hear it → Tap and say → Blend on your own → Sanad's challenge → Sticker.
// Fading support: level 1 (days 1–2) plays sounds automatically, level 2 (days 3–4) the child taps,
// level 3 (day 5) has no automatic audio at all and hints only on request.

import { h, frag, sleep, FAST } from '../util.js';
import { icon, picture, sticker } from '../art.js';
import { t, getLang, SEP } from '../i18n.js';
import { app, T } from '../ctx.js';
import { progress } from '../store.js';
import * as audio from '../audio.js';
import { go } from '../router.js';
import { isUnlocked, dayDef } from '../days.js';
import {
  btn, iconBtn, parentCard, letterTile, pictureBtn, markRight, sanadEl, sanadDo, celebrate, gentleRetry,
  stepBar, levelBadge, waitTap, txt, en,
} from '../ui.js';

const CANCEL = { cancelled: true };

export function dayAudioUrls(day) {
  const c = app.content;
  const urls = [];
  const sounds = new Set(day.newSounds.concat(day.reviewSounds || []));
  const words = new Set(day.tapSay.map((x) => x.word).concat(day.blend));
  day.challenge.forEach((it) => { if (it.type === 'sound') { sounds.add(it.target); it.choices.forEach((x) => sounds.add(x)); } else words.add(it.target); });
  words.forEach((w) => { (c.words[w] ? c.words[w].sounds : []).forEach((s) => sounds.add(s)); });
  sounds.forEach((s) => urls.push(audio.url.ph(s)));
  day.hear.find.forEach((f) => f.pictures.forEach((p) => urls.push(audio.url.word(p))));
  words.forEach((w) => { urls.push(audio.url.word(w)); urls.push(audio.url.blend(w)); });
  ['hello', 'find', 'again', 'say', 'sticker', 'tomorrow', 'great'].forEach((k) => urls.push(audio.url.en(k)));
  return urls;
}

export function sessionScreen(root, r) {
  const n = Math.max(1, Math.min(5, parseInt(r.params[0], 10) || 1));
  if (!isUnlocked(n)) { setTimeout(() => go('#/map'), 0); return null; }
  const C = app.content;
  const day = dayDef(n);
  const level = day.level;
  const LV = C.levels[level];
  const demo = !!r.query.demo || app.tour;
  const auto = LV.autoplay && !demo;          // level 1: sounds play automatically
  const noAutoAudio = LV.hintOnly || demo;     // level 3: nothing plays unless asked
  const flow = { cancelled: false };
  const chk = () => { if (flow.cancelled) throw CANCEL; };
  const pause = async (ms) => { await sleep(ms); chk(); };
  const play = async (p) => { await p; chk(); };
  const record = { items: [], blend: { right: 0, total: 0 } };

  audio.preload(dayAudioUrls(day));

  const top = h('div.s-top');
  const stage = h('section.stage', { 'aria-live': 'polite' });
  const pc = h('div.pc-wrap.stack');
  root.append(h('div.screen-child', { 'data-test': 'session', 'data-day': String(n) }, top, stage, pc));

  function setStep(id) {
    top.innerHTML = '';
    top.append(iconBtn('home', t('exit'), () => go('#/home'), 'btn-ghost exit-btn'), stepBar(id, day.final));
    root.querySelector('.screen-child').setAttribute('data-step', id);
  }
  function setParent(...cards) { pc.innerHTML = ''; cards.filter(Boolean).forEach((c) => pc.append(c)); }
  function clear() { stage.innerHTML = ''; }
  function title(iconName, key) {
    const k = { hear: ['st_hear', 'Hear it'], tapsay: ['st_tapsay', 'Tap and say'], blend: ['st_blend', 'Blend on your own'], challenge: [day.final ? 'st_final' : 'st_challenge', day.final ? 'Final check' : "Sanad's challenge"] }[key];
    return h('h2.step-title', frag(icon(iconName)), h('span', t(k[0])), getLang() === 'ar' ? en(k[1]) : null);
  }
  function nextBtn(label, test = 'next') {
    return btn(label || t('next'), { icon: 'next', iconAfter: true, cls: 'btn-primary btn-big next-btn', iconCls: 'flip-rtl', test });
  }
  const tipFor = (s) => btn(t('howToSay'), {
    icon: 'speaker', cls: 'btn-sand btn-small-text', test: 'how-to-say',
    onClick: () => audio.arabic(C.sounds[s].tip, T(C.sounds[s].tip).ar),
  });

  // ---------------------------------------------------------------- 0. start
  async function stepStart() {
    setStep('start'); clear();
    const sounds = day.newSounds.length ? day.newSounds : day.reviewSounds;
    const s = sanadEl('lg');
    const greet = iconBtn('speaker', 'Hello / مرحبًا', () => { sanadDo.wave(s); audio.english('hello'); }, 'sanad-say');
    const go1 = btn(t('start'), { icon: 'play', cls: 'btn-primary btn-big', test: 'go' });
    stage.append(
      h('div.day-head', h('span.pill', frag(icon('map')), t('dayN', { n }) + SEP + txt(C.stops[day.stop].name))),
      s, greet,
      h('div.tiles', { 'aria-label': t('allSix') }, sounds.map((x) => letterTile(x, { size: sounds.length > 3 ? 'sm' : 'mid', onTap: () => { audio.phoneme(x); sanadDo.nod(s); } }))),
      h('div.child-actions', go1),
    );
    setParent(
      parentCard(day.tip, { badge: null }),
      parentCard(LV.desc, { label: t('level'), extra: levelBadge(level) }),
    );
    sanadDo.wave(s);
    const tapped = waitTap(go1);
    if (!noAutoAudio) { pause(500).then(() => { if (!flow.cancelled && go1.isConnected) audio.english('hello'); }).catch(() => {}); }
    await play(tapped);
  }

  // ---------------------------------------------------------------- 1. hear it
  async function letterCard(s) {
    clear();
    const sn = sanadEl('sm');
    const tile = letterTile(s, { size: 'big', test: 'letter-card' });
    const next = nextBtn(); next.hidden = true;
    let heard = false;
    tile.addEventListener('click', async () => { sanadDo.nod(sn); await audio.phoneme(s); heard = true; next.hidden = false; });
    stage.append(title('ear', 'hear'), sn, tile, h('div.child-actions', next));
    setParent(parentCard('hear_L' + level, { extra: tipFor(s) }));
    const tapped = waitTap(next);
    if (auto) {
      await pause(500);
      tile.classList.add('lit'); await play(audio.phoneme(s)); tile.classList.remove('lit');
      heard = true; next.hidden = false;
    }
    await play(tapped);
  }

  async function keywords(s) {
    clear();
    const kws = C.sounds[s].keywords;
    const seen = new Set();
    const next = nextBtn(); next.hidden = true;
    const pics = kws.map((w) => pictureBtn(C.keywords[w].picture, w, {
      caption: true, test: 'kw',
      onTap: async (b) => { b.classList.add('lit'); await audio.keyword(w, s); b.classList.remove('lit'); seen.add(w); if (seen.size === kws.length) next.hidden = false; },
    }));
    stage.append(title('ear', 'hear'), h('div.tiles', letterTile(s, { size: 'sm', onTap: () => audio.phoneme(s) })), h('div.pic-row', pics), h('div.child-actions', next));
    setParent(parentCard('kw_L' + level));
    const tapped = waitTap(next);
    if (auto) {
      await pause(400);
      for (let i = 0; i < kws.length; i++) {
        pics[i].classList.add('lit'); await play(audio.keyword(kws[i], s)); pics[i].classList.remove('lit');
        seen.add(kws[i]); await pause(350);
      }
      next.hidden = false;
    }
    await play(tapped);
  }

  async function findSound(f) {
    clear();
    const s = f.sound;
    const sn = sanadEl('sm');
    const next = nextBtn(); next.hidden = true;
    const prompt = () => audio.say([{ url: audio.url.en('find'), tts: C.english.find, lang: 'en' }, { gap: 0.25 }, { url: audio.url.ph(s) }]);
    const ask = btn('', { icon: 'speaker', cls: 'btn-round say-big btn-primary', aria: t('findIt') + ' ' + s, test: 'find-prompt', onClick: prompt });
    let found = 0;
    const done = new Set();
    const pics = f.pictures.map((w) => pictureBtn(C.keywords[w].picture, w, {
      test: 'find-pic',
      onTap: async (b) => {
        if (done.has(w)) return;
        if (C.keywords[w].first === s) {
          done.add(w); found++; markRight(b); celebrate(b, sn);
          audio.word(w);
          if (found === 2) { await sleep(600); next.hidden = false; next.focus(); }
        } else {
          await gentleRetry(b, sn);
          audio.phoneme(s);
        }
      },
    }));
    stage.append(title('ear', 'hear'), h('div.row', { style: { justifyContent: 'center' } }, sn, ask, letterTile(s, { size: 'sm', onTap: () => audio.phoneme(s) })), h('div.pic-row.find-grid', pics), h('div.child-actions', next));
    setParent(parentCard('find_L' + level));
    const tapped = waitTap(next);
    if (!noAutoAudio) { await pause(450); if (!done.size) await play(prompt()); }
    await play(tapped);
  }

  async function review6() {
    clear();
    const sounds = day.reviewSounds;
    const next = nextBtn(); next.hidden = true;
    const tapped = new Set();
    const sn = sanadEl('sm');
    const tiles = sounds.map((s) => letterTile(s, {
      size: 'mid', test: 'review-tile',
      onTap: async (el) => {
        sanadDo.nod(sn); await audio.phoneme(s);
        if (!tapped.has(s)) { tapped.add(s); el.append(h('span.done-mark', { 'aria-hidden': 'true' }, frag(icon('check')))); }
        if (tapped.size === sounds.length) next.hidden = false;
      },
    }));
    stage.append(title('ear', 'hear'), sn, h('div.grid3', { style: { direction: 'ltr', justifyItems: 'center' } }, tiles), h('div.child-actions', next));
    setParent(parentCard('review_L3'));
    await play(waitTap(next));
  }

  async function stepHear() {
    setStep('hear');
    if (day.hear.review) await review6();
    else {
      for (const s of day.newSounds) {
        await letterCard(s);
        await keywords(s);
        const f = day.hear.find.find((x) => x.sound === s);
        if (f) await findSound(f);
      }
      return;
    }
    for (const f of day.hear.find) await findSound(f);
  }

  // ---------------------------------------------------------------- 2. tap and say
  function wordTiles(w, opts = {}) {
    const sounds = C.words[w].sounds;
    const row = h('div.tiles.train', { 'data-word': w });
    const engine = h('span.engine', { html: icon('train') });
    row.append(engine);
    const tiles = sounds.map((s) => letterTile(s, { size: 'word', wheels: true, test: 'word-tile', onTap: opts.onTap }));
    tiles.forEach((x) => row.append(x));
    return { row, tiles, sounds };
  }

  async function revealWord(w, sn) {
    const meta = C.words[w];
    const box = h('div.reveal', { 'data-test': 'reveal' });
    if (meta.picture) box.innerHTML = `<div class="reveal-pic">${picture(meta.picture)}</div>`;
    box.append(h('p.reveal-word', { lang: 'en' }, w), h('p.meaning', t('wordMeaning', { x: meta.ar })));
    celebrate(box, sn);
    return box;
  }

  async function tapSayWord(item) {
    clear();
    const w = item.word;
    const sn = sanadEl('sm');
    const heard = new Set();
    const train = btn(t('train'), { icon: 'train', cls: 'btn-primary btn-big', aria: t('trainLabel'), test: 'train' });
    train.disabled = true;
    const wt = wordTiles(w, {
      onTap: async (el) => {
        const i = wt.tiles.indexOf(el);
        el.classList.add('lit'); await audio.phoneme(wt.sounds[i]); el.classList.remove('lit');
        heard.add(i); if (heard.size === wt.tiles.length) train.disabled = false;
      },
    });
    const hint = btn(t('hint'), { icon: 'hint', cls: 'btn-sand', aria: t('hintLabel'), test: 'hint', onClick: () => playSegmented(wt) });
    stage.append(title('tap', 'tapsay'), sn, wt.row, h('div.child-actions', hint, train));
    setParent(parentCard('tapsay_L' + level));
    const tapped = waitTap(train);
    if (auto) {
      await pause(400);
      await playSegmented(wt);
      chk();
      wt.tiles.forEach((_, i) => heard.add(i));
      train.disabled = false;
    }
    await play(tapped);
    audio.stopSpeech();
    hint.remove(); train.remove();
    wt.row.classList.add('joined');
    audio.sfx('whoosh');
    await pause(700);
    await play(audio.word(w));
    const rv = await revealWord(w, sn);
    stage.append(rv);
    const next = nextBtn(t('nextWord'));
    stage.append(h('div.child-actions', next));
    setParent(parentCard(item.ask, { cls: 'ask', label: t('askTip'), test: 'ask-card' }));
    await play(waitTap(next));
  }

  async function playSegmented(wt) {
    for (let i = 0; i < wt.tiles.length; i++) {
      if (flow.cancelled) return;
      wt.tiles[i].classList.add('lit');
      await audio.phoneme(wt.sounds[i]);
      wt.tiles[i].classList.remove('lit');
      if (i < wt.tiles.length - 1) await sleep(400);
    }
  }

  async function stepTapSay() {
    setStep('tapsay');
    for (const item of day.tapSay) await tapSayWord(item);
  }

  // ---------------------------------------------------------------- 3. blend on your own
  async function blendWord(w) {
    clear();
    const sn = sanadEl('sm');
    const wt = wordTiles(w, { onTap: async (el) => { const i = wt.tiles.indexOf(el); el.classList.add('lit'); await audio.phoneme(wt.sounds[i]); el.classList.remove('lit'); } });
    const hint = btn(t('hint'), { icon: 'hint', cls: 'btn-sand', aria: t('hintLabel'), test: 'hint', onClick: () => playSegmented(wt) });
    const right = btn(t('saidRight'), { icon: 'check', cls: 'btn-ok', test: 'said-right' });
    const again = btn(t('tryAgain'), { icon: 'retry', cls: 'btn-sand', test: 'try-again' });
    const judge = h('div.judge', right, again);
    stage.append(title('bubble', 'blend'), sn, wt.row, h('div.child-actions', hint));
    setParent(parentCard('blend_L' + level, { extra: judge }));
    let tries = 0;
    let busy = false;
    record.blend.total++;
    // the parent can confirm at any moment (even during a replay); "try again" replays the sounds
    const confirmed = new Promise((resolve) => {
      right.addEventListener('click', () => { audio.stopSpeech(); resolve(); });
      again.addEventListener('click', async () => {
        if (busy) return;
        busy = true;
        tries++;
        if (tries === 1) stage.append(h('p.listen-again', { lang: 'en' }, frag(icon('retry')), "Let's listen again"));
        try { await gentleRetry(wt.row, sn); await playSegmented(wt); } finally { busy = false; }
        if (tries >= 2 && !judge.querySelector('[data-test="show-me"]')) {
          const show = btn(t('showMe'), { icon: 'sparkle', cls: 'btn-ghost', test: 'show-me' });
          judge.append(show);
          show.addEventListener('click', () => right.click());
        }
      });
    });
    if (!noAutoAudio) { pause(300).then(() => { if (!tries && right.isConnected) audio.english('say'); }).catch(() => {}); }
    await play(confirmed);
    if (tries === 0) record.blend.right++;
    hint.remove();
    judge.remove();
    wt.row.classList.add('joined');
    await pause(400);
    await play(audio.word(w));
    stage.append(await revealWord(w, sn));
    const next = nextBtn(t('nextWord'));
    stage.append(h('div.child-actions', next));
    await play(waitTap(next));
  }

  async function stepBlend() {
    setStep('blend');
    for (const w of day.blend) await blendWord(w);
  }

  // ---------------------------------------------------------------- 4. Sanad's challenge / final check
  async function stepChallenge() {
    setStep('challenge'); clear();
    const sIntro = sanadEl('lg');
    const goBtn = btn(t('start'), { icon: 'play', cls: 'btn-primary btn-big', test: 'go-challenge' });
    stage.append(title('trophy', 'challenge'), sIntro, h('div.child-actions', goBtn));
    setParent(parentCard(day.final ? 'final_intro' : 'challenge_intro'));
    sanadDo.wave(sIntro);
    await play(waitTap(goBtn));
    const items = day.challenge;
    for (let i = 0; i < items.length; i++) {
      const it = items[i];
      clear();
      const sn = sanadEl('sm');
      const stim = () => (it.type === 'sound' ? audio.phoneme(it.target) : audio.blend(it.target, C.words[it.target].sounds));
      const replayBtn = btn('', { icon: 'speaker', cls: 'btn-round say-big btn-primary', aria: t('replay'), test: 'stimulus', onClick: stim });
      const dots = h('div.progress-dots', { 'aria-label': t('itemOf', { n: i + 1, t: items.length }) },
        items.map((_, k) => h('b', { class: k < i ? 'done' : k === i ? 'now' : '' }, String(k + 1))));
      const choices = it.choices.map((c) => it.type === 'sound'
        ? letterTile(c, { size: 'mid', test: 'choice', aria: c })
        : pictureBtn(C.words[c].picture, c, { test: 'choice', aria: c }));
      choices.forEach((el, k) => el.setAttribute('data-value', it.choices[k]));
      stage.append(title('trophy', 'challenge'), dots, h('div.row', { style: { justifyContent: 'center' } }, sn, replayBtn), h('div.choice-row', { 'data-test': 'choices' }, choices));
      const key = (it.type === 'sound' ? 'ch_sound' : 'ch_blend') + (LV.hintOnly ? '_L3' : '');
      setParent(parentCard(key));
      // answers are accepted at any moment; a wrong one gets "Let's listen again" and the sound again
      const first = await new Promise((resolve) => {
        let firstTry = true, locked = false;
        choices.forEach((el) => el.addEventListener('click', () => {
          if (locked) return;
          if (el.getAttribute('data-value') === it.target) {
            locked = true;
            audio.stopSpeech();
            if (it.type === 'blend') markRight(el); else el.append(h('span.done-mark', { 'aria-hidden': 'true' }, frag(icon('check'))));
            celebrate(el, sn);
            resolve(firstTry);
          } else {
            firstTry = false;
            gentleRetry(el, sn).then(() => { if (!locked && !flow.cancelled) stim(); });
          }
        }));
        if (!noAutoAudio) pause(350).then(() => { if (firstTry && !locked) stim(); }).catch(() => {});
      });
      chk();
      record.items.push({ type: it.type, target: it.target, firstTry: first });
      await pause(900);
    }
  }

  // ---------------------------------------------------------------- 5. sticker + stop
  async function stepDone() {
    setStep('done'); clear();
    const score = record.items.filter((x) => x.firstTry).length;
    if (!demo && record.items.length) {
      progress.complete(n, { challenge: { score, total: record.items.length, items: record.items }, blend: record.blend });
    } else if (!demo) {
      progress.complete(n, {});
    }
    const sName = txt(C.stickers[day.sticker].name);
    const sn = sanadEl('');
    const stEl = h('div.sticker-reveal', { html: sticker(day.sticker), role: 'img', 'aria-label': t('stickerFor', { x: sName }) });
    const finish = btn(day.final ? t('seeResults') : t('done'), { icon: day.final ? 'chart' : 'home', cls: 'btn-primary btn-big', test: 'finish' });
    const book = btn(t('stickers'), { icon: 'book', cls: 'btn-sand', test: 'to-stickers' });
    stage.append(
      stEl, h('h2.center', t('stickerFor', { x: sName })),
      sn, h('p.speech', { lang: 'en' }, 'See you tomorrow!'),
      h('p.stop-sign', { 'data-test': 'stop-sign' }, frag(icon('moon')), t('sessionOver')),
      h('div.child-actions', finish, book),
    );
    setParent(
      parentCard(day.final ? 'celebrate_d5' : 'celebrate'),
      parentCard(day.home, { label: t('homeActivity'), cls: 'ask', test: 'home-activity' }),
    );
    audio.sfx('sticker');
    sanadDo.wave(sn);
    const tapped = waitTap([finish, book]);
    if (!noAutoAudio) {
      pause(900).then(async () => { await audio.english('sticker'); if (finish.isConnected) await audio.english('tomorrow'); }).catch(() => {});
    }
    const which = await tapped;
    audio.stopSpeech();
    go(which === book ? '#/stickers' : day.final ? '#/results' : '#/home');
  }

  const order = ['start', 'hear', 'tapsay', 'blend', 'challenge', 'done'];
  const fns = { start: stepStart, hear: stepHear, tapsay: stepTapSay, blend: stepBlend, challenge: stepChallenge, done: stepDone };
  let from = order.indexOf(r.query.step || 'start');
  if (from < 0) from = 0;
  (async () => {
    try {
      for (let i = from; i < order.length; i++) { chk(); await fns[order[i]](); }
    } catch (e) {
      if (e !== CANCEL) { console.error(e); }
    }
  })();
  return () => { flow.cancelled = true; audio.stopSpeech(); };
}
