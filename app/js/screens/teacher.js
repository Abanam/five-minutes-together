// Trusted apps, For teachers (guide, flyer, QR, WhatsApp, printable cards), reviewer checklist, settings.

import { h, frag } from '../util.js';
import { icon, family, picture, sanad, sticker } from '../art.js';
import { t, num, getLang, setLang, appVersion } from '../i18n.js';
import { app, T, liveUrl } from '../ctx.js';
import { settings, review, resetAll } from '../store.js';
import * as audio from '../audio.js';
import { go, render } from '../router.js';
import { parentGate } from '../gate.js';
import { btn, parentCard, letterTile, letterChip, levelBadge, toast, confirmBox, txt, en, richText } from '../ui.js';
import { topbar } from './parent.js';

const QR_SRC = 'img/qr-code.svg';
function qrImg(cls) {
  const src = (window.__FMT_EMBED__ && window.__FMT_EMBED__.qr) || QR_SRC;
  const img = h('img', { src, alt: t('qrAlt'), class: cls || 'qr', width: '240', height: '240', 'data-test': 'qr' });
  img.addEventListener('error', () => { img.replaceWith(h('p.small', { lang: 'en', dir: 'ltr' }, liveUrl())); });
  return img;
}

// ---------------------------------------------------------------- trusted apps (R3)
export function appsScreen(root) {
  const C = app.content;
  const list = h('div.stack.apps-list', { 'data-test': 'apps' });
  C.trustedApps.forEach((a) => {
    const isEn = getLang() === 'en';
    const open = btn(t('openSite'), { icon: 'link', cls: 'btn-primary btn-wide', test: 'open-site' });
    open.addEventListener('click', async () => {
      if (await parentGate()) window.open(a.url, '_blank', 'noopener,noreferrer');
    });
    list.append(h('article.app-card.stack', { 'data-test': 'app-card' },
      h('h3', { lang: 'en' }, a.name),
      parentCard('app_' + a.id + '_why', { label: t('whyHelps'), textOverride: a.why }),
      parentCard('app_' + a.id + '_ask', { label: t('askTip'), cls: 'ask', textOverride: a.ask }),
      h('p.small.muted', t('checkedOn', { d: a.checked })),
      open));
  });
  root.append(topbar('apps'), h('main.screen.stack', parentCard('apps_intro'), list));
}

// ---------------------------------------------------------------- for teachers (R5)
export function teachersScreen(root) {
  const link = liveUrl();
  const msg = T('teacher_whatsapp')[getLang() === 'en' ? 'en' : 'ar'].split('{link}').join(link || '');
  const ta = h('textarea', { readonly: true, rows: '10', 'aria-label': t('whatsapp'), 'data-test': 'wa-text', dir: getLang() === 'en' ? 'ltr' : 'rtl' });
  ta.value = msg;
  const copy = btn(t('copy'), { icon: 'copy', cls: 'btn-primary', test: 'wa-copy', onClick: () => copyText(msg) });
  const share = btn(t('share'), { icon: 'share', cls: 'btn-sand', test: 'wa-share', onClick: () => shareText(msg, link) });
  if (!navigator.share) share.hidden = true;
  const flyerCard = h('section.section-card.stack.flyer-preview', { 'data-test': 'flyer-preview' },
    h('h2', t('flyer')),
    h('div.center', qrImg('qr-preview'), h('p.small', { lang: 'en', dir: 'ltr' }, link)),
    h('div.grid2', btn(t('printFlyer'), { icon: 'print', cls: 'btn-primary', test: 'to-flyer', onClick: () => go('#/flyer') }),
      btn(t('printCards'), { icon: 'print', cls: 'btn-sand', test: 'to-cards', onClick: () => go('#/cards') })));
  root.append(topbar('teachers'), h('main.screen.stack', { 'data-test': 'teachers' },
    h('div.hero', { html: family('brother-girl'), role: 'img', 'aria-label': getLang() === 'ar' ? 'أخ كبير يساعد أخته' : 'An older brother helping his little sister' }),
    h('h2', t('guide')), parentCard('teacher_guide'),
    flyerCard,
    h('section.section-card.stack', h('h2', t('whatsapp')), ta, h('div.grid2', copy, share)),
    h('section.section-card.stack', h('h2', t('editContent')), parentCard('teacher_edit'),
      h('p.small', { lang: 'en', dir: 'ltr', style: { textAlign: 'left' } },
        'For developers: all learning content is in ', h('code', 'app/content.json'), ' (days, sounds, words, pictures and Arabic prompts). Words built from the six sounds work at once; Arabic text changes are read by the device voice until tools/make_audio_v11.py is run again. See README.md.'))));
}

