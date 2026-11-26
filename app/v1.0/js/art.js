// All illustrations are original inline SVG drawn for this app (flat, rounded style).
// No photos, emoji, brands or existing characters. Every function returns an SVG string.

const INK = '#24434F';
const st = (w = 3) => ` stroke="${INK}" stroke-width="${w}" stroke-linejoin="round" stroke-linecap="round"`;
const svg = (vb, inner, cls = '') =>
  `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${vb}"${cls ? ` class="${cls}"` : ''} aria-hidden="true" focusable="false">${inner}</svg>`;
const f1 = (n) => Math.round(n * 10) / 10;

// ---------------------------------------------------------------- Sanad
const SK = '#8FD4A6', SP = '#63B987', SH = '#2F8E6C', SC = '#5CB98D', RIM = '#F5E7BD', CHEEK = '#FF8C96', EYE = '#1F2B33';

export function sanadParts({ eyes = 'open', mouth = 'smile', anim = true, shadow = true } = {}) {
  const S = st(3);
  let g = '';
  if (shadow) g += `<ellipse cx="100" cy="184" rx="64" ry="8" fill="#0F3D4A" opacity=".12"/>`;
  g += `<path d="M60 150 C42 156 30 170 38 177 C48 182 62 170 70 160 Z" fill="${SK}"${S}/>`;
  g += `<path d="M140 150 C158 156 170 170 162 177 C152 182 138 170 130 160 Z" fill="${SK}"${S}/>`;
  g += `<ellipse cx="100" cy="133" rx="66" ry="45" fill="${RIM}"${S}/>`;
  // rim marks (marginal scutes)
  for (let a = 0; a < 360; a += 30) {
    const r = (a * Math.PI) / 180;
    g += `<path d="M${f1(100 + 57 * Math.cos(r))} ${f1(130 + 37 * Math.sin(r))} L${f1(100 + 65 * Math.cos(r))} ${f1(133 + 44 * Math.sin(r))}" stroke="#D8C690" stroke-width="2.5" stroke-linecap="round"/>`;
  }
  g += `<ellipse cx="100" cy="129" rx="56" ry="36" fill="${SH}"${S}/>`;
  const sc = ` fill="${SC}" stroke="#267A5C" stroke-width="2" stroke-linejoin="round"`;
  g += `<path d="M86 116 L100 108 L114 116 L114 136 L100 144 L86 136 Z"${sc}/>`;
  g += `<path d="M80 114 L64 119 C57 126 57 136 64 143 L80 138 Z"${sc}/>`;
  g += `<path d="M120 114 L136 119 C143 126 143 136 136 143 L120 138 Z"${sc}/>`;
  // front flippers (right one waves)
  g += `<g class="flip-l"><path d="M72 121 C50 112 23 120 12 138 C9 145 15 149 22 145 C36 137 54 134 75 135 Z" fill="${SK}"${S}/></g>`;
  g += `<g class="flip-r"><path d="M128 121 C150 112 177 120 188 138 C191 145 185 149 178 145 C164 137 146 134 125 135 Z" fill="${SK}"${S}/></g>`;
  // head
  g += `<g class="head">`;
  g += `<path d="M80 104 C80 96 120 96 120 104 L121 122 C108 126 92 126 79 122 Z" fill="${SK}"/>`;
  g += `<path d="M80 106 L79 121 M120 106 L121 121" fill="none"${st(3)}/>`;
  g += `<ellipse cx="100" cy="76" rx="41" ry="36" fill="${SK}"${S}/>`;
  g += `<ellipse cx="80" cy="51" rx="7.5" ry="4.5" fill="${SP}"/><ellipse cx="100" cy="45" rx="8.5" ry="5" fill="${SP}"/><ellipse cx="120" cy="51" rx="7.5" ry="4.5" fill="${SP}"/><ellipse cx="68" cy="64" rx="4" ry="3" fill="${SP}"/><ellipse cx="132" cy="64" rx="4" ry="3" fill="${SP}"/>`;
  if (eyes === 'open') {
    g += `<ellipse cx="84" cy="77" rx="10.5" ry="12.5" fill="#fff"${st(2.5)}/><ellipse cx="116" cy="77" rx="10.5" ry="12.5" fill="#fff"${st(2.5)}/>`;
    g += `<circle cx="85.5" cy="79.5" r="6.6" fill="${EYE}"/><circle cx="117.5" cy="79.5" r="6.6" fill="${EYE}"/>`;
    g += `<circle cx="88" cy="76" r="2.4" fill="#fff"/><circle cx="120" cy="76" r="2.4" fill="#fff"/>`;
    if (anim) g += `<g class="lids" opacity="0"><ellipse cx="84" cy="77" rx="12" ry="14" fill="${SK}"/><ellipse cx="116" cy="77" rx="12" ry="14" fill="${SK}"/><path d="M74 80 Q84 86 94 80 M106 80 Q116 86 126 80" fill="none"${st(3)}/></g>`;
  } else if (eyes === 'closed') {
    g += `<path d="M74 79 Q84 86 94 79 M106 79 Q116 86 126 79" fill="none"${st(3.2)}/>`;
  } else {
    g += `<path d="M74 81 Q84 70 94 81 M106 81 Q116 70 126 81" fill="none"${st(3.2)}/>`;
  }
  g += `<ellipse cx="70" cy="93" rx="7" ry="4.5" fill="${CHEEK}" opacity=".6"/><ellipse cx="130" cy="93" rx="7" ry="4.5" fill="${CHEEK}" opacity=".6"/>`;
  if (mouth === 'smile') g += `<path d="M89 96 Q100 105 111 96" fill="none"${st(3)}/>`;
  else if (mouth === 'open') g += `<path d="M88 94 Q100 109 112 94 Q100 98 88 94 Z" fill="#C8505A"${st(2.5)}/>`;
  else if (mouth === 'o') g += `<ellipse cx="100" cy="98" rx="5" ry="4.5" fill="#C8505A"${st(2.5)}/>`;
  else g += `<path d="M93 98 Q100 101 107 98" fill="none"${st(2.5)}/>`;
  g += `</g>`;
  return g;
}

/** The animated mascot used on child screens. */
export function sanad(opts = {}) {
  return svg('0 0 200 200', sanadParts(opts), 'sanad-svg');
}

// ---------------------------------------------------------------- pictures (120 x 120)
const P = {};

P.sun = () => {
  let r = '';
  for (let a = 0; a < 360; a += 45) {
    const t = (a * Math.PI) / 180;
    r += `<line x1="${f1(60 + 37 * Math.cos(t))}" y1="${f1(60 + 37 * Math.sin(t))}" x2="${f1(60 + 51 * Math.cos(t))}" y2="${f1(60 + 51 * Math.sin(t))}" stroke="#F59E0B" stroke-width="7" stroke-linecap="round"/>`;
  }
  return r + `<circle cx="60" cy="60" r="28" fill="#FFC93C"${st()}/><path d="M44 52 A18 18 0 0 1 58 40" fill="none" stroke="#FFE7A3" stroke-width="5" stroke-linecap="round"/>`;
};

P.sand = () =>
  `<path d="M6 98 C24 72 44 56 62 52 C78 60 94 76 114 98 Z" fill="#F2CC7E"${st()}/>` +
  `<path d="M62 54 C76 61 92 76 110 96 L84 96 C78 80 70 66 62 54 Z" fill="#DFA54C"/>` +
  `<path d="M4 106 C30 86 52 80 74 82 C92 84 106 92 116 102 L116 110 L4 110 Z" fill="#F7DA97"${st()}/>` +
  `<path d="M22 100 q12 -6 24 -3 M62 96 q12 -5 22 -1 M38 90 q8 -4 16 -2" fill="none" stroke="#D49B45" stroke-width="2.5" stroke-linecap="round"/>`;

