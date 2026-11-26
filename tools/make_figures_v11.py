"""Figures for the report (brief §8.4): PNG at 300 dpi, 6.5 in wide, white background, black and grey only,
sans-serif labels of at least 9 pt, no title inside the image, and a CSV of the plotted data next to each.

    .venv/Scripts/python.exe tools/make_figures_v11.py

fig4_letter_sounds_v1.0_v1.1.png    rows /s/ /æ/ /t/ /p/ /ɪ/ /n/; columns Version 1.0 | Version 1.1; each cell a waveform
                                    above a spectrogram (0–8 kHz) on the same 0–1.0 s time axis
fig4b_arabic_intelligibility_v1.0_v1.1.png   paired dots: Whisper similarity of the 107 Arabic clips, v1.0 vs v1.1,
                                    dashed line at 0.80
Data: deliverables/evidence/v1.0/audio (v1.0 clips), app/audio (v1.1 clips),
      deliverables/evidence/v1.0/remeasured/audio_verification.json and tools/audio_verification.json (similarities).
"""
from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.gridspec import GridSpec  # noqa: E402
from scipy.signal import spectrogram  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "deliverables" / "figures"
V10 = ROOT / "deliverables" / "evidence" / "v1.0" / "audio"
V11 = ROOT / "app" / "audio"
SR = 24000
SOUNDS = [("s", "/s/"), ("a", "/æ/"), ("t", "/t/"), ("p", "/p/"), ("i", "/ɪ/"), ("n", "/n/")]
plt.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Arial", "Liberation Sans", "DejaVu Sans"],
                     "font.size": 9, "axes.labelsize": 9, "xtick.labelsize": 9, "ytick.labelsize": 9,
                     "axes.edgecolor": "black", "axes.linewidth": 0.6, "savefig.facecolor": "white"})


def decode(path: Path) -> np.ndarray:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                         check=True, capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32).copy()


def fig_letters() -> None:
    fig = plt.figure(figsize=(6.5, 8.6))
    gs = GridSpec(len(SOUNDS) * 2, 2, figure=fig, height_ratios=[1, 2.2] * len(SOUNDS), hspace=0.12, wspace=0.12,
                  left=0.1, right=0.98, top=0.965, bottom=0.055)
    rows = []
    for r, (s, ipa) in enumerate(SOUNDS):
        for col, (label, folder) in enumerate((("Version 1.0", V10), ("Version 1.1", V11))):
            y = decode(folder / "en" / f"ph-{s}.mp3")[: SR]          # the same 0–1.0 s window for every cell
            t = np.arange(len(y)) / SR
            peak = float(np.max(np.abs(y))) or 1.0
            ax = fig.add_subplot(gs[2 * r, col])
            ax.plot(t, y / peak, color="black", linewidth=0.35)
            ax.set_xlim(0, 1.0)
            ax.set_ylim(-1.05, 1.05)
            ax.set_xticks([])
            ax.set_yticks([])
            if r == 0:
                ax.set_title(label, fontsize=10, pad=4)
            if col == 0:
                ax.set_ylabel(ipa, rotation=0, fontsize=11, labelpad=16, va="center")
            f, tt, sxx = spectrogram(y, SR, window="hann", nperseg=512, noverlap=448)
            db = 10 * np.log10(sxx + 1e-12)
            keep = f <= 8000
            ax2 = fig.add_subplot(gs[2 * r + 1, col])
            ax2.pcolormesh(tt, f[keep] / 1000, db[keep], cmap="Greys", vmin=db.max() - 60, vmax=db.max(), shading="auto",
                           rasterized=True)
            ax2.set_xlim(0, 1.0)
            ax2.set_ylim(0, 8)
            ax2.set_yticks([0, 4, 8] if col == 0 else [])
            if col == 0:
                ax2.set_ylabel("kHz")
            ax2.set_xticks([0, 0.25, 0.5, 0.75, 1.0] if r == len(SOUNDS) - 1 else [])
            if r == len(SOUNDS) - 1:
                ax2.set_xticklabels(["0", "0.25", "0.5", "0.75", "1"])
                ax2.set_xlabel("Time (s)")
            # plotted data for the CSV: waveform peaks per 1 ms, spectrogram levels per 20 ms × 500 Hz
            ms = int(SR / 1000)
            for k in range(0, len(y) // ms):
                rows.append([ipa, label, "waveform peak (normalised)", round(k / 1000, 3), "", round(float(np.max(np.abs(y[k * ms:(k + 1) * ms]))) / peak, 4)])
            for ti in range(0, len(tt), 5):
                for fi in range(0, int(keep.sum()), 11):
                    rows.append([ipa, label, "spectrogram level (dB)", round(float(tt[ti]), 3), round(float(f[fi])), round(float(db[fi, ti]), 1)])
    OUT.mkdir(parents=True, exist_ok=True)
    png = OUT / "fig4_letter_sounds_v1.0_v1.1.png"
    fig.savefig(png, dpi=300)
    plt.close(fig)
    with open(png.with_suffix(".csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["sound", "version", "series", "time_s", "frequency_hz", "value"])
        w.writerows(rows)
    print("wrote", png.relative_to(ROOT), "and its CSV")


def fig_arabic() -> None:
    a = json.loads((ROOT / "deliverables" / "evidence" / "v1.0" / "remeasured" / "audio_verification.json").read_text(encoding="utf-8"))["whisper_ar"]
    b = json.loads((ROOT / "tools" / "audio_verification.json").read_text(encoding="utf-8"))["whisper_ar"]
    ids = sorted(set(a) & set(b), key=lambda k: a[k]["similarity"])
    va = np.array([a[k]["similarity"] for k in ids])
    vb = np.array([b[k]["similarity"] for k in ids])
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    rng = np.random.default_rng(3)
    jit = rng.uniform(-0.06, 0.06, len(ids))
    for i in range(len(ids)):
        ax.plot([0 + jit[i], 1 + jit[i]], [va[i], vb[i]], color="0.75", linewidth=0.5, zorder=1)
    ax.scatter(0 + jit, va, s=9, color="0.45", zorder=2, linewidths=0)
    ax.scatter(1 + jit, vb, s=9, color="black", zorder=2, linewidths=0)
    ax.boxplot([va, vb], positions=[-0.3, 1.3], widths=0.14, showfliers=False,
               medianprops={"color": "black"}, boxprops={"color": "black"}, whiskerprops={"color": "black"}, capprops={"color": "black"})
    ax.axhline(0.80, color="black", linestyle="--", linewidth=0.8)
    ax.text(1.58, 0.808, "0.80", ha="right", va="bottom", fontsize=9)
    ax.set_xlim(-0.55, 1.6)
    ax.set_ylim(min(0.3, float(min(va.min(), vb.min())) - 0.02), 1.01)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["Version 1.0", "Version 1.1"])
    ax.set_ylabel(f"Whisper similarity to the script (n = {len(ids)})")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    fig.tight_layout()
    png = OUT / "fig4b_arabic_intelligibility_v1.0_v1.1.png"
    fig.savefig(png, dpi=300)
    plt.close(fig)
    with open(png.with_suffix(".csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["clip", "similarity_v1.0", "similarity_v1.1", "change"])
        for k, x, y in zip(ids, va, vb):
            w.writerow([k, f"{x:.3f}", f"{y:.3f}", f"{y - x:+.3f}"])
    print("wrote", png.relative_to(ROOT), "and its CSV")


if __name__ == "__main__":
    fig_letters()
    fig_arabic()
