// Studio page (local only): choose the voices, record the six letter sounds.
// Raw PCM is captured with an AudioWorklet (no echo cancellation, noise suppression or auto gain:
// noise suppression damages /s/) and sent as a 16-bit WAV to the local server, which checks it.
import { picture } from '/app/js/art.js';

const $ = (s, el = document) => el.querySelector(s);
function h(sel, attrs, ...kids) {
  const [tag, ...cls] = sel.split('.');
  const el = document.createElement(tag || 'div');
  if (cls.length) el.className = cls.join(' ');
  if (attrs != null && (typeof attrs !== 'object' || attrs instanceof Node || Array.isArray(attrs))) { kids.unshift(attrs); attrs = null; }
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v == null || v === false) continue;
    if (k.startsWith('on')) el.addEventListener(k.slice(2), v);
    else if (k === 'html') el.innerHTML = v;
    else el.setAttribute(k, v === true ? '' : v);
  }
  for (const k of kids.flat(Infinity)) if (k != null && k !== false) el.append(k instanceof Node ? k : String(k));
  return el;
}

let S = null;        // server state
let C = null;        // app content.json (keyword pictures)
let rec = null;      // the recording in progress
let player = null;

function play(url) {
  if (player) player.pause();
  player = new Audio(url + (url.includes('?') ? '&' : '?') + 't=' + Date.now());
  player.play().catch(() => {});
}

async function api(path, body) {
  const opt = body === undefined ? {} : { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) };
  const r = await fetch(path, opt);
  const j = await r.json().catch(() => ({ error: 'HTTP ' + r.status }));
  if (!r.ok || j.error) throw new Error(j.error || 'HTTP ' + r.status);
  return j;
}

function showError(panel, e) {
  $('#' + panel).prepend(h('p.err', null, 'حدث خطأ: ', h('span', { lang: 'en', dir: 'ltr' }, String((e && e.message) || e))));
}

// ------------------------------------------------------------------ tabs
function showTab(name) {
  for (const t of ['voices', 'record']) {
    $('#tab-' + t).setAttribute('aria-selected', String(t === name));
    $('#' + t).hidden = t !== name;
  }
  try { history.replaceState(null, '', '#' + name); } catch (e) { /* ignore */ }
}
$('#tab-voices').addEventListener('click', () => showTab('voices'));
$('#tab-record').addEventListener('click', () => showTab('record'));

// ------------------------------------------------------------------ Voices tab
function englishCard() {
  const en = S.english;
  const card = h('section.card', null,
    h('h2', null, 'الصوت الإنجليزي ', h('span.en', { lang: 'en', dir: 'ltr' }, 'English voice: the 27 words and Sanad’s 14 phrases')));
  if (!en) { card.append(h('p.hint', null, 'لم تُصنع تجربة الأصوات الإنجليزية بعد.')); return card; }
  card.append(h('p.hint', null, 'هذه هي الكلمات الخمس التي أخطأ فيها الإصدار 1.0. استمع إليها بكل صوت، ثم اختر صوتًا واحدًا. علامة ✓ تعني أن برنامج Whisper سمع الكلمة الصحيحة وأن بدايتها نظيفة.'));
  const grid = h('div.voice-grid');
  for (const v of en.voices) {
    const chosen = en.chosen === v.voice_id;
    grid.append(h('article.voice' + (chosen ? '.is-chosen' : ''), null,
      h('div', null, h('span.name', { lang: 'en' }, v.name), ' ', en.recommended === v.voice_id ? h('span.badge.rec', null, 'التوصية') : null),
      h('div.about', { lang: 'en' }, v.about),
      h('div.score', { dir: 'ltr', lang: 'en' }, `Whisper: ${v.score}/${v.clips.length}`),
      h('div.words', null, v.clips.map((c) => {
        const good = c.match && c.onset_ok;
        return h('div.word', null,
          h('button', { type: 'button', lang: 'en', 'aria-label': `Play “${c.word}” (${v.name})`, onclick: () => play(c.url) }, '▶ ' + c.word),
          h('span.heard', { lang: 'en' }, '“' + c.heard + '”'),
          h('span.mark.' + (good ? 'ok' : 'bad'), { title: good ? '' : (!c.match ? 'Whisper heard another word' : 'unclean onset') }, good ? '✓' : '✗'));
      })),
      h('button.choose', { type: 'button', onclick: () => act('voices', () => api('/api/english', { voice_id: v.voice_id })) },
        chosen ? '✓ تم الاختيار' : 'اختر هذا الصوت')));
  }
  card.append(grid);
  if (en.chosen) card.append(h('p.status.ok', null, 'تم حفظ اختيار الصوت الإنجليزي.'));
  return card;
}

