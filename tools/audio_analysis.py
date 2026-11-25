"""Objective acoustic checks for generated speech clips (we cannot listen).

Used by make_audio.py (to pick the best phoneme candidate) and by
verify_audio.py (to log the final checks). Pure numpy/scipy.
"""
from __future__ import annotations

import numpy as np
from scipy.signal import lfilter, resample_poly


def to_float(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=np.float64)
    if x.ndim > 1:
        x = x.mean(axis=1)
    return x


def trim(x: np.ndarray, sr: int, top_db: float = 40.0, pad_ms: float = 15.0) -> np.ndarray:
    """Trim leading/trailing silence (frames quieter than peak - top_db)."""
    x = to_float(x)
    if x.size == 0:
        return x
    frame = max(1, int(sr * 0.010))
    n = len(x) // frame
    if n == 0:
        return x
    rms = np.sqrt(np.mean(x[: n * frame].reshape(n, frame) ** 2, axis=1) + 1e-12)
    db = 20 * np.log10(rms / (rms.max() + 1e-12))
    keep = np.where(db > -top_db)[0]
    if keep.size == 0:
        return x[:0]
    pad = int(sr * pad_ms / 1000)
    a = max(0, keep[0] * frame - pad)
    b = min(len(x), (keep[-1] + 1) * frame + pad)
    return x[a:b]


def frames(x: np.ndarray, sr: int, win_ms: float = 25.0, hop_ms: float = 10.0):
    win = int(sr * win_ms / 1000)
    hop = int(sr * hop_ms / 1000)
    if len(x) < win:
        x = np.pad(x, (0, win - len(x)))
    n = 1 + (len(x) - win) // hop
    idx = np.arange(win)[None, :] + hop * np.arange(n)[:, None]
    return x[idx], win, hop


def voicing(x: np.ndarray, sr: int):
    """Per-frame (is_voiced, f0) using normalised autocorrelation."""
    fr, win, _ = frames(x, sr, 40.0, 10.0)
    fr = fr * np.hanning(win)[None, :]
    rms = np.sqrt(np.mean(fr ** 2, axis=1) + 1e-12)
    loud = rms > (rms.max() * 0.08)
    lo, hi = int(sr / 400), int(sr / 70)
    voiced = np.zeros(len(fr), bool)
    f0 = np.zeros(len(fr))
    for i, f in enumerate(fr):
        if not loud[i]:
            continue
        ac = np.correlate(f, f, mode="full")[win - 1:]
        if ac[0] <= 0:
            continue
        ac = ac / ac[0]
        seg = ac[lo:hi]
        if seg.size == 0:
            continue
        k = int(np.argmax(seg))
        if seg[k] > 0.45:
            voiced[i] = True
            f0[i] = sr / (lo + k)
    return voiced, f0, loud


def spectral_centroid(x: np.ndarray, sr: int) -> float:
    fr, win, _ = frames(x, sr)
    fr = fr * np.hanning(win)[None, :]
    spec = np.abs(np.fft.rfft(fr, axis=1)) ** 2
    freqs = np.fft.rfftfreq(win, 1 / sr)
    w = spec.sum(axis=1)
    loud = w > w.max() * 0.05
    if not loud.any():
        return 0.0
    c = (spec[loud] * freqs[None, :]).sum(axis=1) / (w[loud] + 1e-12)
    return float(np.median(c))


def band_ratio(x: np.ndarray, sr: int, lo: float, hi: float) -> float:
    spec = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2
    freqs = np.fft.rfftfreq(len(x), 1 / sr)
    tot = spec.sum() + 1e-12
    return float(spec[(freqs >= lo) & (freqs < hi)].sum() / tot)


def _lpc(frame: np.ndarray, order: int) -> np.ndarray:
    r = np.correlate(frame, frame, mode="full")[len(frame) - 1: len(frame) + order]
    if r[0] <= 0:
        return np.zeros(order + 1)
    a = np.zeros(order + 1)
    a[0] = 1.0
    e = r[0]
    for i in range(1, order + 1):
        acc = r[i] + np.dot(a[1:i], r[i - 1:0:-1])
        k = -acc / e
        a_new = a.copy()
        a_new[1:i] = a[1:i] + k * a[i - 1:0:-1]
        a_new[i] = k
        a = a_new
        e *= 1 - k * k
        if e <= 0:
            break
    return a