P.ant = () =>
  `<path d="M56 72 L48 90 M62 74 L64 92 M68 72 L80 89" stroke="#5E3A22" stroke-width="3" stroke-linecap="round" fill="none"/>` +
  `<ellipse cx="34" cy="68" rx="21" ry="16" fill="#8A5530"${st()}/>` +
  `<ellipse cx="28" cy="61" rx="7" ry="4" fill="#B7794A" opacity=".8"/>` +
  `<ellipse cx="54.5" cy="66" rx="5" ry="5" fill="#8A5530"${st(2.5)}/>` +
  `<ellipse cx="65" cy="64" rx="10" ry="8.5" fill="#8A5530"${st()}/>` +
  `<path d="M82 45 Q84 32 94 28 M89 46 Q96 37 106 37" fill="none"${st(2.5)}/>` +
  `<circle cx="94" cy="28" r="3" fill="#9C6338"${st(2)}/><circle cx="106" cy="37" r="3" fill="#9C6338"${st(2)}/>` +
  `<circle cx="85" cy="57" r="13" fill="#9C6338"${st()}/>` +
  `<circle cx="90" cy="54" r="4.2" fill="#fff"/><circle cx="91" cy="54.5" r="2.3" fill="${EYE}"/>` +
  `<path d="M86 63 Q90 66 95 62" fill="none"${st(2)}/>` +
  `<path d="M58 72 L50 92 L44 94 M65 73 L67 94 L61 96 M71 71 L83 90 L89 92" fill="none"${st(3)}/>`;

P.apple = () =>
  `<path d="M60 40 C44 28 16 36 18 64 C20 92 42 108 60 100 C78 108 100 92 102 64 C104 36 76 28 60 40 Z" fill="#E84A4F"${st()}/>` +
  `<path d="M34 54 C31 62 32 72 37 80" fill="none" stroke="#fff" stroke-opacity=".6" stroke-width="5" stroke-linecap="round"/>` +
  `<path d="M60 40 C60 32 62 24 67 18" fill="none" stroke="#7A4B2A" stroke-width="5" stroke-linecap="round"/>` +
  `<path d="M65 27 C72 14 90 13 95 20 C88 31 73 33 65 27 Z" fill="#3AA55B"${st(2.5)}/>` +
  `<path d="M68 26 C76 23 84 21 92 20" fill="none" stroke="#2C7F45" stroke-width="2" stroke-linecap="round"/>`;

P.tent = () =>
  `<path d="M8 102 H112" fill="none"${st()}/>` +
  `<path d="M28 80 L12 100 M92 80 L108 100" stroke="${INK}" stroke-width="2" stroke-linecap="round"/>` +
  `<path d="M60 20 L104 100 H16 Z" fill="#FF8A3D"/>` +
  `<path d="M60 20 L104 100 H80 Z" fill="#E8702A"/>` +
  `<path d="M60 20 L104 100 H16 Z" fill="none"${st()}/>` +
  `<path d="M60 46 L76 100 H44 Z" fill="#7A3E17"${st(2.5)}/>` +
  `<path d="M60 46 L44 100 L35 100 Z" fill="#FFB27A"${st(2.5)}/>` +
  `<path d="M60 20 V8" fill="none"${st()}/>` +
  `<path d="M60 8 L74 12 L60 17 Z" fill="#FF6F7D"${st(2)}/>`;

P.tomato = () =>
  `<path d="M60 42 C30 40 14 56 16 74 C18 94 38 104 60 104 C82 104 102 94 104 74 C106 56 90 40 60 42 Z" fill="#F0533B"${st()}/>` +
  `<path d="M44 48 C38 60 38 82 46 98 M76 48 C82 60 82 82 74 98" fill="none" stroke="#C93A26" stroke-width="2.5" stroke-linecap="round"/>` +
  `<ellipse cx="34" cy="68" rx="6" ry="9" fill="#fff" opacity=".45"/>` +
  `<path d="M60 47 L47 38 L53 48 L39 50 L53 54 L49 63 L60 55 L71 63 L67 54 L81 50 L67 48 L73 38 Z" fill="#3AA55B"${st(2.5)}/>` +
  `<path d="M60 46 C60 40 61 34 64 29" fill="none" stroke="#2C7F45" stroke-width="4" stroke-linecap="round"/>`;

const PALM_FRONDS =
  `<path d="M63 42 C48 30 26 30 10 46 C26 40 44 42 62 47 Z"/><path d="M63 42 C78 30 100 30 112 46 C96 40 80 42 64 47 Z"/>` +
  `<path d="M62 42 C56 24 42 14 26 13 C40 22 52 32 59 45 Z"/><path d="M64 42 C72 24 86 14 102 14 C88 22 76 32 67 45 Z"/>` +
  `<path d="M61 44 C46 46 32 58 28 74 C38 62 50 54 62 49 Z"/><path d="M65 44 C80 46 94 58 98 74 C88 62 76 54 64 49 Z"/>`;

function palmTree() {
  return `<path d="M55 104 C53 84 55 62 59 44 L67 44 C65 62 64 84 67 104 Z" fill="#A0703F"${st()}/>` +
    `<path d="M55 92 Q61 95 66 91 M56 80 Q61 83 66 79 M57 68 Q62 71 66 67 M58 56 Q62 59 66 55" fill="none" stroke="#7A4B2A" stroke-width="2" stroke-linecap="round"/>` +
    `<g fill="#C8642A" stroke="${INK}" stroke-width="1.5"><ellipse cx="55" cy="51" rx="4" ry="5"/><ellipse cx="62" cy="53" rx="4" ry="5"/><ellipse cx="69" cy="51" rx="4" ry="5"/><ellipse cx="58" cy="58" rx="3.5" ry="4.5"/><ellipse cx="66" cy="58" rx="3.5" ry="4.5"/></g>` +
    `<g fill="#3AA55B"${st(2.5)}>${PALM_FRONDS}</g>` +
    `<path d="M62 44 C50 38 34 38 20 44 M64 44 C76 38 92 38 104 44 M62 43 C56 30 46 22 34 18 M64 43 C70 30 80 22 92 19" fill="none" stroke="#2C8447" stroke-width="1.8" stroke-linecap="round"/>` +
    `<circle cx="63" cy="44" r="5" fill="#2C8447"${st(2)}/>`;
}
P.palm = () => `<ellipse cx="61" cy="106" rx="30" ry="6" fill="#F2D48F"${st(2.5)}/>` + palmTree();

P.pen = () =>
  `<g transform="rotate(-38 60 60)">` +
  `<path d="M20 53 L6 60 L20 67 Z" fill="#F7E6BD"${st(2.5)}/>` +
  `<path d="M10 58 L3 60 L10 62 Z" fill="${INK}"/>` +
  `<rect x="19" y="51" width="62" height="18" rx="6" fill="#0F5E73"${st()}/>` +
  `<rect x="22" y="53" width="14" height="14" rx="3" fill="#1AA6A6"/>` +
  `<rect x="78" y="49" width="27" height="22" rx="7" fill="#1AA6A6"${st()}/>` +
  `<rect x="82" y="43" width="22" height="6" rx="3" fill="#E6F4F4"${st(2.2)}/>` +
  `<path d="M30 56 H70" stroke="#5FB7C9" stroke-width="2.5" stroke-linecap="round"/>` +
  `</g>`;

P.insect = () =>
  `<path d="M34 54 L20 46 M30 70 L13 70 M34 86 L20 96 M86 54 L100 46 M90 70 L107 70 M86 86 L100 96" fill="none"${st(3)}/>` +
  `<path d="M52 30 Q46 18 38 16 M68 30 Q74 18 82 16" fill="none"${st(2.5)}/>` +
  `<ellipse cx="60" cy="36" rx="18" ry="13" fill="#2B3138"${st()}/>` +
  `<circle cx="53" cy="33" r="3" fill="#fff"/><circle cx="67" cy="33" r="3" fill="#fff"/>` +
  `<circle cx="60" cy="68" r="31" fill="#E5484D"${st()}/>` +
  `<path d="M60 39 V99" fill="none"${st(3)}/>` +
  `<g fill="#2B3138"><circle cx="45" cy="56" r="6"/><circle cx="75" cy="56" r="6"/><circle cx="42" cy="78" r="5.5"/><circle cx="78" cy="78" r="5.5"/><circle cx="51" cy="92" r="4"/><circle cx="69" cy="92" r="4"/></g>` +
  `<ellipse cx="46" cy="46" rx="6" ry="3.5" fill="#fff" opacity=".5" transform="rotate(-30 46 46)"/>`;

