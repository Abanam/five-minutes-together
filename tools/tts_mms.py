"""Arabic phrase synthesis with Meta MMS-TTS (facebook/mms-tts-ara, VITS, CC BY-NC 4.0).

Run with the .venv-mms interpreter (it reuses the machine's PyTorch):
    .venv-mms/Scripts/python.exe tools/tts_mms.py requests.json out_dir

requests.json = [{"key": "<file stem>", "text": "<undiacritised Arabic phrase>"}, ...]
Writes out_dir/<key>.wav (16 kHz mono float). Existing files are skipped (cache).
"""
import json
import os
import sys

import numpy as np
import soundfile as sf
import torch
from transformers import AutoTokenizer, VitsModel

MODEL = "facebook/mms-tts-ara"
CACHE = os.path.join(os.path.expanduser("~"), ".cache", "fmt-models", "hf")


def main(req_path: str, out_dir: str, rate: float = 0.88) -> None:
    reqs = json.load(open(req_path, encoding="utf-8-sig"))
    os.makedirs(out_dir, exist_ok=True)
    todo = [r for r in reqs if not os.path.exists(os.path.join(out_dir, r["key"] + ".wav"))]
    print(f"MMS: {len(reqs)} phrases requested, {len(todo)} to synthesise")
    if not todo:
        return
    tok = AutoTokenizer.from_pretrained(MODEL, cache_dir=CACHE)
    model = VitsModel.from_pretrained(MODEL, cache_dir=CACHE)
    model.eval()
    model.speaking_rate = rate  # < 1 = a little slower and clearer for parents
    model.noise_scale = 0.5
    model.noise_scale_duration = 0.6
    sr = model.config.sampling_rate
    for i, r in enumerate(todo):
        torch.manual_seed(1234)  # deterministic output
        ids = tok(r["text"], return_tensors="pt")
        if ids["input_ids"].shape[1] == 0:
            raise ValueError(f"empty tokens for {r['key']}: {r['text']!r}")
        with torch.no_grad():
            wav = model(**ids).waveform[0].cpu().numpy().astype(np.float32)
        sf.write(os.path.join(out_dir, r["key"] + ".wav"), wav, sr)
        if (i + 1) % 20 == 0:
            print(f"  {i + 1}/{len(todo)}")
    print("MMS: done")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 0.88)