function arabicCard() {
  const ar = S.arabic;
  const job = S.job || {};
  const card = h('section.card', null,
    h('h2', null, 'الصوت العربي ', h('span.en', { lang: 'en', dir: 'ltr' }, 'Arabic voice: the instructions for parents (Voice Design)')));
  if (!ar || (!ar.previews && ar.mode !== 'website')) { card.append(h('p.hint', null, 'لم تُصنع نماذج الصوت العربي بعد.')); return card; }
  if (ar.mode === 'website') card.append(...websiteSteps(ar, job));
  else {
    card.append(h('p.hint', null, 'صنعت أداة Voice Design ثلاثة نماذج من الوصف نفسه، وكلها تقرأ هذا النص. استمع إليها، واختر الأقرب إلى معلّمة عُمانية دافئة وواضحة.'));
    card.append(h('div.ar-text', null, ar.preview_text));
    const grid = h('div.previews');
    for (const p of ar.previews) {
      const chosen = ar.chosen_preview === p.n;
      grid.append(h('article.voice' + (chosen ? '.is-chosen' : ''), null,
        h('strong', null, 'النموذج ' + p.n),
        h('button.play', { type: 'button', onclick: () => play(p.url) }, '▶ استمع'),
        h('button.choose', { type: 'button', disabled: job.state === 'running', onclick: () => act('voices', () => api('/api/arabic', { preview: p.n })) },
          chosen ? '✓ تم الاختيار' : 'اختر هذا الصوت')));
    }
    card.append(grid);
  }
  if (job.state === 'running') card.append(h('p.status.busy', null, 'جارٍ حفظ الصوت وصنع جملتين حقيقيتين من التطبيق به…'));
  if (job.state === 'error') card.append(h('p.status.bad', null, 'حدث خطأ: ', h('span', { lang: 'en', dir: 'ltr' }, job.error)));
  if (ar.lines && job.state !== 'running') {
    card.append(h('h3', null, 'جملتان من التطبيق بالصوت المختار'));
    card.append(h('div.lines', null, ar.lines.map((l) => h('div.line', null,
      h('div.ar-text', null, l.text),
      h('button.play', { type: 'button', onclick: () => play(l.url) }, '▶ استمع'), ' ',
      h('span.small', null, 'المدة ', h('bdi', null, String(l.report.seconds)), ' ثانية')))));
    card.append(ar.approved
      ? h('p.status.ok', null, '✓ تمت الموافقة على الصوت العربي.')
      : h('button.approve', { type: 'button', onclick: () => act('voices', () => api('/api/arabic-approve', { ok: true })) }, 'أوافق على هذا الصوت العربي'));
  }
  card.append(h('p.small', null, ar.mode === 'website'
    ? 'إن لم يبدُ أيّ نموذج خليجيًا أو عُمانيًا، أو أردت صوت رجل، فيُسمح بجولة تصميم واحدة أخرى في الموقع (يمكن فيها اختيار نموذج v3). يُختبر الصوت بعدها بالجملتين التجريبيتين بنموذج Multilingual v2.'
    : 'إن لم يبدُ أيّ نموذج خليجيًا أو عُمانيًا، أو أردت صوت رجل، فاكتب ذلك لـ Claude في المحادثة؛ يُسمح بجولة تصميم واحدة أخرى.'));
  return card;
}

function copyBox(text, label, dir) {
  const box = h('div.ar-text', { dir, lang: dir === 'ltr' ? 'en' : 'ar' }, text);
  const btn = h('button.choose', { type: 'button' }, label);
  btn.addEventListener('click', async () => {
    try { await navigator.clipboard.writeText(text); btn.textContent = '✓ تم النسخ'; } catch (e) {
      const r = document.createRange(); r.selectNodeContents(box); const s = getSelection(); s.removeAllRanges(); s.addRange(r);
    }
  });
  return h('div.copy', null, box, btn);
}