async function copyText(text) {
  let ok = false;
  try { if (navigator.clipboard && navigator.clipboard.writeText) { await navigator.clipboard.writeText(text); ok = true; } } catch (e) { ok = false; }
  if (!ok) {
    const ta = h('textarea', { style: { position: 'fixed', top: '-1000px' } });
    ta.value = text; document.body.append(ta); ta.select();
    try { ok = document.execCommand('copy'); } catch (e) { ok = false; }
    ta.remove();
  }
  toast(ok ? t('copied') + ' ✓' : text.slice(0, 60) + '…');
  return ok;
}
async function shareText(text, url) {
  try { await navigator.share({ title: t('appName'), text, url: url || undefined }); } catch (e) { /* cancelled */ }
}

// ---------------------------------------------------------------- printable flyer (A4, Arabic)
export function flyerScreen(root) {
  const link = liveUrl();
  const page = h('article.print-page.flyer', { lang: 'ar', dir: 'rtl', 'data-test': 'flyer' },
    h('div.row', { style: { justifyContent: 'space-between', alignItems: 'flex-start' } },
      h('div', h('h1', 'خمس دقائق معًا'), h('p.tag', 'تطبيق مجاني لتعليم أطفال الصف الأول والثاني أصوات الحروف الإنجليزية في البيت')),
      h('div', { style: { width: '42mm', flex: 'none' }, html: sanad({ anim: false }) })),
    h('div.hero-print', { html: family('mother-boy') }),
    h('div.row', { style: { alignItems: 'flex-start' } },
      h('div', { style: { flex: '1' } },
        h('h2', { style: { fontSize: '18pt' } }, 'كيف نبدأ؟'),
        h('ol.steps-ol', h('li', 'امسح الرمز بكاميرا الهاتف، أو افتح الرابط.'), h('li', 'اجلس مع طفلك خمس دقائق كل يوم.'), h('li', 'التطبيق ينطق الأصوات، وأنت تشجّع وتسأل.'), h('li', 'بعد الجلسة: نشاط قصير في البيت دون شاشة.'))),
      h('div.center', { style: { width: '66mm', flex: 'none' } }, qrImg('qr'), h('p', { style: { fontSize: '10pt', direction: 'ltr', wordBreak: 'break-all' } }, link))),
    h('div.feat', { style: { marginTop: '6mm' } },
      h('div', '✔ مجاني، دون إعلانات، ودون حساب'), h('div', '✔ لا تحتاج إلى معرفة الإنجليزية'),
      h('div', '✔ يعمل دون إنترنت بعد فتحه أول مرة'), h('div', '✔ لا تغادر أي بيانات الهاتف')),
    h('p', { style: { fontSize: '11pt', marginTop: '6mm', color: '#4A5D66' } }, 'لا يوجد جهاز؟ اطلب من معلم اللغة الإنجليزية بطاقات الأيام الخمسة المطبوعة.'),
    h('p', { style: { fontSize: '9pt', color: '#4A5D66', direction: 'ltr', textAlign: 'left', position: 'absolute', bottom: '10mm', left: '14mm' } }, '5 Minutes Together · v' + appVersion() + ' · EDEN4233 prototype, Rustaq College of Education'));
  root.append(topbar('flyer'), h('main.screen',
    h('div.print-tools.no-print', btn(t('print'), { icon: 'print', cls: 'btn-primary', onClick: () => window.print() }), btn(t('back'), { icon: 'back', iconCls: 'flip-rtl', cls: 'btn-ghost', onClick: () => go('#/teachers') })),
    h('div.print-scroll', { tabindex: '0', role: 'region', 'aria-label': t('flyer') }, page)));
}