P.ink = () =>
  `<path d="M100 60 C100 60 110 73 110 80 A10 10 0 0 1 90 80 C90 73 100 60 100 60 Z" fill="#1E4E9C"${st(2.5)}/>` +
  `<path d="M34 52 H76 C84 52 88 58 88 66 V98 C88 104 84 108 78 108 H32 C26 108 22 104 22 98 V66 C22 58 26 52 34 52 Z" fill="#DDF0F5"/>` +
  `<path d="M22 76 C38 71 70 81 88 74 V98 C88 104 84 108 78 108 H32 C26 108 22 104 22 98 Z" fill="#1E4E9C"/>` +
  `<path d="M34 52 H76 C84 52 88 58 88 66 V98 C88 104 84 108 78 108 H32 C26 108 22 104 22 98 V66 C22 58 26 52 34 52 Z" fill="none"${st()}/>` +
  `<rect x="31" y="82" width="48" height="17" rx="4" fill="#F7E6BD"${st(2)}/>` +
  `<path d="M39 90.5 H71" stroke="#C9B48A" stroke-width="3" stroke-linecap="round"/>` +
  `<path d="M28 60 V70" stroke="#fff" stroke-width="4" stroke-linecap="round" opacity=".85"/>` +
  `<rect x="41" y="38" width="28" height="16" rx="3" fill="#DDF0F5"${st()}/>` +
  `<rect x="37" y="24" width="36" height="16" rx="5" fill="#7A4B2A"${st()}/>`;

P.net = () =>
  `<path d="M14 30 Q60 20 106 30 L94 94 Q60 112 26 94 Z" fill="#E6F3F1"/>` +
  `<path d="M24 28 L32 97 M42 24 L46 103 M60 22 L60 106 M78 24 L74 103 M96 28 L88 97" fill="none" stroke="#2F6E78" stroke-width="2.2" stroke-linecap="round"/>` +
  `<path d="M18 48 Q60 40 102 48 M21 66 Q60 60 99 66 M24 84 Q60 92 96 84" fill="none" stroke="#2F6E78" stroke-width="2.2" stroke-linecap="round"/>` +
  `<path d="M14 30 L26 94 Q60 112 94 94 L106 30" fill="none"${st()}/>` +
  `<path d="M8 28 Q60 15 112 28" fill="none" stroke="#7A4B2A" stroke-width="5" stroke-linecap="round"/>` +
  `<g fill="#FF8A3D"${st(2)}><ellipse cx="24" cy="26" rx="7" ry="5"/><ellipse cx="46" cy="21" rx="7" ry="5"/><ellipse cx="74" cy="21" rx="7" ry="5"/><ellipse cx="96" cy="26" rx="7" ry="5"/></g>` +
  `<g fill="#5B6B73"${st(1.5)}><circle cx="34" cy="100" r="3.5"/><circle cx="60" cy="107" r="3.5"/><circle cx="86" cy="100" r="3.5"/></g>`;

P.nest = () =>
  `<g${st(2.5)}><ellipse cx="44" cy="62" rx="11" ry="14" fill="#DDF0F6"/><ellipse cx="76" cy="62" rx="11" ry="14" fill="#F6EBD3"/><ellipse cx="60" cy="57" rx="11.5" ry="14.5" fill="#EAF6E2"/></g>` +
  `<g fill="#9FB4BC"><circle cx="40" cy="58" r="1.6"/><circle cx="47" cy="54" r="1.4"/><circle cx="62" cy="50" r="1.5"/><circle cx="57" cy="56" r="1.3"/><circle cx="79" cy="57" r="1.5"/></g>` +
  `<path d="M14 64 C16 94 104 94 106 64 C92 74 28 74 14 64 Z" fill="#A9743F"${st()}/>` +
  `<path d="M19 71 C40 80 80 80 101 71 M23 80 C44 88 76 88 97 80 M31 88 C48 94 72 94 89 88" fill="none" stroke="#7A4B2A" stroke-width="2.5" stroke-linecap="round"/>` +
  `<path d="M13 62 L4 56 M107 62 L116 56 M19 74 L7 76 M101 74 L113 76" fill="none" stroke="#7A4B2A" stroke-width="3" stroke-linecap="round"/>`;

P.pan = () =>
  `<path d="M84 58 L113 49 C118 48 120 55 116 57 L87 69 Z" fill="#2E3A40"${st()}/>` +
  `<circle cx="112" cy="52" r="2.5" fill="#8FA0A8"/>` +
  `<ellipse cx="50" cy="64" rx="40" ry="30" fill="#3E4C54"${st()}/>` +
  `<ellipse cx="50" cy="61" rx="31" ry="22" fill="#5A6A72"/>` +
  `<path d="M30 52 Q40 44 54 43" fill="none" stroke="#9DADB5" stroke-width="4" stroke-linecap="round"/>`;

P.pin = () =>
  `<g transform="rotate(-6 60 72)"><rect x="20" y="46" width="80" height="60" rx="5" fill="#FFF7DE"${st()}/>` +
  `<path d="M32 72 H88 M32 84 H82 M32 96 H70" stroke="#E3CFA0" stroke-width="3" stroke-linecap="round"/></g>` +
  `<ellipse cx="66" cy="63" rx="11" ry="3" fill="#0F3D4A" opacity=".14"/>` +
  `<path d="M60 55 L60 64" stroke="#8C99A0" stroke-width="4" stroke-linecap="round"/>` +
  `<ellipse cx="60" cy="52" rx="20" ry="6" fill="#E04A5C"${st(2.5)}/>` +
  `<path d="M50 30 H70 L66 50 H54 Z" fill="#FF6F7D"${st(2.5)}/>` +
  `<ellipse cx="60" cy="28" rx="16" ry="7" fill="#FF8A95"${st(2.5)}/>` +
  `<path d="M52 27 Q56 24 62 24" stroke="#fff" stroke-width="2.5" fill="none" stroke-linecap="round" opacity=".85"/>`;

P.tin = () =>
  `<path d="M30 30 V100 A30 9 0 0 0 90 100 V30 Z" fill="#C7D2D8"${st()}/>` +
  `<path d="M30 50 A30 9 0 0 0 90 50 V80 A30 9 0 0 1 30 80 Z" fill="#1AA6A6"${st(2.5)}/>` +
  `<path d="M38 65 Q46 59 54 65 T70 65 T84 65" fill="none" stroke="#E6F7F7" stroke-width="3" stroke-linecap="round"/>` +
  `<path d="M30 40 A30 9 0 0 0 90 40 M30 92 A30 9 0 0 0 90 92" fill="none" stroke="#9AA8AF" stroke-width="2"/>` +
  `<path d="M40 42 V48 M40 84 V96" stroke="#fff" stroke-width="4" opacity=".7" stroke-linecap="round"/>` +
  `<ellipse cx="60" cy="30" rx="30" ry="9" fill="#E4EAED"${st()}/>` +
  `<ellipse cx="60" cy="30" rx="23" ry="6" fill="none" stroke="#9AA8AF" stroke-width="2"/>`;