// Brief §5 fallback: the free plan refuses Voice Design through the API, so the voice is made on the website.
function websiteSteps(ar, job) {
  const en = (t) => h('bdi', { lang: 'en', dir: 'ltr' }, t);
  const input = h('input', { type: 'text', id: 'voice-id', dir: 'ltr', lang: 'en', placeholder: 'voice ID', value: ar.voice_id || '', 'aria-label': 'Voice ID',
    style: 'font:inherit;padding:6px 10px;border:2px solid var(--line);border-radius:10px;min-width:260px' });
  const go = h('button.approve', { type: 'button', disabled: job.state === 'running' }, 'تحقّق من الصوت واصنع جملتين تجريبيتين');
  go.addEventListener('click', () => act('voices', () => api('/api/arabic-voice', { voice_id: input.value.trim() })));
  return [
    h('p.hint', null, 'لا تسمح الخطة المجانية بإنشاء صوت عبر الـ API، لذلك يُصنع الصوت في موقع ElevenLabs بالوصف والنص نفسيهما:'),
    h('ol', null,
      h('li', null, 'افتح ', en('elevenlabs.io'), ' وسجّل الدخول.'),
      h('li', null, 'اذهب إلى ', en('Voices → My Voices → Add a new voice → Voice Design'), '.'),
      h('li', null, 'انسخ الوصف الإنجليزي أدناه، والصقه في خانة الوصف.'),
      h('li', null, 'انسخ النص العربي أدناه، والصقه في خانة النص بدل النص التلقائي.'),
      h('li', null, 'اضغط ', en('Generate'), '، واستمع إلى النماذج الثلاثة، واختر الأقرب إلى معلّمة عُمانية دافئة وواضحة. (يخصم الموقع نحو 168 رصيدًا.)'),
      h('li', null, 'احفظ الصوت باسم: ', en(ar.voice_name || 'Five Minutes Together – Omani teacher (Arabic)')),
      h('li', null, 'في ', en('My Voices'), ' افتح قائمة الصوت واختر ', en('Copy voice ID'), '، ثم الصقه في الخانة أدناه.')),
    copyBox(ar.description, 'انسخ الوصف', 'ltr'),
    copyBox(ar.preview_text, 'انسخ النص', 'rtl'),
    h('div.controls', null, input, go),
  ];
}

// The six letter sounds from ElevenLabs (the team's recordings were not good enough). Every candidate listed
// passed check_phoneme with the unchanged RULES; the recommended one is used unless another is chosen here.
function lettersCard() {
  const L = S.letters;
  const card = h('section.card', null,
    h('h2', null, 'أصوات الحروف ', h('span.en', { lang: 'en', dir: 'ltr' }, 'Letter sounds: ElevenLabs candidates that passed the checks')));
  if (!L) { card.append(h('p.hint', null, 'لم تُصنع مرشّحات أصوات الحروف بعد.')); return card; }
  card.append(h('p.hint', null, 'كل صوت هنا اجتاز الفحص الصوتي نفسه (صوت نقي، لا اسم الحرف ولا حركة بعده). المختار الآن هو توصيتي. استمع، وإن كان غيره أوضح فاضغط «اختر» بجانبه.'));
  const grid = h('div.letters');
  for (const [letter, info] of Object.entries(L)) {
    const rows = info.candidates.filter((c) => c.ok).slice(0, 6);
    grid.append(h('article.letter-box' + (info.chosen != null ? '.done' : ''), null,
      h('div.rec-head', null, h('span.letter', { lang: 'en' }, letter), h('span.ipa', { lang: 'en' }, '/' + C.sounds[letter].ipa + '/')),
      rows.length ? h('ol.cands', null, rows.map((c) => {
        const isChosen = info.chosen === c.n;
        const src = c.kind === 'prompt' ? `“${c.text}”` : `cut from “${c.text}”`;
        return h('li.cand' + (isChosen ? '.is-chosen' : ''), null,
          h('button.play', { type: 'button', 'aria-label': `Play /${letter}/ candidate ${c.n}`, onclick: () => play(c.url) }, '▶'),
          h('span.small', { lang: 'en', dir: 'ltr' }, `${c.voice} · ${src} · ${c.how} · ${c.measures.duration.toFixed(2)} s`),
          c.recommended ? h('span.badge.rec', null, 'التوصية') : h('span'),
          h('button.use', { type: 'button', onclick: () => act('voices', () => api('/api/letter', { letter, n: c.n })) }, isChosen ? '✓ المختار' : 'اختر'));
      })) : h('p.err', null, 'لا يوجد مرشّح اجتاز الفحص.')));
  }
  card.append(grid);
  return card;
}

