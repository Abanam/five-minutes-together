"""Summarise the reviewers' "Copy my feedback" texts (brief §13). Nothing is invented: a missing rating stays missing.

    .venv/Scripts/python.exe tools/summarise_reviews.py

Reads   deliverables/reviews/v1.0/*.txt and deliverables/reviews/v1.1/*.txt (one reviewer per file)
Writes  deliverables/reviews-summary.md: per item the mean, SD and n for v1.0 and v1.1 and the change;
        A1–A3 (v1.1 only); comments grouped by item with the reviewer's role only (never a name).
A line looks like "3. Cultural suitability: 4/5 – comment" (or "A1. English sounds and words: 4/5 – comment");
"–" means the reviewer gave no rating. The SD is the sample standard deviation (n − 1); it needs n ≥ 2.
"""
from __future__ import annotations

import re
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REV = ROOT / "deliverables" / "reviews"
OUT = ROOT / "deliverables" / "reviews-summary.md"
ITEMS = [("1", "Clarity for parents"), ("2", "Ease for children"), ("3", "Cultural suitability"), ("4", "Accessibility"),
         ("5", "Learning value"), ("6", "Daily routine"), ("7", "Safety and privacy"), ("8", "Technical problems")]
AUDIO = [("A1", "English sounds and words"), ("A2", "Arabic voice"), ("A3", "Pronunciation compared with version 1.0")]
LINE = re.compile(r"^(A?[0-9]+)\.\s+([^:]+):\s+(?:([1-5])/5|–|-)(?:\s+[–-]\s+(.*))?\s*$")


def parse(path: Path) -> dict:
    text = path.read_text(encoding="utf-8-sig")
    out = {"file": path.name, "role": None, "version": None, "ratings": {}, "comments": {}, "unparsed": []}
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        m = re.match(r"^5 Minutes Together v([0-9.]+)", line)
        if m:
            out["version"] = m.group(1)
            continue
        if line.startswith("Role:"):
            out["role"] = line[5:].strip() or None
            continue
        if line.startswith("Date:"):
            continue
        m = LINE.match(line)
        if m:
            key, _, score, comment = m.groups()
            if score:
                out["ratings"][key] = int(score)
            if comment:
                out["comments"][key] = comment.strip()
        else:
            out["unparsed"].append(line)
    return out


def stats(vals: list[int]) -> str:
    if not vals:
        return "– (n = 0)"
    sd = f"{statistics.stdev(vals):.2f}" if len(vals) > 1 else "–"
    return f"{statistics.mean(vals):.2f} (SD {sd}, n = {len(vals)})"


def main() -> None:
    data = {v: [parse(p) for p in sorted((REV / v).glob("*.txt")) if p.name.lower() != "readme.txt"] for v in ("v1.0", "v1.1")}
    lines = ["# Reviewer feedback summary", "",
             "Made by `tools/summarise_reviews.py` from the reviewers' own \"Copy my feedback\" texts in `deliverables/reviews/`. "
             "Ratings are 1–5 (5 = strongly agree; for A3, 5 = much better than v1.0). Missing ratings are left out, never filled in. "
             "Reviewers are identified by role only.", "",
             f"Files read: v1.0 – {len(data['v1.0'])}, v1.1 – {len(data['v1.1'])}.", ""]
    warn = [f"{v}/{r['file']}: header says v{r['version']}" for v, rs in data.items() for r in rs if r["version"] and "v" + r["version"] != v]
    warn += [f"{v}/{r['file']}: {len(r['unparsed'])} line(s) not understood" for v, rs in data.items() for r in rs if r["unparsed"]]
    if warn:
        lines += ["**Check these files:** " + "; ".join(warn), ""]
    lines += ["## The eight checklist items", "", "| Item | v1.0 mean (SD, n) | v1.1 mean (SD, n) | Change in mean |", "|---|---|---|---|"]
    for key, label in ITEMS:
        a = [r["ratings"][key] for r in data["v1.0"] if key in r["ratings"]]
        b = [r["ratings"][key] for r in data["v1.1"] if key in r["ratings"]]
        change = f"{statistics.mean(b) - statistics.mean(a):+.2f}" if a and b else "–"
        lines.append(f"| {key}. {label} | {stats(a)} | {stats(b)} | {change} |")
    lines += ["", "## Audio re-check (v1.1 only)", "", "| Item | v1.1 mean (SD, n) |", "|---|---|"]
    for key, label in AUDIO:
        b = [r["ratings"][key] for r in data["v1.1"] if key in r["ratings"]]
        lines.append(f"| {key}. {label} | {stats(b)} |")
    lines += ["", "## Comments by item", ""]
    for key, label in ITEMS + AUDIO:
        cs = [(v, r["role"] or "role not given", r["comments"][key]) for v, rs in data.items() for r in rs if key in r["comments"]]
        if cs:
            lines += [f"**{key}. {label}**", ""] + [f"- {v}, {role}: {c}" for v, role, c in cs] + [""]
    if not any(r["comments"] for rs in data.values() for r in rs):
        lines += ["No comments yet.", ""]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} (v1.0: {len(data['v1.0'])} file(s), v1.1: {len(data['v1.1'])} file(s))")


if __name__ == "__main__":
    main()