// ---------------------------------------------------------------- printable day cards (offline alternative, R4)
export function cardsScreen(root) {
  const C = app.content;
  const pages = C.days.map((d) => {
    const sounds = d.newSounds.length ? d.newSounds : d.reviewSounds;
    const words = Array.from(new Set(d.tapSay.map((x) => x.word).concat(d.blend)));
    const levelName = T(C.levels[d.level].name).ar;
    const step = (n2, title, body) => h('div.box', h('b', n2 + '. ' + title), h('p', Array.isArray(body) ? body : richText(body)));
    return h('article.print-page.dcard', { lang: 'ar', dir: 'rtl', 'data-test': 'day-card' },
      h('div.row', { style: { justifyContent: 'space-between' } },
        h('div', h('h1', 'خمس دقائق معًا — اليوم ' + num(d.day)), h('div', T(C.stops[d.stop].name).ar + ' – مستوى الدعم: ' + levelName)),
        h('div.head-sticker', { html: sticker(d.sticker) })),
      h('div.letters-big', { style: { margin: '2mm 0' } }, sounds.map((s) => letterTile(s, { size: sounds.length > 3 ? 'xs' : 'sm' }))),
      h('div.box', { style: { marginBottom: '3mm' } }, h('b', 'تذكير: '), richText(T('tip_general').ar)),
      d.hear.review
        // review day: six tips in two columns instead of the keyword pictures
        ? h('div.box', h('b', 'نطق الأصوات الستة'), h('div', { style: { columnCount: '2', columnGap: '6mm' } }, sounds.map((s) => h('p', letterChip(s), ' ', T(C.sounds[s].tip).ar))))
        : h('div.dc-grid',
          h('div.box', h('b', 'نطق أصوات اليوم'), sounds.map((s) => h('p', letterChip(s), ' ', T(C.sounds[s].tip).ar))),
          h('div.box', h('b', 'صور تبدأ بالصوت'), h('div.words', sounds.slice(0, 3).map((s) => C.sounds[s].keywords.map((k) => h('div.wd', h('div.pic-mini', { html: picture(C.keywords[k].picture) }), en(k))))))),
      h('div', { style: { margin: '3mm 0' } },
        step('١', 'اسمع', 'قل صوت كل حرف (وليس اسمه)، واطلب من طفلك أن يكرّره. أشيرا إلى الصور التي تبدأ بالصوت.'),
        step('٢', 'انقر وقل', ['أشر إلى كل حرف في الكلمة وقل صوته، ثم اجمع الأصوات بسرعة: ']
          .concat(...words.slice(0, 3).map((w, i) => [i ? '، ' : '', en(C.words[w].sounds.join('… ') + ' = ' + w)]))),
        step('٣', 'ادمج وحدك', 'دع طفلك يقرأ الكلمات وحده، وشجّعه: ' + words.join('، ')),
        step('٤', 'اسأل طفلك', d.tapSay.slice(0, 3).map((x) => T(x.ask).ar).join(' · '))),
      h('div.dc-grid',
        h('div.box', h('b', 'كلمات اليوم'), h('div.words', words.map((w) => h('div.wd', C.words[w].picture ? h('div.pic-mini', { html: picture(C.words[w].picture) }) : null, en(w))))),
        h('div.box', h('b', 'نشاط في البيت دون شاشة'), h('p', richText(T(d.home).ar)))),
      h('p', { style: { marginTop: '3mm' } }, h('span.tick'), 'أكملنا اليوم ' + num(d.day) + ' — التاريخ: ____________'),
      d.day === 5 ? h('div', h('b', 'بطاقات حروف للقص:'), h('div.cutout', ['s', 'a', 't', 'p', 'i', 'n'].map((l) => h('div', { class: 'L-' + l, style: { color: 'var(--ld)' } }, l)))) : null,
      h('p', { style: { fontSize: '9pt', color: '#4A5D66', position: 'absolute', bottom: '8mm', left: '14mm', direction: 'ltr' } }, '5 Minutes Together · v' + appVersion() + ' · ' + (liveUrl() || '')));
  });
  root.append(topbar('printCards'), h('main.screen',
    h('div.print-tools.no-print', btn(t('print'), { icon: 'print', cls: 'btn-primary', onClick: () => window.print() }), btn(t('back'), { icon: 'back', iconCls: 'flip-rtl', cls: 'btn-ghost', onClick: () => go('#/teachers') })),
    h('div.print-scroll', { tabindex: '0', role: 'region', 'aria-label': t('printCards') }, pages)));
}