function renderVoices() {
  const root = $('#voices');
  root.textContent = '';
  root.append(englishCard(), arabicCard(), lettersCard());
}

async function act(panel, fn) {
  try { S = await fn(); } catch (e) { showError(panel, e); return; }
  render();
}

// ------------------------------------------------------------------ Record tab
function takeRow(it, t, chosen) {
  const isChosen = !!chosen && chosen.take === t.take;
  return h('li.take.' + (t.ok ? 'ok' : 'bad') + (isChosen ? '.is-chosen' : ''), null,
    h('button.play', { type: 'button', disabled: !t.url, onclick: () => play(t.url) }, '▶ التسجيل ' + t.take),
    h('span.mark.' + (t.ok ? 'ok' : 'bad'), null, t.ok ? '✓' : '✗'),
    t.ok ? h('button.use', { type: 'button', onclick: () => act('record', () => api('/api/use', { item: it.item, take: t.take })) },
      isChosen ? '✓ المختار' : 'استخدم هذا التسجيل') : h('span'),
    t.messages && t.messages.length ? h('ul.msgs', null, t.messages.map((m) => h('li', null, m))) : null);
}

function recCard(it) {
  const chosen = S.chosen[it.item];
  const takes = S.takes[it.item] || [];
  const card = h('article.rec-card' + (chosen ? '.done' : ''), { id: 'card-' + it.item });
  if (it.kind === 'phoneme') {
    card.append(h('div.rec-head', null,
      h('span.letter', { lang: 'en' }, it.letter),
      h('span.ipa', { lang: 'en' }, '/' + it.ipa + '/'),
      h('div.pics', null, it.keywords.map((w) => h('button.pic', { type: 'button', title: w, 'aria-label': w, onclick: () => play('/app/audio/en/w-' + w + '.mp3') },
        h('div', { html: picture(C.keywords[w].picture) }), h('span', { lang: 'en' }, w))))));
    // exact text from the brief; Latin words are isolated (<bdi>) so the mixed Arabic/English line reads in order
    card.append(h('p.coach', null, S.texts.coach[it.letter].split(/([A-Za-z]+)/).map((p, i) => (i % 2 ? h('bdi', { lang: 'en' }, p) : p))));
  } else if (it.kind === 'word') {
    card.append(h('div.rec-head', null, h('span.letter', { lang: 'en' }, it.word)));
    card.append(h('p.coach', null, 'قل الكلمة الإنجليزية مرة واحدة بوضوح: ', h('bdi', { lang: 'en' }, it.word)));
  }
  const btn = h('button.rec-btn', { type: 'button' }, '● سجّل');
  const meter = h('div.meter', { 'aria-hidden': 'true' }, h('i'));
  const timer = h('span.timer', null, '');
  btn.addEventListener('click', () => toggle(it, btn, meter, timer, card));
  card.append(h('div.controls', null, btn, meter, timer));
  if (takes.length) card.append(h('ol.takes', null, takes.map((t) => takeRow(it, t, chosen))));
  else card.append(h('p.small', null, 'يمكنك تسجيل حتى ' + S.max_takes + ' محاولات لكل صوت.'));
  return card;
}

function renderRecord() {
  if (rec) return; // never rebuild the cards while a take is being recorded
  const root = $('#record');
  root.textContent = '';
  const done = S.items.filter((i) => S.chosen[i.item]).length;
  root.append(h('p.small', null, 'أصوات الحروف تُصنع الآن بـ ElevenLabs، واختيارها في تبويب «الأصوات». هذا التبويب احتياطي فقط.'));
  root.append(h('p.note', null, S.texts.note));
  root.append(h('p.progress', null, 'تم اختيار ', h('bdi', null, `${done}/${S.items.length}`), done === S.items.length ? ' ✓' : ''));
  root.append(h('div.rec-grid', null, S.items.map(recCard)));
}