P.tap = () =>
  `<rect x="8" y="30" width="14" height="36" rx="4" fill="#B9C4CA"${st()}/>` +
  `<path d="M22 40 H72 C84 40 92 48 92 60 V70 H78 V62 C78 56 75 54 70 54 H22 Z" fill="#D3DCE1"${st()}/>` +
  `<rect x="76" y="68" width="18" height="6" rx="2" fill="#B9C4CA"${st(2.5)}/>` +
  `<rect x="48" y="26" width="10" height="15" fill="#B9C4CA"${st(2.5)}/>` +
  `<rect x="33" y="16" width="40" height="11" rx="5.5" fill="#1AA6A6"${st()}/>` +
  `<path d="M28 45 H66" stroke="#fff" stroke-width="3" stroke-linecap="round" opacity=".75"/>` +
  `<path d="M85 82 C85 82 91 90 91 94 A6 6 0 0 1 79 94 C79 90 85 82 85 82 Z" fill="#5BC0EB"${st(2)}/>` +
  `<path d="M85 101 C85 101 89 106 89 109 A4 4 0 0 1 81 109 C81 106 85 101 85 101 Z" fill="#5BC0EB"${st(2)}/>`;

P.tip = () =>
  `<g transform="rotate(-40 60 60)">` +
  `<rect x="34" y="50" width="60" height="20" fill="#FFC93C"${st()}/>` +
  `<path d="M34 56.6 H94 M34 63.4 H94" stroke="#F2A516" stroke-width="2"/>` +
  `<rect x="94" y="49" width="10" height="22" fill="#B9C4CA"${st(2.5)}/>` +
  `<path d="M104 49 H109 C113 49 115 52 115 56 V64 C115 68 113 71 109 71 H104 Z" fill="#FF8FA0"${st(2.5)}/>` +
  `<path d="M34 50 L12 60 L34 70 Z" fill="#F4D9A8"${st(2.5)}/>` +
  `<path d="M19.5 56.6 L6 60 L19.5 63.4 Z" fill="#3B474E"${st(2)}/>` +
  `</g>` +
  `<circle cx="19" cy="95" r="14" fill="none" stroke="#FF6F7D" stroke-width="3" stroke-dasharray="5 5"/>`;

P.pit = () =>
  `<path d="M4 66 C30 56 90 56 116 66 V110 H4 Z" fill="#F4D89B"${st()}/>` +
  `<g fill="#E0B868"><circle cx="20" cy="96" r="2"/><circle cx="96" cy="98" r="2"/><circle cx="36" cy="104" r="1.6"/><circle cx="84" cy="88" r="1.6"/></g>` +
  `<path d="M84 70 C90 54 104 54 110 70 Z" fill="#EBC77D"${st(2.5)}/>` +
  `<ellipse cx="56" cy="80" rx="31" ry="12" fill="#8A5A35"${st()}/>` +
  `<ellipse cx="56" cy="83" rx="23" ry="7.5" fill="#4A2C17"/>` +
  `<path d="M100 60 L106 30" stroke="#7A4B2A" stroke-width="4" stroke-linecap="round"/>` +
  `<path d="M94 66 L98 52 L108 54 L104 68 Q99 72 94 66 Z" fill="#1AA6A6"${st(2)}/>` +
  `<path d="M12 50 H34 L30 70 H16 Z" fill="#FF6F7D"${st(2.5)}/><path d="M14 50 Q23 36 32 50" fill="none"${st(2.5)}/>`;

P.pat = () =>
  `<path d="M84 100 C98 100 106 90 102 80" fill="none" stroke="${INK}" stroke-width="10" stroke-linecap="round"/>` +
  `<path d="M84 100 C98 100 106 90 102 80" fill="none" stroke="#F4A259" stroke-width="5" stroke-linecap="round"/>` +
  `<path d="M30 106 C26 82 34 68 52 66 C70 64 84 74 86 92 C87 100 86 104 84 106 Z" fill="#F4A259"${st()}/>` +
  `<path d="M40 49 L37 31 L52 41 Z M72 49 L75 31 L60 41 Z" fill="#F4A259"${st(2.5)}/>` +
  `<path d="M41 45 L40 36 L48 41 Z M71 45 L72 36 L64 41 Z" fill="#FFB8C0"/>` +
  `<circle cx="56" cy="59" r="20" fill="#F4A259"${st()}/>` +
  `<path d="M46 59 Q50 55 54 59 M58 59 Q62 55 66 59" fill="none"${st(2.5)}/>` +
  `<path d="M54 64.5 L58 64.5 L56 67 Z" fill="#E05A6A"/>` +
  `<path d="M56 67 Q53 71 50 69 M56 67 Q59 71 62 69" fill="none"${st(2)}/>` +
  `<path d="M44 65 L31 63 M44 68 L31 70 M68 65 L81 63 M68 68 L81 70" stroke="${INK}" stroke-width="1.8" stroke-linecap="round"/>` +
  `<path d="M98 6 L76 30 L86 38 L110 16 Z" fill="#C68B59"${st(2.5)}/>` +
  `<path d="M96 4 L112 20 L118 13 L103 -1 Z" fill="#FFFFFF"${st(2.5)}/>` +
  `<path d="M42 38 C42 31 50 27 60 27 C70 27 80 30 82 36 C83 39 81 41 78 40 C74 42 64 43 56 43 C48 43 42 42 42 38 Z" fill="#C68B59"${st(2.5)}/>` +
  `<path d="M52 33 V41 M60 31 V42 M68 32 V41" stroke="#9E6A40" stroke-width="1.8" stroke-linecap="round"/>` +
  `<path d="M88 46 Q94 42 96 36 M92 54 Q100 50 102 42" fill="none" stroke="#1AA6A6" stroke-width="2.6" stroke-linecap="round"/>`;

P.sit = () =>
  `<ellipse cx="58" cy="105" rx="48" ry="6" fill="#0F3D4A" opacity=".1"/>` +
  `<path d="M18 82 C11 84 9 90 12 94" fill="none"${st(3)}/>` +
  `<rect x="20" y="91" width="30" height="12" rx="6" fill="#C98D55"${st(2.5)}/>` +
  `<rect x="58" y="91" width="32" height="12" rx="6" fill="#C98D55"${st(2.5)}/>` +
  `<path d="M18 94 C15 72 29 60 43 58 C47 41 66 39 72 54 C81 56 89 64 91 76 C93 86 91 93 87 95 Z" fill="#D9A066"${st()}/>` +
  `<path d="M43 58 C50 54 66 54 72 58 L74 74 C64 78 50 78 41 74 Z" fill="#FF6F7D"${st(2.5)}/>` +
  `<path d="M45 70 H71" stroke="#FFD166" stroke-width="3" stroke-dasharray="2 4" stroke-linecap="round"/>` +
  `<path d="M84 72 C92 63 94 49 92 37 L102 33 C106 47 104 65 95 80 Z" fill="#D9A066"${st()}/>` +
  `<path d="M90 35 C90 25 98 21 106 23 C114 25 118 31 116 37 C114 41 106 41 100 41 C96 41 92 39 90 35 Z" fill="#D9A066"${st()}/>` +
  `<path d="M95 25 L92 18 L100 22" fill="#D9A066"${st(2)}/>` +
  `<circle cx="103" cy="29" r="2.7" fill="${INK}"/>` +
  `<path d="M111 35 Q113 37.5 116 36" fill="none"${st(2)}/>`;

P.sat = () =>
  `<path d="M12 106 C8 88 20 76 40 74 C56 68 80 70 96 78 C110 84 113 98 107 106 Z" fill="#A8B3B9"${st()}/>` +
  `<path d="M30 84 C40 79 54 78 64 80" fill="none" stroke="#D3DADE" stroke-width="4" stroke-linecap="round"/>` +
  `<g transform="translate(12 -12) scale(.48)">${sanadParts({ anim: false, shadow: false })}</g>`;

