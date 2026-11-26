// Shared run-time context (content.json, audio manifest, flags). Filled in by main.js.
export const app = {
  content: null,
  manifest: null,
  tour: false,
  gateUntil: 0,
};

/** A content text by id: { ar, en, say }. */
export function T(id) {
  return (app.content && app.content.texts[id]) || { ar: id, en: id };
}

/** Public link of the app: content.json meta.liveUrl, else the address it is served from. */
export function liveUrl() {
  const m = app.content && app.content.meta && app.content.meta.liveUrl;
  if (m) return m;
  if (/^https?:/.test(location.protocol)) return location.origin + location.pathname.replace(/index\.html$/, '');
  return '';
}
