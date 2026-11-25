"""Prepare the self-hosted web fonts for the app (run once; output is committed).

* Andika (SIL Global, OFL 1.1 with Reserved Font Names "Andika" and "SIL"):
  the OFL-FAQ (2.6) says subsetting is a modification that cannot keep a
  Reserved Font Name, so we ship SIL's own, unmodified WOFF2 files from the
  official 7.000 release.
* Baloo Bhaijaan 2 (Ek Type / The Baloo 2 Project Authors, OFL 1.1, no RFN):
  subset to Arabic + Arabic punctuation/digits (no Latin letters, so every
  Latin letter falls back to Andika and always shows a single-storey "a").

Sources are downloaded by the build (see CREDITS.md):
  tools/fonts-src/andika7/Andika-7.000/web/*.woff2      (github.com/silnrsi/font-andika v7.000)
  tools/fonts-src/BalooBhaijaan2-wght.ttf               (github.com/google/fonts ofl/baloobhaijaan2)
"""
import shutil
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "tools" / "fonts-src"
OUT = ROOT / "app" / "fonts"
OUT.mkdir(parents=True, exist_ok=True)

# 1. Andika: copy official webfonts unchanged + licence
andika_web = SRC / "andika7" / "Andika-7.000" / "web"
# one weight only (Medium) so slow connections download a single Andika file
for old in ("Andika-Regular.woff2", "Andika-Bold.woff2"):
    (OUT / old).unlink(missing_ok=True)
shutil.copyfile(andika_web / "Andika-Medium.woff2", OUT / "Andika-Medium.woff2")
shutil.copyfile(SRC / "andika7" / "Andika-7.000" / "OFL.txt", OUT / "Andika-OFL.txt")

# 2. Baloo Bhaijaan 2: Arabic subset, keep the weight axis
unicodes = []
ranges = [
    (0x0020, 0x0020), (0x00A0, 0x00A0),
    (0x0021, 0x002F), (0x003A, 0x0040), (0x005B, 0x0060), (0x007B, 0x007E),  # ASCII punctuation
    (0x0030, 0x0039),            # western digits
    (0x00AB, 0x00AB), (0x00BB, 0x00BB), (0x00B7, 0x00B7), (0x00D7, 0x00D7),
    (0x0600, 0x06FF),            # Arabic
    (0x0750, 0x077F),            # Arabic Supplement
    (0x08A0, 0x08FF),            # Arabic Extended-A
    (0xFB50, 0xFDFF),            # Presentation Forms-A
    (0xFE70, 0xFEFF),            # Presentation Forms-B
    (0x200C, 0x200F), (0x2010, 0x2027), (0x2030, 0x203A), (0x2066, 0x2069),
    (0x2212, 0x2212), (0x25CC, 0x25CC),
]
for a, b in ranges:
    unicodes.extend(range(a, b + 1))

src_ttf = SRC / "BalooBhaijaan2-wght.ttf"
font = TTFont(src_ttf)
cmap = font.getBestCmap()
unicodes = [u for u in unicodes if u in cmap]
opts = subset.Options()
opts.flavor = "woff2"
opts.layout_features = ["*"]
opts.name_IDs = ["*"]
opts.name_languages = ["*"]
opts.notdef_outline = True
opts.glyph_names = False
opts.hinting = False
sub = subset.Subsetter(options=opts)
sub.populate(unicodes=unicodes)
sub.subset(font)
dest = OUT / "BalooBhaijaan2-Arabic.woff2"
font.flavor = "woff2"
font.save(dest)
shutil.copyfile(SRC / "BalooBhaijaan2-OFL.txt", OUT / "BalooBhaijaan2-OFL.txt")

for f in sorted(OUT.iterdir()):
    print(f"{f.name:34s} {f.stat().st_size/1024:8.1f} KB")