P.nap = () =>
  `<path d="M96 8 A15 15 0 1 0 113 30 A11.5 11.5 0 1 1 96 8 Z" fill="#FFD166"${st(2.5)}/>` +
  `<path d="M80 14 l2 4 4 2 -4 2 -2 4 -2 -4 -4 -2 4 -2 Z M108 44 l1.5 3 3 1.5 -3 1.5 -1.5 3 -1.5 -3 -3 -1.5 3 -1.5 Z" fill="#FFD166"${st(1.5)}/>` +
  `<rect x="4" y="84" width="112" height="26" rx="13" fill="#F7E6BD"${st()}/>` +
  `<path d="M16 96 H104" stroke="#E5CF98" stroke-width="3" stroke-linecap="round"/>` +
  `<g transform="translate(6 2) scale(.5) rotate(-8 100 120)">${sanadParts({ eyes: 'closed', mouth: 'calm', anim: false, shadow: false })}</g>`;

P.sip = () =>
  `<g transform="translate(10 -6) scale(.5)">${sanadParts({ eyes: 'happy', mouth: 'o', anim: false, shadow: false })}</g>` +
  `<path d="M65 76 L63 54 L60 49" fill="none" stroke="#FF6F7D" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round"/>` +
  `<path d="M44 70 H78 L73 108 H49 Z" fill="#E9F7FA"${st()}/>` +
  `<path d="M46.5 84 H75.5 L73 106 H49 Z" fill="#FF9F43"/>` +
  `<path d="M44 70 H78 L73 108 H49 Z" fill="none"${st()}/>` +
  `<circle cx="56" cy="94" r="2" fill="#FFD9A8"/><circle cx="64" cy="98" r="1.6" fill="#FFD9A8"/>`;

const PICTURE_NAMES = Object.keys(P);
export function picture(id) {
  const fn = P[id];
  if (!fn) return svg('0 0 120 120', `<rect x="10" y="10" width="100" height="100" rx="18" fill="#F7E6BD"${st()}/>`, 'pic');
  return svg('0 0 120 120', fn(), 'pic');
}
export const pictureIds = PICTURE_NAMES;

// ---------------------------------------------------------------- stickers (120 x 120)
const STK = {
  turtle: { bg: '#9ED9D6', body: () =>
    `<path d="M24 74 q8 -4 16 0 t16 0 M66 92 q8 -4 16 0 t16 0" fill="none" stroke="#6CC3BF" stroke-width="3" stroke-linecap="round"/>` +
    `<path d="M46 50 C32 40 20 42 16 50 C24 54 34 58 46 60 Z M74 50 C88 40 100 42 104 50 C96 54 86 58 74 60 Z" fill="${SK}"${st(2.5)}/>` +
    `<path d="M50 84 C42 90 38 96 42 98 C48 98 54 92 56 86 Z M70 84 C78 90 82 96 78 98 C72 98 66 92 64 86 Z" fill="${SK}"${st(2.5)}/>` +
    `<circle cx="60" cy="34" r="9" fill="${SK}"${st(2.5)}/><circle cx="56.5" cy="32" r="1.8" fill="${EYE}"/><circle cx="63.5" cy="32" r="1.8" fill="${EYE}"/>` +
    `<ellipse cx="60" cy="64" rx="22" ry="26" fill="${SH}"${st(2.5)}/>` +
    `<path d="M60 44 L70 52 L70 68 L60 76 L50 68 L50 52 Z" fill="${SC}" stroke="#267A5C" stroke-width="2" stroke-linejoin="round"/>` +
    `<path d="M50 52 L42 56 M50 68 L42 72 M70 52 L78 56 M70 68 L78 72 M60 76 L60 88" stroke="#267A5C" stroke-width="2" stroke-linecap="round"/>` },
  palm: { bg: '#CDEFF5', body: () =>
    `<path d="M14 92 C34 84 86 84 106 92 C100 104 84 110 60 110 C36 110 20 104 14 92 Z" fill="#F2D48F"/>` +
    `<g transform="translate(9 6) scale(.85)">${palmTree()}</g>` },
  fort: { bg: '#FFD4B0', body: () =>
    `<path d="M16 96 H104" fill="none"${st(2.5)}/>` +
    `<path d="M40 52 V96 H98 V52 L92 52 V46 H86 V52 H80 V46 H74 V52 H68 V46 H62 V52 H56 V46 H50 V52 Z" fill="#E9C98E"${st(2.5)}/>` +
    `<path d="M20 96 V44 C20 38 42 38 42 44 V96 Z" fill="#DDB874"${st(2.5)}/>` +
    `<path d="M18 44 H44 V36 H39 V40 H34 V36 H29 V40 H24 V36 H18 Z" fill="#DDB874"${st(2.5)}/>` +
    `<path d="M62 96 V80 C62 72 76 72 76 80 V96 Z" fill="#7A4B2A"${st(2.5)}/>` +
    `<rect x="27" y="56" width="8" height="12" rx="4" fill="#7A4B2A"/><rect x="50" y="62" width="7" height="10" rx="3.5" fill="#7A4B2A"/><rect x="83" y="62" width="7" height="10" rx="3.5" fill="#7A4B2A"/>` +
    `<path d="M24 76 H38 M44 84 H58 M80 84 H94" stroke="#C9A060" stroke-width="2" stroke-linecap="round"/>` },
  dates: { bg: '#F7E6BD', body: () =>
    `<g fill="#8B4513"${st(2)}><ellipse cx="44" cy="58" rx="8" ry="11" transform="rotate(-20 44 58)"/><ellipse cx="60" cy="52" rx="8" ry="11"/><ellipse cx="76" cy="58" rx="8" ry="11" transform="rotate(20 76 58)"/><ellipse cx="52" cy="64" rx="8" ry="11" transform="rotate(-8 52 64)"/><ellipse cx="68" cy="64" rx="8" ry="11" transform="rotate(8 68 64)"/></g>` +
    `<g fill="#C27A47"><ellipse cx="42" cy="54" rx="2" ry="3.5" transform="rotate(-20 42 54)"/><ellipse cx="58" cy="48" rx="2" ry="3.5"/><ellipse cx="74" cy="54" rx="2" ry="3.5" transform="rotate(20 74 54)"/></g>` +
    `<path d="M22 66 H98 C96 86 80 98 60 98 C40 98 24 86 22 66 Z" fill="#1AA6A6"${st(2.5)}/>` +
    `<path d="M30 74 L36 82 L42 74 L48 82 L54 74 L60 82 L66 74 L72 82 L78 74 L84 82 L90 74" fill="none" stroke="#FFD166" stroke-width="3" stroke-linejoin="round"/>` +
    `<path d="M48 98 H72 L68 104 H52 Z" fill="#0F5E73"${st(2)}/>` },
  dhow: { bg: '#8FD3D0', body: () =>
    `<path d="M14 88 q9 -5 18 0 t18 0 t18 0 t18 0 t18 0" fill="none" stroke="#5BB9B5" stroke-width="3.5" stroke-linecap="round"/>` +
    `<path d="M58 28 V80" fill="none"${st(3)}/>` +
    `<path d="M60 30 C78 42 90 60 92 76 H60 Z" fill="#FFF7E6"${st(2.5)}/>` +
    `<path d="M56 34 C44 48 36 62 34 74 H56 Z" fill="#F7E6BD"${st(2.5)}/>` +
    `<path d="M66 44 L82 72 M60 52 L74 72" stroke="#E8D3A3" stroke-width="2" stroke-linecap="round"/>` +
    `<path d="M18 74 H102 C98 86 86 92 74 92 H40 C30 92 22 86 18 74 Z" fill="#9A5B2E"${st(2.5)}/>` +
    `<path d="M24 80 H96" stroke="#C78B55" stroke-width="2.5" stroke-linecap="round"/>` +
    `<path d="M102 74 L110 66" fill="none"${st(3)}/>` },
};