// ---------------------------------------------------------------- reviewer checklist (nothing is sent)
const ITEMS = [
  ['clarity', 'Clarity for parents: the Arabic instructions are clear and easy to follow.', 'وضوح الإرشادات: التعليمات العربية واضحة وسهلة الاتباع لولي الأمر.'],
  ['ease', 'Ease for children: a 6–8-year-old can use the child screens without reading.', 'سهولة الاستخدام للطفل: يستطيع طفل من ٦ إلى ٨ سنوات استخدام شاشاته دون قراءة.'],
  ['culture', 'Cultural suitability: pictures, characters and wording suit Omani families.', 'الملاءمة الثقافية: الصور والشخصيات والكلمات مناسبة للأسر العُمانية.'],
  ['access', 'Accessibility: audio, large text, calm mode and contrast work for different users.', 'سهولة الوصول: الصوت والخط الكبير والوضع الهادئ والتباين تناسب مستخدمين مختلفين.'],
  ['learning', 'Learning value: the activities build letter–sound knowledge and blending.', 'القيمة التعليمية: الأنشطة تبني معرفة أصوات الحروف ودمجها.'],
  ['routine', 'Daily routine: one session fits into about five minutes.', 'الروتين اليومي: الجلسة الواحدة تناسب خمس دقائق تقريبًا.'],
  ['safety', 'Safety and privacy: the app feels safe for children (no ads, chat or data sharing).', 'الأمان والخصوصية: التطبيق آمن للأطفال (لا إعلانات ولا محادثة ولا مشاركة بيانات).'],
  ['technical', 'Technical problems: the app worked without errors on my device.', 'المشكلات التقنية: عمل التطبيق دون أخطاء على جهازي.'],
];

// v1.1: audio re-check block (shown below the eight items, which stay word for word)
const AUDIO_ITEMS = [
  ['A1', 'English sounds and words', 'English sounds and words: the letter sounds and words are clear and correctly pronounced.', 'الأصوات والكلمات الإنجليزية: أصوات الحروف والكلمات واضحة ومنطوقة نطقًا صحيحًا.'],
  ['A2', 'Arabic voice', 'Arabic voice: the Arabic instructions are clear, natural and easy to understand.', 'الصوت العربي: الإرشادات العربية واضحة وطبيعية وسهلة الفهم.'],
  ['A3', 'Pronunciation compared with version 1.0', 'Compared with version 1.0, the pronunciation is (1 = much worse, 3 = the same, 5 = much better).', 'مقارنة بالإصدار 1.0، النطق الآن (١ = أسوأ بكثير، ٣ = كما هو، ٥ = أفضل بكثير).'],
];

export function reviewScreen(root) {
  const version = appVersion();
  const data = review.get(version);   // answers are stored per version; a new version starts empty
  const save = () => review.set(version, data);
  const item = (id, number, enQ, arQ, scale) => {
    const name = 'r_' + id;
    const row = h('div.rate', { role: 'radiogroup', 'aria-label': enQ });
    for (let v = 1; v <= 5; v++) {
      const input = h('input', { type: 'radio', name, value: String(v), 'aria-label': `${v} / 5`, 'data-test': `rate-${id}-${v}` });
      if (data[id] && data[id].score === v) input.checked = true;
      const label = h('label', { class: data[id] && data[id].score === v ? 'on' : '' }, input, h('span', String(v)));
      input.addEventListener('change', () => {
        data[id] = Object.assign({}, data[id], { score: v }); save();
        row.querySelectorAll('label').forEach((l) => l.classList.remove('on')); label.classList.add('on');
      });
      row.append(label);
    }
    const ta = h('textarea', { rows: '2', placeholder: t('comment'), 'aria-label': t('comment') + ' – ' + enQ, 'data-test': `comment-${id}` });
    ta.value = (data[id] && data[id].comment) || '';
    ta.addEventListener('input', () => { data[id] = Object.assign({}, data[id], { comment: ta.value }); save(); });
    return h('div.review-item.stack', { 'data-test': 'review-item', 'data-item': id },
      h('p.q-en', { lang: 'en' }, number + '. ' + enQ), h('p.q-ar', { lang: 'ar' }, arQ),
      row, scale || h('div.rate-scale', h('span', '1 = ' + t('disagree')), h('span', '5 = ' + t('agree'))), ta);
  };
  const items = ITEMS.map(([id, enQ, arQ], k) => item(id, k + 1, enQ, arQ));
  const audioScale = h('div.rate-scale', h('span', getLang() === 'ar' ? '١ = أسوأ بكثير' : '1 = much worse'),
    h('span', getLang() === 'ar' ? '٣ = كما هو' : '3 = the same'), h('span', getLang() === 'ar' ? '٥ = أفضل بكثير' : '5 = much better'));
  const audioItems = AUDIO_ITEMS.map(([id, , enQ, arQ]) => item(id, id, enQ, arQ, id === 'A3' ? audioScale : null));
  const audioBlock = h('section.stack.audio-recheck', { 'data-test': 'audio-recheck' },
    h('h2', 'Audio re-check (v1.1) / مراجعة الأصوات (الإصدار 1.1)'), audioItems);
  const role = h('input', { type: 'text', placeholder: t('role'), 'aria-label': t('role'), 'data-test': 'review-role' });
  role.value = data.role || '';
  role.addEventListener('input', () => { data.role = role.value; save(); });
  const line = (label, d) => `${label}: ${d.score ? d.score + '/5' : '–'}${d.comment ? ' – ' + d.comment : ''}`;
  const summary = () => {
    const lines = [`5 Minutes Together v${version} – reviewer feedback / ملاحظات المراجع`, 'Date: ' + new Date().toISOString().slice(0, 10)];
    if (data.role) lines.push('Role: ' + data.role);
    ITEMS.forEach(([id, enQ], k) => lines.push(`${k + 1}. ` + line(enQ.split(':')[0], data[id] || {})));
    AUDIO_ITEMS.forEach(([id, label]) => lines.push(`${id}. ` + line(label, data[id] || {})));
    return lines.join('\n');
  };
  const copy = btn(t('copyFeedback'), { icon: 'copy', cls: 'btn-primary btn-wide', test: 'copy-feedback', onClick: () => { out.value = summary(); out.hidden = false; copyText(out.value); } });
  const share = btn(t('shareFeedback'), { icon: 'share', cls: 'btn-sand btn-wide', test: 'share-feedback', onClick: () => shareText(summary()) });
  if (!navigator.share) share.hidden = true;
  const out = h('textarea', { readonly: true, rows: '10', hidden: true, 'data-test': 'feedback-out', dir: 'ltr', 'aria-label': t('copyFeedback') });
  root.append(topbar('review'), h('main.screen.stack', { 'data-test': 'review' },
    parentCard('review_intro'), role, items, audioBlock, copy, share, out, h('p.small.muted.center', frag(icon('shield', 'inline')), t('nothingSent'))));
}