def formants(x: np.ndarray, sr: int, lifter_ms: float = 1.8, nfft: int = 4096):
    """F1/F2 from the cepstrally smoothed spectral envelope of steady voiced frames.

    (LPC root-finding locks onto harmonics for high-pitched voices; envelope
    peak-picking in fixed bands was validated on synthetic vowels: mean error
    about 5 %.) Returns medians plus first-third / last-third medians.
    """
    x = to_float(x)
    voiced, _, _ = voicing(x, sr)
    win = int(sr * 0.04)
    hop = int(sr * 0.01)
    w = np.hanning(win)
    freqs = np.fft.rfftfreq(nfft, 1 / sr)
    cut = int(sr * lifter_ms / 1000)
    energies, res = [], []
    for j, i in enumerate(range(0, max(0, len(x) - win), hop)):
        if j >= len(voiced) or not voiced[j]:
            continue
        f = x[i:i + win] * w
        e = float(np.sqrt(np.mean(f ** 2)))
        spec = np.abs(np.fft.rfft(f, nfft)) + 1e-9
        c = np.fft.irfft(np.log(spec))
        c[cut:len(c) - cut] = 0
        env = np.fft.rfft(c).real
        m1 = (freqs >= 250) & (freqs <= 1150)
        f1 = freqs[np.argmax(np.where(m1, env, -1e9))]
        m2 = (freqs >= max(f1 + 350, 850)) & (freqs <= 3000)
        f2 = freqs[np.argmax(np.where(m2, env, -1e9))]
        energies.append(e)
        res.append((f1, f2))
    if not res:
        return None
    energies = np.array(energies)
    keep = energies > energies.max() * 10 ** (-12 / 20)  # steady part, within 12 dB of max
    arr = np.array(res)[keep]
    if len(arr) == 0:
        return None
    third = max(1, len(arr) // 3)
    return {
        "F1": float(np.median(arr[:, 0])), "F2": float(np.median(arr[:, 1])),
        "F1_start": float(np.median(arr[:third, 0])), "F1_end": float(np.median(arr[-third:, 0])),
        "F2_start": float(np.median(arr[:third, 1])), "F2_end": float(np.median(arr[-third:, 1])),
        "frames": int(len(arr)),
    }


def basic_stats(x: np.ndarray, sr: int) -> dict:
    x = to_float(x)
    dur = len(x) / sr if sr else 0
    rms = float(np.sqrt(np.mean(x ** 2))) if x.size else 0.0
    peak = float(np.max(np.abs(x))) if x.size else 0.0
    clipped = int(np.sum(np.abs(x) >= 0.999)) if x.size else 0
    return {
        "duration": dur,
        "rms_db": 20 * np.log10(rms + 1e-12),
        "peak_db": 20 * np.log10(peak + 1e-12),
        "clipped_samples": clipped,
    }


def frame_labels(x: np.ndarray, sr: int, hop_ms: float = 5.0):
    """Per-frame rms(dB re peak), voiced flag and spectral centroid at a fine hop."""
    x = to_float(x)
    win = int(sr * 0.025)
    hop = int(sr * hop_ms / 1000)
    lo, hi = int(sr / 400), int(sr / 70)
    n = max(0, 1 + (len(x) - int(sr * 0.04)) // hop)
    rms, voiced, cen = [], [], []
    freqs = np.fft.rfftfreq(win, 1 / sr)
    for j in range(n):
        i = j * hop
        f = x[i:i + win] * np.hanning(win)
        r = float(np.sqrt(np.mean(f ** 2)) + 1e-12)
        sp = np.abs(np.fft.rfft(f)) ** 2
        cen.append(float((sp * freqs).sum() / (sp.sum() + 1e-12)))
        g = x[i:i + int(sr * 0.04)]
        g = g * np.hanning(len(g))
        ac = np.correlate(g, g, mode="full")[len(g) - 1:]
        vv = False
        if ac[0] > 0:
            seg = ac[lo:hi] / ac[0]
            vv = seg.size > 0 and float(seg.max()) > 0.45
        rms.append(r)
        voiced.append(vv)
    rms = np.array(rms)
    db = 20 * np.log10(rms / (rms.max() + 1e-12)) if len(rms) else rms
    return db, np.array(voiced, bool), np.array(cen), hop


def _runs(mask: np.ndarray):
    runs, start = [], None
    for i, m in enumerate(list(mask) + [False]):
        if m and start is None:
            start = i
        elif not m and start is not None:
            runs.append((start, i))
            start = None
    return runs


def extract_fricative(x: np.ndarray, sr: int, min_centroid: float = 3000) -> np.ndarray:
    """Longest run of loud, unvoiced, high-centroid frames (e.g. the /s/ in 'the sun')."""
    db, v, cen, hop = frame_labels(x, sr)
    mask = (db > -35) & (~v) & (cen > min_centroid)
    runs = _runs(mask)
    if not runs:
        return x[:0]
    a, b = max(runs, key=lambda r: r[1] - r[0])
    return to_float(x)[a * hop: b * hop + int(sr * 0.02)]


def extract_stop(x: np.ndarray, sr: int) -> np.ndarray:
    """Burst + aspiration before the stressed vowel of a carrier word (e.g. /t/ in 'the tap')."""
    db, v, cen, hop = frame_labels(x, sr)
    vruns = [r for r in _runs(v & (db > -30))]
    if not vruns:
        return x[:0]
    vs = max(vruns, key=lambda r: r[1] - r[0])[0]  # onset of the main vowel
    i = vs - 1
    while i > 0 and (not v[i]) and db[i] > -42:
        i -= 1
    start = max(0, (i + 1) * hop - int(sr * 0.004))
    end = max(start, vs * hop - int(sr * 0.006))
    return to_float(x)[start:end]


def describe_phoneme(x: np.ndarray, sr: int) -> dict:
    x = to_float(x)
    if x.size < int(sr * 0.05):
        x = np.pad(x, (0, int(sr * 0.05) - x.size))
    v, f0, loud = voicing(x, sr)
    vf = float(v[loud].mean()) if loud.any() else 0.0
    # longest run of voiced frames (10 ms hop) -> detects an added vowel
    run = best = 0
    for b in v:
        run = run + 1 if b else 0
        best = max(best, run)
    d = basic_stats(x, sr)
    d.update({
        "voiced_fraction": vf,
        "longest_voiced_ms": best * 10,
        "centroid_hz": spectral_centroid(x, sr),
        "low_ratio_0_500": band_ratio(x, sr, 0, 500),
        "high_ratio_3k_plus": band_ratio(x, sr, 3000, sr / 2),
    })
    fm = formants(x, sr)
    if fm:
        d.update(fm)
    return d


# Expected acoustic profile of each pure phoneme (female adult voice).
RULES = {
    # continuous unvoiced fricative: no voicing, energy high in spectrum
    "s": dict(dur=(0.55, 0.95), voiced_max=0.15, centroid_min=3500),
    # stops: short, no vowel attached (no long voiced stretch)
    # (an upper centroid limit keeps /t/ and /p/ from sounding hissy, like "ts")
    "t": dict(dur=(0.05, 0.40), voiced_ms_max=60, centroid_min=1500, centroid_max=6000),
    "p": dict(dur=(0.05, 0.40), voiced_ms_max=60, centroid_max=5000),
    # vowels: voiced, steady (not a diphthong letter-name)
    "a": dict(dur=(0.55, 0.95), voiced_min=0.7, F1=(650, 1150), F2=(1450, 2350), F2_move_max=350),
    "i": dict(dur=(0.55, 0.95), voiced_min=0.7, F1=(300, 650), F2=(1800, 3000), F2_move_max=350, F1_move_max=200),
    # nasal: voiced murmur, energy concentrated low, no vowel onset
    "n": dict(dur=(0.55, 0.95), voiced_min=0.6, low_min=0.45, F1_start_max=480),
}


def check_phoneme(letter: str, d: dict) -> list[str]:
    """Return a list of problems (empty list = passes)."""
    r = RULES[letter]
    p = []
    lo, hi = r["dur"]
    if not lo <= d["duration"] <= hi:
        p.append(f"duration {d['duration']:.2f}s not in {lo}-{hi}")
    if "voiced_max" in r and d["voiced_fraction"] > r["voiced_max"]:
        p.append(f"voiced {d['voiced_fraction']:.2f} > {r['voiced_max']}")
    if "voiced_min" in r and d["voiced_fraction"] < r["voiced_min"]:
        p.append(f"voiced {d['voiced_fraction']:.2f} < {r['voiced_min']}")
    if "voiced_ms_max" in r and d["longest_voiced_ms"] > r["voiced_ms_max"]:
        p.append(f"voiced stretch {d['longest_voiced_ms']}ms > {r['voiced_ms_max']}ms (vowel added?)")
    if "centroid_min" in r and d["centroid_hz"] < r["centroid_min"]:
        p.append(f"centroid {d['centroid_hz']:.0f}Hz < {r['centroid_min']}")
    if "centroid_max" in r and d["centroid_hz"] > r["centroid_max"]:
        p.append(f"centroid {d['centroid_hz']:.0f}Hz > {r['centroid_max']} (too hissy for a stop)")
    if "low_min" in r and d["low_ratio_0_500"] < r["low_min"]:
        p.append(f"low-band ratio {d['low_ratio_0_500']:.2f} < {r['low_min']}")
    for k in ("F1", "F2"):
        if k in r:
            if k not in d:
                p.append(f"{k} not measurable")
            elif not r[k][0] <= d[k] <= r[k][1]:
                p.append(f"{k} {d[k]:.0f}Hz not in {r[k]}")
    if "F2_move_max" in r and "F2_start" in d:
        mv = abs(d["F2_end"] - d["F2_start"])
        if mv > r["F2_move_max"]:
            p.append(f"F2 moves {mv:.0f}Hz (diphthong / letter name?)")
    if "F1_move_max" in r and "F1_start" in d:
        mv = abs(d["F1_end"] - d["F1_start"])
        if mv > r["F1_move_max"]:
            p.append(f"F1 moves {mv:.0f}Hz (diphthong / letter name?)")
    if "F1_start_max" in r and "F1_start" in d and d["F1_start"] > r["F1_start_max"]:
        p.append(f"starts with a vowel-like F1 {d['F1_start']:.0f}Hz (letter name 'en'?)")
    return p