export function sticker(id, { earned = true } = {}) {
  const s = STK[id];
  if (!s) return '';
  const inner = `<circle cx="60" cy="60" r="56" fill="#fff" stroke="#E2D3A8" stroke-width="2"/>` +
    `<circle cx="60" cy="60" r="48" fill="${s.bg}"/>` + s.body();
  if (earned) return svg('0 0 120 120', inner, 'sticker-svg');
  // not yet earned: soft outline only (shape visible, no colour) + a question mark badge
  return svg('0 0 120 120', `<g opacity=".35">${inner.replace(/fill="#[0-9A-Fa-f]{3,6}"/g, 'fill="#D9D2C2"')}</g>`, 'sticker-svg locked');
}
export const stickerIds = Object.keys(STK);

// ---------------------------------------------------------------- journey map (360 x 640)
export const MAP_STOPS = [
  { id: 'beach', x: 92, y: 578 },
  { id: 'palms', x: 262, y: 470 },
  { id: 'fort', x: 182, y: 380 },
  { id: 'wadi', x: 256, y: 238 },
  { id: 'sea', x: 112, y: 150 },
];

export function mapArt() {
  const palm = (x, y, s) => `<g transform="translate(${x} ${y}) scale(${s}) translate(-61 -106)">${palmTree()}</g>`;
  let g = '';
  g += `<rect width="360" height="640" fill="#F7E6BD"/>`;
  // top sea
  g += `<path d="M0 0 H360 V112 C304 132 246 100 186 120 C128 140 66 112 0 132 Z" fill="#1AA6A6"/>`;
  g += `<path d="M0 132 C66 112 128 140 186 120 C246 100 304 132 360 112" fill="none" stroke="#FFFFFF" stroke-width="5" stroke-linecap="round" opacity=".85"/>`;
  g += `<path d="M24 40 q10 -6 20 0 t20 0 M210 26 q10 -6 20 0 t20 0 M60 86 q10 -6 20 0 t20 0 M290 90 q8 -5 16 0 t16 0" fill="none" stroke="#7FD3D3" stroke-width="3.5" stroke-linecap="round"/>`;
  // dhow in the sea
  g += `<g transform="translate(212 18) scale(.9)">` +
    `<path d="M58 28 V80" fill="none"${st(3)}/>` +
    `<path d="M60 30 C78 42 90 60 92 76 H60 Z" fill="#FFF7E6"${st(2.5)}/>` +
    `<path d="M56 34 C44 48 36 62 34 74 H56 Z" fill="#F7E6BD"${st(2.5)}/>` +
    `<path d="M18 74 H102 C98 86 86 92 74 92 H40 C30 92 22 86 18 74 Z" fill="#9A5B2E"${st(2.5)}/>` +
    `<path d="M24 80 H96" stroke="#C78B55" stroke-width="2.5" stroke-linecap="round"/></g>`;
  // wadi: mountains + turquoise pool
  g += `<path d="M150 300 L196 196 L232 246 L270 170 L318 236 L360 186 V300 Z" fill="#C98E6A"${st(3)}/>`;
  g += `<path d="M196 196 L214 248 L232 246 M270 170 L284 236 L318 236" fill="none" stroke="#A9714F" stroke-width="3" stroke-linejoin="round"/>`;
  g += `<path d="M168 300 C196 280 226 282 246 290 C272 280 310 284 336 300 Z" fill="#B97E5B"/>`;
  g += `<ellipse cx="270" cy="282" rx="40" ry="11" fill="#5CC8C8"${st(2.5)}/>`;
  g += `<path d="M252 282 q8 -3 16 0 M276 280 q8 -3 14 0" fill="none" stroke="#E6FAFA" stroke-width="2.5" stroke-linecap="round"/>`;
  g += palm(330, 292, .42);
  // fort on a hill
  g += `<path d="M0 410 C40 360 120 352 200 392 C214 400 220 410 220 410 Z" fill="#EBCB8B"/>`;
  g += `<g transform="translate(36 288) scale(1.12)">` +
    `<path d="M40 52 V96 H98 V52 L92 52 V46 H86 V52 H80 V46 H74 V52 H68 V46 H62 V52 H56 V46 H50 V52 Z" fill="#E9C98E"${st(2.5)}/>` +
    `<path d="M20 96 V44 C20 38 42 38 42 44 V96 Z" fill="#DDB874"${st(2.5)}/>` +
    `<path d="M18 44 H44 V36 H39 V40 H34 V36 H29 V40 H24 V36 H18 Z" fill="#DDB874"${st(2.5)}/>` +
    `<path d="M62 96 V80 C62 72 76 72 76 80 V96 Z" fill="#7A4B2A"${st(2.5)}/>` +
    `<rect x="27" y="56" width="8" height="12" rx="4" fill="#7A4B2A"/><rect x="50" y="62" width="7" height="10" rx="3.5" fill="#7A4B2A"/><rect x="83" y="62" width="7" height="10" rx="3.5" fill="#7A4B2A"/></g>`;
  // palm grove
  g += `<ellipse cx="270" cy="500" rx="98" ry="34" fill="#CFE8B4"/>`;
  g += palm(204, 486, .62) + palm(326, 480, .58) + palm(256, 512, .7) + palm(300, 520, .5);
  // beach + sea corner with turtle tracks
  g += `<path d="M0 548 C52 540 118 594 146 640 H0 Z" fill="#1AA6A6"/>`;
  g += `<path d="M0 548 C52 540 118 594 146 640" fill="none" stroke="#fff" stroke-width="5" stroke-linecap="round" opacity=".9"/>`;
  g += `<path d="M20 590 q8 -5 16 0 t16 0 M40 620 q8 -5 16 0 t16 0" fill="none" stroke="#7FD3D3" stroke-width="3.5" stroke-linecap="round"/>`;
  g += `<path d="M170 612 l8 -6 M180 600 l8 -6 M190 588 l8 -6 M200 576 l8 -6 M168 600 l-6 -8 M178 588 l-6 -8 M188 576 l-6 -8" stroke="#D9B56E" stroke-width="3" stroke-linecap="round"/>`;
  g += `<g transform="translate(206 548) scale(.16)">${sanadParts({ anim: false, shadow: false })}</g>`;
  g += `<ellipse cx="300" cy="598" rx="26" ry="10" fill="#EBCB8B"/><ellipse cx="300" cy="594" rx="12" ry="5" fill="#D9B56E"/>`;
  // path between the stops
  const d = 'M92 578 C170 566 262 540 262 470 C262 420 196 430 182 380 C168 320 250 300 256 238 C262 186 150 204 112 150';
  g += `<path d="${d}" fill="none" stroke="#FFFFFF" stroke-width="14" stroke-linecap="round" opacity=".75"/>`;
  g += `<path d="${d}" fill="none" stroke="#B98A4E" stroke-width="5" stroke-linecap="round" stroke-dasharray="1 14"/>`;
  return svg('0 0 360 640', g, 'map-svg');
}

// ---------------------------------------------------------------- family scenes (240 x 170)
const SKIN = { mother: '#C68B59', father: '#A86F45', sister: '#D19A6E', brother: '#B07A4F', girl: '#C9935F', boy: '#B57E52' };

