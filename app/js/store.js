// localStorage only, namespaced keys. Nothing ever leaves the device.
// If storage is blocked (private mode, file:// in some browsers) we keep state in memory.

import { today } from './util.js';

const NS = 'fmt1.';
const mem = {};

function get(key, fallback) {
  try {
    const v = localStorage.getItem(NS + key);
    return v === null ? fallback : JSON.parse(v);
  } catch (e) {
    return key in mem ? mem[key] : fallback;
  }
}
function set(key, value) {
  mem[key] = value;
  try { localStorage.setItem(NS + key, JSON.stringify(value)); } catch (e) { /* in-memory only */ }
}
function del(key) {
  delete mem[key];
  try { localStorage.removeItem(NS + key); } catch (e) { /* ignore */ }
}

export const settings = {
  get() {
    const s = get('settings', {});
    return {
      lang: s.lang || 'ar',
      large: !!s.large,
      calm: s.calm === undefined || s.calm === null ? null : !!s.calm, // null = follow the device's reduced-motion setting
      sfx: s.sfx !== false,
      unlockAll: !!s.unlockAll,
      onboarded: !!s.onboarded,
    };
  },
  set(patch) { set('settings', Object.assign(this.get(), patch)); },
};

export const progress = {
  get() { return get('progress', { days: {} }); },
  save(p) { set('progress', p); },
  day(n) { return this.get().days[n] || null; },
  /** Record a finished session. */
  complete(n, data) {
    const p = this.get();
    const prev = p.days[n] || {};
    p.days[n] = Object.assign({}, prev, data, {
      done: true,
      firstDate: prev.firstDate || today(),
      date: today(),
      plays: (prev.plays || 0) + 1,
    });
    p.last = n;
    this.save(p);
    return p.days[n];
  },
  reset() { del('progress'); },
};

// Reviewer checklist answers are stored per app version ("review.1.1"), so a new version starts
// empty. (v1.0 stored its answers under "review"; they are kept but no longer shown.)
export const review = {
  get(version) { return get('review.' + version, {}); },
  set(version, v) { set('review.' + version, v); },
};

/** The version the device last ran, or null on a device that never ran the app. */
export const appState = {
  seenVersion() { return get('seenVersion', null); },
  setSeenVersion(v) { set('seenVersion', v); },
  /** True if this device has data from a version before seenVersion existed (v1.0). */
  hasOldData() {
    try {
      return ['settings', 'progress', 'review'].some((k) => localStorage.getItem(NS + k) !== null);
    } catch (e) { return false; }
  },
};

export function resetAll(version) {
  progress.reset();
  if (version) review.set(version, {});
}