function encodeWav(chunks, sr) {
  const n = chunks.reduce((a, c) => a + c.length, 0);
  const buf = new ArrayBuffer(44 + n * 2);
  const v = new DataView(buf);
  const w = (o, s) => { for (let i = 0; i < s.length; i++) v.setUint8(o + i, s.charCodeAt(i)); };
  w(0, 'RIFF'); v.setUint32(4, 36 + n * 2, true); w(8, 'WAVE'); w(12, 'fmt ');
  v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true); v.setUint32(24, sr, true);
  v.setUint32(28, sr * 2, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true); w(36, 'data'); v.setUint32(40, n * 2, true);
  let o = 44;
  for (const c of chunks) {
    for (let i = 0; i < c.length; i++) {
      const s = Math.max(-1, Math.min(1, c[i]));
      v.setInt16(o, s < 0 ? s * 0x8000 : s * 0x7fff, true);
      o += 2;
    }
  }
  return new Blob([buf], { type: 'audio/wav' });
}

async function startCapture(item, onLevel, onTime) {
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false, channelCount: 1 },
  });
  const ctx = new AudioContext();
  await ctx.audioWorklet.addModule('/studio/recorder-worklet.js');
  const src = ctx.createMediaStreamSource(stream);
  const node = new AudioWorkletNode(ctx, 'pcm-capture');
  const sink = ctx.createGain();
  sink.gain.value = 0;                       // no monitoring through the speakers
  const chunks = [];
  const t0 = performance.now();
  node.port.onmessage = (e) => {
    const c = e.data;
    chunks.push(c);
    let s = 0;
    for (let i = 0; i < c.length; i++) s += c[i] * c[i];
    onLevel(Math.sqrt(s / c.length));
    onTime((performance.now() - t0) / 1000);
  };
  src.connect(node); node.connect(sink); sink.connect(ctx.destination);
  const track = stream.getAudioTracks()[0];
  const st = track && track.getSettings ? track.getSettings() : {};
  return {
    item,
    mic: { echoCancellation: st.echoCancellation, noiseSuppression: st.noiseSuppression, autoGainControl: st.autoGainControl,
      channelCount: st.channelCount, sampleRate: ctx.sampleRate },
    async stop() {
      try { src.disconnect(); node.disconnect(); } catch (e) { /* ignore */ }
      stream.getTracks().forEach((t) => t.stop());
      const sr = ctx.sampleRate;
      await ctx.close();
      return encodeWav(chunks, sr);
    },
  };
}

async function toggle(it, btn, meter, timer, card) {
  if (rec) { if (rec.item === it.item) await finish(); return; }
  try {
    rec = await startCapture(it.item,
      (lvl) => { meter.firstChild.style.width = Math.min(100, lvl * 300) + '%'; },
      (sec) => { timer.textContent = sec.toFixed(1) + ' s'; });
  } catch (e) {
    rec = null;
    card.append(h('p.err', null, 'لم يُسمح للصفحة باستخدام الميكروفون. اسمح به من شريط العنوان، ثم أعد المحاولة.'));
    return;
  }
  Object.assign(rec, { btn, card, meter, auto: setTimeout(finish, 6000) });
  btn.textContent = '■ أوقف';
  btn.classList.add('on');
}

async function finish() {
  const r = rec;
  if (!r) return;
  clearTimeout(r.auto);
  r.btn.disabled = true;
  r.btn.textContent = 'جارٍ الفحص…';
  r.meter.firstChild.style.width = '0';
  const wav = await r.stop();
  rec = null;
  try {
    const res = await fetch('/api/take?item=' + encodeURIComponent(r.item) + '&mic=' + encodeURIComponent(JSON.stringify(r.mic)),
      { method: 'POST', headers: { 'Content-Type': 'audio/wav' }, body: wav });
    const j = await res.json();
    if (!res.ok || j.error) throw new Error(j.error || 'HTTP ' + res.status);
    S = await api('/api/state');
    renderRecord();
    if (j.url) play(j.url);                  // play back the processed take
  } catch (e) {
    r.btn.disabled = false;
    r.btn.textContent = '● سجّل';
    r.btn.classList.remove('on');
    r.card.append(h('p.err', null, 'تعذّر فحص التسجيل: ', h('span', { lang: 'en', dir: 'ltr' }, String(e.message || e))));
  }
}

// ------------------------------------------------------------------ start
function render() { renderVoices(); renderRecord(); }

async function init() {
  C = await (await fetch('/app/content.json')).json();
  S = await api('/api/state');
  render();
  showTab(location.hash === '#record' ? 'record' : 'voices');
  setInterval(async () => {
    if (S && S.job && S.job.state === 'running' && !rec) {
      try { S = await api('/api/state'); render(); } catch (e) { /* retry next time */ }
    }
  }, 2500);
}
init().catch((e) => document.body.append(h('p.err', null, String(e))));