function adult(kind) {
  const skin = SKIN[kind];
  let g = '';
  const robe = kind === 'mother' ? '#3D4B5C' : kind === 'sister' ? '#1AA6A6' : kind === 'father' ? '#FFFFFF' : '#DCEEF5';
  g += `<path d="M42 156 C40 116 52 88 80 86 C108 88 118 116 116 156 Z" fill="${robe}"${st()}/>`;
  if (kind === 'mother') g += `<path d="M58 104 C62 120 62 140 60 156 M100 104 C96 120 96 140 98 156" fill="none" stroke="#C9A24D" stroke-width="2.5" stroke-linecap="round"/>`;
  if (kind === 'father' || kind === 'brother') {
    g += `<path d="M80 92 V112" stroke="#C9D5DA" stroke-width="2.5" stroke-linecap="round"/>`;
    g += `<path d="M80 94 C78 104 78 112 80 120 C82 112 82 104 80 94 Z" fill="${kind === 'father' ? '#E3C27A' : '#9FC7D6'}"${st(1.8)}/>`;
    g += `<path d="M50 120 C54 130 56 142 56 156" fill="none" stroke="#E2EAEE" stroke-width="3" stroke-linecap="round"/>`;
  }
  // arm reaching to the phone
  g += `<path d="M98 104 C110 110 118 116 126 118" fill="none" stroke="${INK}" stroke-width="15" stroke-linecap="round"/>`;
  g += `<path d="M98 104 C110 110 118 116 126 118" fill="none" stroke="${robe}" stroke-width="10" stroke-linecap="round"/>`;
  g += `<circle cx="128" cy="118" r="6.5" fill="${skin}"${st(2.5)}/>`;
  // head
  if (kind === 'mother' || kind === 'sister') {
    const scarf = kind === 'mother' ? '#0F5E73' : '#FF8A3D';
    g += `<path d="M58 66 C56 34 106 32 104 66 C106 82 96 94 80 96 C64 94 56 82 58 66 Z" fill="${scarf}"${st()}/>`;
    g += `<ellipse cx="83" cy="64" rx="13" ry="15" fill="${skin}"${st(2.5)}/>`;
    g += `<path d="M66 54 C72 46 92 44 100 52" fill="none" stroke="${kind === 'mother' ? '#1AA6A6' : '#FFB27A'}" stroke-width="3" stroke-linecap="round"/>`;
  } else {
    g += `<ellipse cx="82" cy="64" rx="15" ry="17" fill="${skin}"${st()}/>`;
    g += `<path d="M65 54 C65 40 99 40 99 54 Z" fill="#FFFFFF"${st(2.5)}/>`;
    g += `<g fill="${kind === 'father' ? '#0F5E73' : '#FF8A3D'}"><circle cx="72" cy="50" r="1.8"/><circle cx="78" cy="47.5" r="1.8"/><circle cx="84" cy="47" r="1.8"/><circle cx="90" cy="48" r="1.8"/><circle cx="95" cy="51" r="1.6"/></g>`;
    g += `<path d="M66 53.5 H98" stroke="${kind === 'father' ? '#1AA6A6' : '#3AA55B'}" stroke-width="2.5" stroke-linecap="round"/>`;
    if (kind === 'father') g += `<path d="M70 68 C70 80 76 84 83 84 C90 84 96 80 96 68 C93 74 89 76 83 76 C77 76 73 74 70 68 Z" fill="#3B2A20"/>`;
  }
  // face (looking at the phone, to the right)
  g += `<ellipse cx="87" cy="64" rx="1.9" ry="2.3" fill="${EYE}"/><ellipse cx="95" cy="64" rx="1.9" ry="2.3" fill="${EYE}"/>`;
  g += `<path d="M86 72 Q90 75 94 72" fill="none"${st(2)}/>`;
  return g;
}

function child(kind) {
  const skin = SKIN[kind];
  let g = '';
  const cloth = kind === 'girl' ? '#FF8A3D' : '#7CCBD8';
  g += `<path d="M138 156 C136 128 146 112 166 110 C186 112 194 128 192 156 Z" fill="${cloth}"${st()}/>`;
  if (kind === 'girl') g += `<path d="M148 136 H184" stroke="#FFD166" stroke-width="3" stroke-dasharray="3 5" stroke-linecap="round"/>`;
  else g += `<path d="M166 114 V128" stroke="#4FA9B8" stroke-width="2.5" stroke-linecap="round"/>`;
  // arm pointing at the phone
  g += `<path d="M148 126 C142 124 138 122 134 120" fill="none" stroke="${INK}" stroke-width="13" stroke-linecap="round"/>`;
  g += `<path d="M148 126 C142 124 138 122 134 120" fill="none" stroke="${cloth}" stroke-width="8.5" stroke-linecap="round"/>`;
  g += `<circle cx="133" cy="119" r="5" fill="${skin}"${st(2.2)}/>`;
  if (kind === 'girl') {
    g += `<path d="M148 92 C146 66 186 66 184 92 C186 104 178 112 166 113 C154 112 146 104 148 92 Z" fill="#FFE1E6"${st()}/>`;
    g += `<ellipse cx="164" cy="91" rx="11" ry="12.5" fill="${skin}"${st(2.5)}/>`;
  } else {
    g += `<ellipse cx="164" cy="90" rx="13" ry="14.5" fill="${skin}"${st()}/>`;
    g += `<path d="M151 86 C150 72 178 70 178 84 C172 80 160 80 151 86 Z" fill="#2B2018"/>`;
  }
  g += `<ellipse cx="157" cy="91" rx="1.8" ry="2.2" fill="${EYE}"/><ellipse cx="164" cy="91" rx="1.8" ry="2.2" fill="${EYE}"/>`;
  g += `<path d="M156 98 Q160 101 164 98" fill="none"${st(2)}/>`;
  g += `<ellipse cx="170" cy="96" rx="3.5" ry="2.2" fill="${CHEEK}" opacity=".55"/>`;
  return g;
}

export function family(kind = 'mother-boy') {
  const [a, c] = kind.split('-');
  let g = '';
  g += `<rect width="240" height="170" rx="20" fill="#FFF4DC"/>`;
  // arched window with a palm outside
  g += `<path d="M168 70 V26 C168 8 214 8 214 26 V70 Z" fill="#CDEFF5"${st(2.5)}/>`;
  g += `<g transform="translate(176 22) scale(.32)">${palmTree()}</g>`;
  g += `<path d="M164 70 H218" fill="none"${st(3)}/>`;
  g += `<path d="M191 12 V70" stroke="#FFFFFF" stroke-width="2.5" opacity=".7"/>`;
  // majlis cushion with a woven pattern
  g += `<rect x="14" y="146" width="212" height="20" rx="8" fill="#C0392B" opacity=".85"/>`;
  g += `<path d="M22 156 L30 150 L38 156 L46 150 L54 156 L62 150 L70 156 L78 150 L86 156 L94 150 L102 156 L110 150 L118 156 L126 150 L134 156 L142 150 L150 156 L158 150 L166 156 L174 150 L182 156 L190 150 L198 156 L206 150 L214 156" fill="none" stroke="#FFD166" stroke-width="2.5" stroke-linejoin="round"/>`;
  g += adult(a);
  g += child(c);
  // the phone between them, showing letters
  g += `<g transform="rotate(-12 131 108)"><rect x="121" y="92" width="22" height="34" rx="4" fill="#24434F"/><rect x="123.5" y="95.5" width="17" height="25" rx="2" fill="#1AA6A6"/>` +
    `<circle cx="132" cy="108" r="5.5" fill="${SK}" stroke="#24434F" stroke-width="1.2"/><circle cx="130.3" cy="107.3" r="1" fill="#24434F"/><circle cx="133.7" cy="107.3" r="1" fill="#24434F"/></g>`;
  return svg('0 0 240 170', g, 'family-svg');
}

