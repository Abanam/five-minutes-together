// UI strings (buttons, labels). Learning content and parent instructions live in content.json.

import { settings } from './store.js';
import { arDigits } from './util.js';
import { app } from './ctx.js';

const S = {
  appName: ['خمس دقائق معًا', '5 Minutes Together'],
  version: ['الإصدار ⁦{v}⁩', 'Version {v}'],  // {v} = content.json meta.version
  forParent: ['لولي الأمر', 'For the parent'],
  listen: ['استمع', 'Listen'],
  listenAr: ['استمع إلى الإرشاد بالعربية', 'Play the Arabic audio'],
  readyOffline: ['جاهز دون إنترنت', 'Ready offline'],
  langToggle: ['English', 'العربية'],
  langToggleLabel: ['Switch to English', 'التبديل إلى العربية'],
  next: ['التالي', 'Next'],
  back: ['رجوع', 'Back'],
  home: ['الصفحة الرئيسية', 'Home'],
  exit: ['خروج إلى صفحة ولي الأمر', 'Exit to the parent page'],
  skip: ['تخطَّ', 'Skip'],
  start: ['ابدأ', 'Start'],
  startToday: ['ابدأ جلسة اليوم', "Start today's session"],
  repeatDay: ['أعِد اليوم', 'Repeat the day'],
  day: ['اليوم', 'Day'],
  dayN: ['اليوم {n}', 'Day {n}'],
  todayStop: ['محطة اليوم', "Today's stop"],
  level: ['مستوى الدعم', 'Support level'],
  progress5: ['تقدّم الأيام الخمسة', 'Five-day progress'],
  latest: ['آخر النتائج', 'Latest results'],
  noResults: ['لا توجد نتائج بعد. ابدأ اليوم الأول.', 'No results yet. Start Day 1.'],
  lastSession: ['آخر جلسة: اليوم {n}، تحدّي سند {s} من {t}', "Last session: Day {n}, Sanad's challenge {s} of {t}"],
  // links
  howto: ['كيف أستخدم التطبيق', 'How to use'],
  tips: ['نطق الأصوات', 'Pronunciation tips'],
  apps: ['تطبيقات موثوقة', 'Trusted apps'],
  teachers: ['للمعلمين', 'For teachers'],
  settings: ['الإعدادات', 'Settings'],
  results: ['النتائج', 'Results'],
  stickers: ['دفتر الملصقات', 'Sticker book'],
  about: ['عن التطبيق والخصوصية', 'About and privacy'],
  review: ['قائمة المراجعين', 'Reviewer checklist'],
  tour: ['Assessor tour / جولة للمقيّم', 'Assessor tour / جولة للمقيّم'],
  map: ['خريطة الرحلة', 'Journey map'],
  // steps
  st_start: ['البداية', 'Start'],
  st_hear: ['اسمع', 'Hear it'],
  st_tapsay: ['انقر وقل', 'Tap and say'],
  st_blend: ['ادمج وحدك', 'Blend on your own'],
  st_challenge: ['تحدّي سند', "Sanad's challenge"],
  st_final: ['الفحص النهائي', 'Final check'],
  st_done: ['الملصق', 'Sticker'],
  // session
  tapLetter: ['استمع إلى صوت {x}', 'Hear the sound {x}'],
  tapPicture: ['{w}: استمع', '{w}: listen'],
  hint: ['تلميح', 'Hint'],
  hintLabel: ['تلميح: استمع إلى الأصوات مرة أخرى', 'Hint: hear the sounds again'],
  train: ['قطار الأصوات', 'Sound train'],
  trainLabel: ['قطار الأصوات: اجمع الأصوات في كلمة', 'Sound train: join the sounds into a word'],
  saidRight: ['قالها صح', 'Said it right'],
  tryAgain: ['نحاول مرة ثانية', "Let's try again"],
  showMe: ['أرني الكلمة', 'Show me the word'],
  nextWord: ['الكلمة التالية', 'Next word'],
  replay: ['أعِد الصوت', 'Play the sound again'],
  howToSay: ['كيف أنطق الصوت؟', 'How do I say it?'],
  stickerFor: ['ملصق اليوم: {x}', "Today's sticker: {x}"],
  seeTomorrow: ['نراك غدًا!', 'See you tomorrow!'],
  homeActivity: ['نشاط في البيت دون شاشة', 'Home activity, no screen'],
  done: ['انتهينا', 'Finish'],
  seeResults: ['اعرض النتائج', 'See the results'],
  sessionOver: ['انتهت جلسة اليوم. أطفئا الشاشة.', "Today's session is over. Switch off the screen."],
  locked: ['مغلق حتى الغد', 'Locked until tomorrow'],
  doneDay: ['مكتمل', 'Completed'],
  todayDay: ['اليوم', 'Today'],
  openDay: ['متاح', 'Open'],
  chooseLetter: ['اختر الحرف', 'Choose the letter'],
  choosePicture: ['اختر الصورة', 'Choose the picture'],
  itemOf: ['السؤال {n} من {t}', 'Question {n} of {t}'],
  findIt: ['ابحث عن الصوت', 'Find the sound'],
  wordMeaning: ['معنى الكلمة: {x}', 'Meaning: {x}'],
  allSix: ['الأصوات الستة', 'All six sounds'],
  // gate
  gateTitle: ['لولي الأمر فقط', 'For parents only'],
  gateHold: ['اضغط مع الاستمرار', 'Press and hold'],
  gateCancel: ['إلغاء', 'Cancel'],
  gateKbd: ['يمكنك أيضًا الضغط على مفتاح المسافة مع الاستمرار.', 'You can also hold the Space key.'],
  // results
  objectives: ['الأهداف', 'Objectives'],
  met: ['تحقق', 'Met'],
  notMet: ['لم يتحقق بعد', 'Not met yet'],
  pending: ['بعد اليوم الخامس', 'After Day 5'],
  sessions: ['الجلسات المكتملة', 'Sessions completed'],
  practise: ['تدرّبا على', 'Practise'],
  challengeScore: ['تحدّي سند', "Sanad's challenge"],
  blendScore: ['قالها صح من أول مرة', 'Said right first time'],
  ofN: ['{s} من {t}', '{s} of {t}'],
  soundsKnown: ['الأصوات: {s} من ٦', 'Sounds: {s} of 6'],
  wordsBlended: ['الكلمات: {s} من ١٠', 'Words: {s} of 10'],
  repeatDayN: ['أعِد اليوم {n}', 'Repeat Day {n}'],
  // settings
  language: ['اللغة', 'Language'],
  arabic: ['العربية', 'العربية (Arabic)'],
  english: ['English', 'English'],
  largeText: ['خط كبير', 'Large text'],
  calmMode: ['الوضع الهادئ (حركة أقل)', 'Calm mode (less motion)'],
  sounds: ['أصوات النقر والمكافأة', 'Tap and reward sounds'],
  unlockAll: ['فتح كل الأيام (للمعلم والمقيّم)', 'Unlock all days (teacher / assessor)'],
  replayOnboarding: ['أعِد شاشات الترحيب', 'Show the welcome screens again'],
  reset: ['مسح التقدّم', 'Reset progress'],
  resetConfirm: ['هل تريد مسح كل التقدّم والملصقات في هذا الجهاز؟ لا يمكن التراجع.', 'Erase all progress and stickers on this device? This cannot be undone.'],
  yesReset: ['نعم، امسح', 'Yes, erase'],
  cancel: ['إلغاء', 'Cancel'],
  resetDone: ['تم مسح التقدّم.', 'Progress erased.'],
  on: ['نعم', 'On'],
  off: ['لا', 'Off'],
  // teacher
  guide: ['دليل المعلم في دقيقة', 'One-minute teacher guide'],
  flyer: ['نشرة للأسر (A4)', 'Family flyer (A4)'],
  printFlyer: ['اطبع النشرة', 'Print the flyer'],
  printCards: ['اطبع بطاقات الأيام الخمسة', 'Print the cards for the five days'],
  print: ['اطبع', 'Print'],
  whatsapp: ['رسالة واتساب جاهزة', 'Ready WhatsApp message'],
  copy: ['انسخ', 'Copy'],
  copied: ['تم النسخ', 'Copied'],
  share: ['شارك', 'Share'],
  editContent: ['تغيير الحروف والكلمات', 'Changing letters and words'],
  qrAlt: ['رمز QR لرابط التطبيق', 'QR code for the app link'],
  scanQR: ['امسح الرمز بكاميرا الهاتف', 'Scan the code with the phone camera'],
  // apps
  openSite: ['افتح الموقع', 'Open the website'],
  whyHelps: ['لماذا يفيد؟', 'Why it helps'],
  askTip: ['اسأل طفلك', 'Ask your child'],
  checkedOn: ['تحقّقنا من موقعه الرسمي في {d}', 'Checked on its official website on {d}'],
  // review
  reviewIntro: ['قيّم كل عبارة من ١ إلى ٥، واكتب ملاحظة إن أردت. لا يُرسل أي شيء؛ انسخ ملاحظاتك وشاركها بنفسك.', 'Rate each statement from 1 to 5 and add a comment if you like. Nothing is sent: copy your feedback and share it yourself.'],
  disagree: ['لا أوافق بشدة', 'Strongly disagree'],
  agree: ['أوافق بشدة', 'Strongly agree'],
  comment: ['ملاحظة', 'Comment'],
  role: ['دورك (اختياري): معلم، ولي أمر، زميل…', 'Your role (optional): teacher, parent, peer…'],
  copyFeedback: ['انسخ ملاحظاتي', 'Copy my feedback'],
  shareFeedback: ['شارك ملاحظاتي', 'Share my feedback'],
  nothingSent: ['لا يُرسل أي شيء من هذا الجهاز.', 'Nothing is sent from this device.'],
  // about
  purpose: ['الهدف من التطبيق', 'Purpose'],
  privacy: ['الخصوصية', 'Privacy'],
  credits: ['الحقوق والمصادر', 'Credits'],
  aiNote: ['ملاحظة عن الذكاء الاصطناعي', 'AI assistance'],
  learningObjectives: ['أهداف التعلّم', 'Learning objectives'],
  noData: ['لا تغادر أي بيانات هذا الجهاز', 'No data leaves this device'],
  // onboarding
  welcome: ['مرحبًا', 'Welcome'],
  getStarted: ['هيا نبدأ', "Let's begin"],
  stepOf: ['{n} من ٣', '{n} of 3'],
};

