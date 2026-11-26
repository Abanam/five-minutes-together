// Day unlocking (next day opens on the next calendar day), levels and objective scoring.

import { app } from './ctx.js';
import { progress, settings } from './store.js';
import { today } from './util.js';

export function days() { return app.content.days; }
export function dayDef(n) { return app.content.days[n - 1]; }

export function isDone(n) { const d = progress.day(n); return !!(d && d.done); }

/** Day n is open if it is Day 1, already completed, unlocked by setting/tour,
 *  or the previous day was completed on an earlier calendar day. */
export function isUnlocked(n) {
  if (n === 1 || isDone(n)) return true;
  if (settings.get().unlockAll || app.tour) return true;
  const prev = progress.day(n - 1);
  return !!(prev && prev.done && prev.firstDate && prev.firstDate < today());
}

/** The day the family should do next (first not-yet-done day), and whether it is open today. */
export function nextDay() {
  const all = days();
  for (const d of all) {
    if (!isDone(d.day)) return { day: d.day, open: isUnlocked(d.day) };
  }
  return { day: null, open: false, allDone: true };
}

export function status(n) {
  if (isDone(n)) return 'done';
  const nd = nextDay();
  if (nd.day === n && nd.open) return 'today';
  return isUnlocked(n) ? 'open' : 'locked';
}

/** Which day introduces each sound (for "practise again" suggestions). */
export function dayOfSound(letter) {
  for (const d of days()) if (d.newSounds.indexOf(letter) >= 0) return d.day;
  return 1;
}

/** Objective results from the Day 5 final check (first-try answers). */
export function objectives() {
  const d5 = progress.day(5);
  const p = progress.get();
  const sessions = days().filter((d) => isDone(d.day)).length;
  const out = { sessions, O3: { score: sessions, of: 5, met: sessions >= 5 } };
  const items = d5 && d5.challenge && d5.challenge.items;
  if (!items) return Object.assign(out, { final: false });
  const snd = items.filter((i) => i.type === 'sound');
  const bl = items.filter((i) => i.type === 'blend');
  const sScore = snd.filter((i) => i.firstTry).length;
  const bScore = bl.filter((i) => i.firstTry).length;
  const o1 = app.content.objectives.O1, o2 = app.content.objectives.O2;
  const missSounds = snd.filter((i) => !i.firstTry).map((i) => i.target);
  const missWords = bl.filter((i) => !i.firstTry).map((i) => i.target);
  // sounds inside missed words also need practice
  const fromWords = [];
  missWords.forEach((w) => (app.content.words[w] ? app.content.words[w].sounds : []).forEach((s) => { if (fromWords.indexOf(s) < 0) fromWords.push(s); }));
  return Object.assign(out, {
    final: true,
    O1: { score: sScore, of: snd.length, met: sScore >= o1.need },
    O2: { score: bScore, of: bl.length, met: bScore >= o2.need },
    missSounds, missWords, fromWords,
    lastDate: p.days[5] && p.days[5].date,
  });
}

/** Letters missed in any daily challenge so far (before Day 5). */
export function weakSounds() {
  const out = [];
  days().forEach((d) => {
    const r = progress.day(d.day);
    if (!r || !r.challenge) return;
    r.challenge.items.forEach((i) => {
      if (i.firstTry) return;
      const letters = i.type === 'sound' ? [i.target] : (app.content.words[i.target] || { sounds: [] }).sounds;
      letters.forEach((l) => { if (out.indexOf(l) < 0) out.push(l); });
    });
  });
  return out;
}