// ---------------------------------------------------------------- settings (behind the parent gate)
export function settingsScreen(root) {
  const s = settings.get();
  const sw = (key, label, test, onChange) => {
    const b = h('button.switch', { type: 'button', role: 'switch', 'aria-checked': String(!!s[key]), 'aria-label': label, 'data-test': test },
      h('span.sw-txt', { 'aria-hidden': 'true' }, s[key] ? t('on') : t('off')));
    b.addEventListener('click', () => {
      const v = b.getAttribute('aria-checked') !== 'true';
      settings.set({ [key]: v });
      b.setAttribute('aria-checked', String(v));
      b.firstChild.textContent = v ? t('on') : t('off');
      if (onChange) onChange(v);
    });
    return h('div.switch-row', h('span', label), b);
  };
  const langSeg = h('div.seg', { role: 'group', 'aria-label': t('language') },
    btn('العربية', { cls: 'lang-ar', test: 'set-ar', onClick: () => { setLang('ar'); render(); } }),
    btn('English', { cls: 'lang-en', test: 'set-en', onClick: () => { setLang('en'); render(); } }));
  langSeg.querySelector(getLang() === 'ar' ? '.lang-ar' : '.lang-en').setAttribute('aria-pressed', 'true');
  langSeg.querySelector(getLang() === 'ar' ? '.lang-en' : '.lang-ar').setAttribute('aria-pressed', 'false');
  root.append(topbar('settings'), h('main.screen.stack', { 'data-test': 'settings' },
    h('h2', t('language')), langSeg,
    sw('large', t('largeText'), 'sw-large', (v) => document.documentElement.classList.toggle('large', v)),
    sw('calm', t('calmMode'), 'sw-calm', (v) => document.documentElement.classList.toggle('calm', v)),
    sw('sfx', t('sounds'), 'sw-sfx', (v) => audio.setSfx(v)),
    sw('unlockAll', t('unlockAll'), 'sw-unlock'),
    btn(t('replayOnboarding'), { icon: 'retry', cls: 'btn-sand btn-wide', test: 'replay-onboarding', onClick: () => { settings.set({ onboarded: false }); go('#/onboarding/1'); } }),
    btn(t('reset'), {
      icon: 'trash', cls: 'btn-ghost btn-wide', test: 'reset',
      onClick: async () => { if (await confirmBox(t('resetConfirm'), t('yesReset'), t('cancel'))) { resetAll(appVersion()); toast(t('resetDone')); } },
    }),
    h('p.footer-note', t('version') + ' · ' + t('noData'))));
}
