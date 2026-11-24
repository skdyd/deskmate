"""Deskmate patch: clean text before the local Kokoro server speaks it (tts-local/server.py).

Drops what should not be read out loud: emoji and other pictographs, roleplay actions in *asterisks*,
markdown marks (* _ # ` ~ > |), double quotes, brackets, and URLs. Apostrophes inside words stay (you're).
The speech bubble is not touched; only the audio. When nothing is left, a short silence is returned instead of
an error, so the app does not fall back to the robotic browser voice.

  python patch_speech_clean.py <server.py>     re-runnable
"""
import re
import sys
from pathlib import Path

MARK = "# [speech-clean patch]"
BLOCK = MARK + r''' text cleanup before speaking (the bubble keeps the original text)
import re as _re
import unicodedata as _ud

_BOLD = _re.compile(r"(\*\*|__)(.+?)\1")                # **word** -> word
_ACTION = _re.compile(r"\*([^*\n]{1,80})\*")            # *giggles*, *waves at you*; one non-action word = emphasis
_ACTIONS = _re.compile(r"^(sighs?|giggles?|laughs?|chuckles?|smiles?|grins?|winks?|waves?|nods?|blushes|blush|pouts?|shrugs?|yawns?|gasps?|hums?|huffs?|snickers?|smirks?|beams?|stretches|stretch|blinks?|tilts|squeals?|whispers?|cheers?|claps?|hugs?|pats?|pokes?|giggling|laughing|sighing|smiling|grinning|winking|waving|nodding|blushing|pouting|yawning)$", _re.I)


def _action(m):
    inner = m.group(1).strip()
    return inner if _re.fullmatch(r"[A-Za-z'-]+", inner) and not _ACTIONS.match(inner) else " "
_URL = _re.compile(r"https?://\S+|www\.\S+")
_DROP = _re.compile(r"[*_#`~>|\"“”„«»\[\]{}<>‘‚]")
_SPACES = _re.compile(r"\s+")


def clean_for_speech(text: str) -> str:
    text = _BOLD.sub(lambda m: m.group(2), text)
    text = _ACTION.sub(_action, text)
    text = _URL.sub(" ", text)
    out = []
    for ch in text:
        cat = _ud.category(ch)
        # So = symbols incl. emoji, Sk = modifiers, Cf/Mn = ZWJ, variation selectors, skin-tone joins
        if cat in ("So", "Sk", "Cs", "Co", "Cf") or 0xFE00 <= ord(ch) <= 0xFE0F or 0x1F000 <= ord(ch) <= 0x1FAFF:
            out.append(" ")
        else:
            out.append(ch)
    text = "".join(out).replace("’", "'")
    text = _DROP.sub(" ", text)
    text = _re.sub(r"\s+([,.!?;:])", r"\1", _SPACES.sub(" ", text)).strip()
    return text if _re.search(r"[A-Za-z0-9぀-ヿ一-鿿]", text) else ""
# [/speech-clean patch]
'''

WAV_DEF = "    def wav(self, text: str, voice: str, speed: float) -> bytes:\n"
WAV_LINES = (
    "        text = clean_for_speech(text)  # [speech-clean patch]\n"
    "        if not text:  # [speech-clean patch] nothing speakable: short silence instead of an error\n"
    "            text = None  # [speech-clean patch]\n"
)
SILENCE = (
    "        if text is None:  # [speech-clean patch]\n"
    "            import numpy as np, soundfile as sf  # [speech-clean patch]\n"
    "            buf = io.BytesIO(); sf.write(buf, np.zeros(int(SAMPLE_RATE * 0.3), dtype=np.float32), SAMPLE_RATE, format=\"WAV\", subtype=\"PCM_16\")  # [speech-clean patch]\n"
    "            return buf.getvalue()  # [speech-clean patch]\n"
)


def main(path: str) -> None:
    p = Path(path)
    src = p.read_text(encoding="utf-8")
    src = re.sub(re.escape(MARK) + r".*?# \[/speech-clean patch\]\n\n\n", "", src, flags=re.S)
    src = "".join(l for l in src.splitlines(keepends=True) if "# [speech-clean patch]" not in l)
    anchor = "\nclass Synth:"
    if anchor not in src or WAV_DEF not in src:
        raise SystemExit("anchors not found")
    src = src.replace(anchor, "\n" + BLOCK + "\n\nclass Synth:", 1)
    src = src.replace(WAV_DEF, WAV_DEF + WAV_LINES + SILENCE, 1)
    p.write_text(src, encoding="utf-8")
    print("patched", p)


if __name__ == "__main__":
    main(sys.argv[1])
