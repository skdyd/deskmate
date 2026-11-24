"""Deskmate patch: younger-sounding voice presets in the local Kokoro server (tts-local/server.py).

Presets mix Kokoro voice tensors and raise the pitch by resampling (formants go up with it, which is what makes
the voice sound younger); speed is pre-scaled so the tempo stays where it should be.
  python patch_voices_server.py <server.py>     re-runnable (replaces an older preset block)
"""
import re
import sys
from pathlib import Path

MARK = "# [voices patch]"
BLOCK = MARK + ''' presets: id -> (voices with weights, pitch in semitones, speed factor). American English (lang "a").
PRESETS = {
    "bella_up13": ([("af_bella", 1.0)], 1.3, 1.0),
    "bella_up15": ([("af_bella", 1.0)], 1.5, 1.0),
    "heart_up15": ([("af_heart", 1.0)], 1.5, 1.0),
    "bellasky_up15": ([("af_bella", 0.7), ("af_sky", 0.3)], 1.5, 1.0),
    "heartbella_up20": ([("af_heart", 0.5), ("af_bella", 0.5)], 2.0, 1.0),
}
VOICES = list(PRESETS) + [v for v in VOICES if v not in PRESETS]
# [/voices patch]
'''

SYNTH_OLD = '''        lang = voice[0] if voice and voice[0] in ("a", "b") else "a"
        with self._lock:  # torch inference is not safe to run concurrently from several threads
            pipe = self._pipeline(lang)
            chunks = []
            for _graphemes, _phonemes, audio in pipe(text, voice=voice, speed=speed):'''
SYNTH_NEW = '''        preset = PRESETS.get(voice)  # [voices patch]
        semis = preset[1] if preset else 0.0
        if preset:
            speed = speed * preset[2] / (2 ** (semis / 12))
        lang = "a" if preset else (voice[0] if voice and voice[0] in ("a", "b") else "a")
        with self._lock:  # torch inference is not safe to run concurrently from several threads
            pipe = self._pipeline(lang)
            if preset:
                parts = preset[0]
                voice = sum(pipe.load_single_voice(n) * w for n, w in parts) / sum(w for _, w in parts)
            chunks = []
            for _graphemes, _phonemes, audio in pipe(text, voice=voice, speed=speed):'''
CONCAT_OLD = '''        samples = np.concatenate(chunks) if chunks else np.zeros(0, dtype=np.float32)
'''
CONCAT_NEW = '''        samples = np.concatenate(chunks) if chunks else np.zeros(0, dtype=np.float32)
        if semis and len(samples):  # [voices patch] resample = pitch (and formants) up, shorter by the same factor
            n = int(len(samples) / (2 ** (semis / 12)))
            samples = np.interp(np.linspace(0, len(samples) - 1, n), np.arange(len(samples)), samples).astype(np.float32)
'''


def main(path: str) -> None:
    p = Path(path)
    src = p.read_text(encoding="utf-8")
    src = re.sub(re.escape(MARK) + r".*?# \[/voices patch\]\n", "", src, flags=re.S)
    anchor = "\n\nclass Synth:"
    if anchor not in src:
        raise SystemExit("anchor 'class Synth' not found")
    src = src.replace(anchor, "\n\n" + BLOCK + "\n\nclass Synth:", 1)
    if "[voices patch]\n        semis" not in src and "PRESETS.get(voice)" not in src:
        if SYNTH_OLD not in src or CONCAT_OLD not in src:
            raise SystemExit("synth anchors not found")
        src = src.replace(SYNTH_OLD, SYNTH_NEW, 1).replace(CONCAT_OLD, CONCAT_NEW, 1)
    p.write_text(src, encoding="utf-8")
    print("patched", p)


if __name__ == "__main__":
    main(sys.argv[1])