let lang = 'ar';
export function getLang() { return lang; }
export function setLang(l) {
  lang = l === 'en' ? 'en' : 'ar';
  document.documentElement.lang = lang;
  document.documentElement.dir = lang === 'ar' ? 'rtl' : 'ltr';
  settings.set({ lang });
}
export function initLang() { setLang(settings.get().lang); }

/** UI string with {placeholders}; numbers are shown in Arabic-Indic digits in Arabic. */
export function t(key, vars) {
  const pair = S[key];
  let s = pair ? pair[lang === 'ar' ? 0 : 1] : key;
  if (s.indexOf('{v}') >= 0 && !(vars && 'v' in vars)) s = s.split('{v}').join(appVersion());
  if (vars) {
    for (const k of Object.keys(vars)) {
      const v = typeof vars[k] === 'number' && lang === 'ar' ? arDigits(vars[k]) : vars[k];
      s = s.split('{' + k + '}').join(v);
    }
  }
  return s;
}
export function num(n) { return lang === 'ar' ? arDigits(n) : String(n); }
/** The app version, read from content.json (meta.version) – never hard-coded. */
export function appVersion() { return (app.content && app.content.meta && app.content.meta.version) || ''; }
/** Separator between a day and its stop name ("·" looks like the Arabic zero "٠"). */
export const SEP = ' – ';
