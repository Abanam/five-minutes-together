"""Minimal espeak-ng synthesiser via ctypes, for phoneme-mode input ([[...]]).

Uses the espeak-ng library and data bundled with the `espeakng-loader`
package (installed with kokoro-onnx). espeak-ng is GPL-3.0; the audio it
produces is not covered by the GPL.
"""
from __future__ import annotations

import ctypes
import numpy as np
import espeakng_loader

_AUDIO_OUTPUT_SYNCHRONOUS = 2
_espeakCHARS_UTF8 = 1
_espeakPHONEMES = 0x100
_espeakRATE, _espeakVOLUME, _espeakPITCH, _espeakRANGE = 1, 2, 3, 4

_lib = None
_sr = None
_chunks: list[np.ndarray] = []

_CB = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.POINTER(ctypes.c_short), ctypes.c_int, ctypes.c_void_p)


@_CB
def _callback(wav, numsamples, events):  # noqa: ANN001
    if numsamples > 0 and wav:
        _chunks.append(np.ctypeslib.as_array(wav, shape=(numsamples,)).copy())
    return 0


def _init():
    global _lib, _sr
    if _lib is not None:
        return
    espeakng_loader.make_library_available()
    _lib = ctypes.CDLL(espeakng_loader.get_library_path())
    _lib.espeak_Initialize.restype = ctypes.c_int
    _sr = _lib.espeak_Initialize(_AUDIO_OUTPUT_SYNCHRONOUS, 500, espeakng_loader.get_data_path().encode(), 0)
    if _sr <= 0:
        raise RuntimeError("espeak-ng failed to initialise")
    _lib.espeak_SetSynthCallback(_callback)


def synth(text: str, voice: str = "en-us", rate: int = 80, pitch: int = 50, rng: int = 30) -> tuple[np.ndarray, int]:
    """Synthesise text (may contain [[phoneme mnemonics]]). Returns float32 audio, sample rate."""
    _init()
    _chunks.clear()
    if _lib.espeak_SetVoiceByName(voice.encode()) != 0:
        raise RuntimeError(f"espeak-ng voice {voice!r} not found")
    _lib.espeak_SetParameter(_espeakRATE, rate, 0)
    _lib.espeak_SetParameter(_espeakPITCH, pitch, 0)
    _lib.espeak_SetParameter(_espeakRANGE, rng, 0)
    _lib.espeak_SetParameter(_espeakVOLUME, 100, 0)
    b = text.encode("utf-8") + b"\0"
    err = _lib.espeak_Synth(b, len(b), 0, 1, 0, _espeakCHARS_UTF8 | _espeakPHONEMES, None, None)
    if err != 0:
        raise RuntimeError(f"espeak_Synth error {err}")
    _lib.espeak_Synchronize()
    y = np.concatenate(_chunks) if _chunks else np.zeros(0, np.int16)
    return (y.astype(np.float32) / 32768.0), _sr