// ---------------------------------------------------------------- icons (24 x 24, currentColor)
const IC = {
  speaker: '<path d="M3.5 9.2h3.6L12 5v14l-4.9-4.2H3.5z" fill="currentColor" stroke="none"/><path d="M15.6 9a4.2 4.2 0 0 1 0 6M18.3 6.3a8 8 0 0 1 0 11.4"/>',
  parent: '<circle cx="8.5" cy="6.5" r="2.7"/><path d="M4 20.5v-5a4.5 4.5 0 0 1 9 0v5"/><circle cx="17" cy="10.3" r="2.1"/><path d="M14 20.5v-3.2a3 3 0 0 1 6 0v3.2"/>',
  home: '<path d="M4 11.2 12 4.7l8 6.5V20h-5.4v-5.2H9.4V20H4z"/>',
  gear: '<circle cx="12" cy="12" r="3.2"/><path d="M12 2.8v2.6M12 18.6v2.6M21.2 12h-2.6M5.4 12H2.8M18.5 5.5l-1.8 1.8M7.3 16.7l-1.8 1.8M18.5 18.5l-1.8-1.8M7.3 7.3 5.5 5.5"/><circle cx="12" cy="12" r="6.3"/>',
  map: '<path d="M3.5 6.5 9 4l6 2.5L20.5 4v13.5L15 20l-6-2.5-5.5 2.5z"/><path d="M9 4v13.5M15 6.5V20"/>',
  star: '<path d="m12 3.5 2.6 5.3 5.8.8-4.2 4.1 1 5.8L12 16.8l-5.2 2.7 1-5.8L3.6 9.6l5.8-.8z"/>',
  starFill: '<path d="m12 3.5 2.6 5.3 5.8.8-4.2 4.1 1 5.8L12 16.8l-5.2 2.7 1-5.8L3.6 9.6l5.8-.8z" fill="currentColor"/>',
  check: '<path d="m5 12.5 4.5 4.5L19 7.5"/>',
  retry: '<path d="M4.6 12a7.4 7.4 0 1 0 2.2-5.3"/><path d="M4.6 3.8v4.6h4.6"/>',
  hint: '<path d="M9 18h6M10 21h4"/><path d="M12 3a6 6 0 0 0-3.5 10.9c.6.5 1 1.2 1 2V16h5v-.1c0-.8.4-1.5 1-2A6 6 0 0 0 12 3z"/>',
  lock: '<rect x="5" y="10.5" width="14" height="10" rx="2.5"/><path d="M8 10.5V8a4 4 0 0 1 8 0v2.5"/>',
  unlock: '<rect x="5" y="10.5" width="14" height="10" rx="2.5"/><path d="M8 10.5V8a4 4 0 0 1 7.7-1.5"/>',
  play: '<path d="M8 5.2v13.6L18.8 12z" fill="currentColor"/>',
  next: '<path d="M5 12h14M13 6l6 6-6 6"/>',
  back: '<path d="M19 12H5M11 6l-6 6 6 6"/>',
  book: '<path d="M4.5 4.5A1.5 1.5 0 0 1 6 3h13.5v14.5H6a1.5 1.5 0 0 0-1.5 1.5z"/><path d="M4.5 19A1.5 1.5 0 0 0 6 20.5h13.5v-3"/><path d="M9 7.5h6"/>',
  chart: '<path d="M4 20V11M10 20V5M16 20v-8M21.5 20h-19"/>',
  apps: '<rect x="4" y="4" width="6.5" height="6.5" rx="1.8"/><rect x="13.5" y="4" width="6.5" height="6.5" rx="1.8"/><rect x="4" y="13.5" width="6.5" height="6.5" rx="1.8"/><rect x="13.5" y="13.5" width="6.5" height="6.5" rx="1.8"/>',
  teacher: '<rect x="3" y="4" width="18" height="12" rx="1.6"/><path d="M8 20.5l4-4.5 4 4.5M7 8h6M7 11.5h4"/>',
  clipboard: '<rect x="5" y="4.5" width="14" height="17" rx="2"/><path d="M9 4.5V3h6v1.5M8.5 10h7M8.5 14h7M8.5 18h4"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.6v.4"/>',
  globe: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.8 3 2.8 15 0 18M12 3c-2.8 3-2.8 15 0 18"/>',
  print: '<path d="M7 8V3.5h10V8"/><rect x="3.5" y="8" width="17" height="8" rx="2"/><path d="M7 13.5h10v7H7z"/>',
  copy: '<rect x="8.5" y="8.5" width="11" height="12" rx="2"/><path d="M15.5 8.5V5A1.5 1.5 0 0 0 14 3.5H6A1.5 1.5 0 0 0 4.5 5v10A1.5 1.5 0 0 0 6 16.5h2.5"/>',
  share: '<circle cx="18" cy="5.5" r="2.5"/><circle cx="6" cy="12" r="2.5"/><circle cx="18" cy="18.5" r="2.5"/><path d="m8.2 10.8 7.6-4.1M8.2 13.2l7.6 4.1"/>',
  train: '<path d="M3.5 16.5V9a2.5 2.5 0 0 1 2.5-2.5h7v10M13 9.5h4.5l3 3.5v3.5h-17"/><circle cx="7.5" cy="18.3" r="2"/><circle cx="16.5" cy="18.3" r="2"/><path d="M6.5 6.5V3.5h3v3"/>',
  close: '<path d="M6 6l12 12M18 6 6 18"/>',
  moon: '<path d="M19.5 14.5A8 8 0 1 1 9.5 4.5a6.5 6.5 0 0 0 10 10z"/>',
  textsize: '<path d="M3 19 8 6l5 13M4.8 14.5h6.4M14.5 19l3.5-9 3.5 9M15.5 16.5h5"/>',
  trash: '<path d="M4 7h16M9 7V4.5h6V7M6.5 7l1 13h9l1-13"/>',
  cloud: '<path d="M7 18.5h10a4 4 0 0 0 .5-8 5.5 5.5 0 0 0-10.6 1.4A3.4 3.4 0 0 0 7 18.5z"/><path d="m9.5 14 2 2 3.5-3.5"/>',
  shield: '<path d="M12 3 4.5 6v5.5c0 4.6 3.2 8.4 7.5 9.5 4.3-1.1 7.5-4.9 7.5-9.5V6z"/><path d="m8.8 12.2 2.2 2.2 4.3-4.3"/>',
  flag: '<path d="M5.5 21V4M5.5 4.5h11l-2 4 2 4h-11"/>',
  ear: '<path d="M7.5 9.5a4.5 4.5 0 1 1 9 .3c0 2.6-2.4 3.6-3.1 5.6-.7 2-2 3.6-4.2 3.6"/><path d="M10.2 10a2 2 0 1 1 4 0"/>',
  tap: '<path d="M9 11V5.5a1.5 1.5 0 0 1 3 0V11m0-1.5a1.5 1.5 0 0 1 3 0V11m0-.5a1.5 1.5 0 0 1 3 0V15a6 6 0 0 1-6 6h-1a6 6 0 0 1-5-2.7l-2-3.2a1.5 1.5 0 0 1 2.5-1.6L9 15"/>',
  bubble: '<path d="M4 5.5h16v10.5H10.5L6 20v-4H4z"/><path d="M8 9.5h8M8 12.5h5"/>',
  trophy: '<path d="M8 4h8v5a4 4 0 0 1-8 0zM8 6H4.8a3 3 0 0 0 3.2 4M16 6h3.2A3 3 0 0 1 16 10M12 13v4M8.5 20.5h7M10 17h4v3.5h-4z"/>',
  sticker: '<path d="M20 12a8 8 0 1 1-8-8h8z"/><path d="M20 12h-5a3 3 0 0 1-3-3V4"/>',
  sparkle: '<path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M18 6l-2.5 2.5M8.5 15.5 6 18"/>',
  wifi: '<path d="M4 9.5a12 12 0 0 1 16 0M7 12.7a7.5 7.5 0 0 1 10 0M10 15.8a3 3 0 0 1 4 0"/><circle cx="12" cy="19" r="1" fill="currentColor"/>',
  link: '<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1"/><path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>',
  hand: '<path d="M7 11.5V6a1.5 1.5 0 0 1 3 0v4.5V4.5a1.5 1.5 0 0 1 3 0v6V5.5a1.5 1.5 0 0 1 3 0v6.5-3a1.5 1.5 0 0 1 3 0V15a6.5 6.5 0 0 1-6.5 6.5H12A6.5 6.5 0 0 1 6.3 18L4 13.8a1.5 1.5 0 0 1 2.5-1.6z"/>',
};

export function icon(name, cls = '') {
  const body = IC[name] || IC.info;
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" class="icon ${cls}" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">${body}</svg>`;
}
export const iconNames = Object.keys(IC);

/** Small parent badge used on every parent card (adult + child silhouette). */
export function parentBadge() {
  return icon('parent', 'parent-icon');
}
