"""Deskmate patch: voice dropdown next to the character dropdown.

The choice is kept in localStorage and sent to the main process, which sets DESKMATE_TTS_VOICE (read on every
line she says, the grammar correction included). The preset voices live in tts-local/server.py
(patch_voices_server.py), so run that one too.

  python patch_voices.py <app.asar>     patch in place (first run backs up to app.asar.bak-voices); re-runnable
"""
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
MARK = "[voices patch]"

VOICE_OPTIONS = [
    ("af_heart", "heart 원본"),
    ("af_bella", "bella 원본"),
    ("heart_up15", "heart 밝게"),
    ("bella_up13", "bella 밝게 1.3"),
    ("bella_up15", "bella 밝게 1.5"),
    ("bellasky_up15", "bella+sky"),
    ("heartbella_up20", "heart+bella"),
]

RENDERER = """// [voices patch] voice dropdown next to the character dropdown; the choice is kept and sent to the main process.
const VOICE_KEY = "deskmate.voice";
const voiceSelect = document.createElement("select");
voiceSelect.id = "voice";
voiceSelect.title = "목소리 바꾸기";
for (const [id, label] of %s) {
	const opt = document.createElement("option");
	opt.value = id;
	opt.textContent = label;
	voiceSelect.appendChild(opt);
}
{
	const saved = localStorage.getItem(VOICE_KEY);
	if (saved && [...voiceSelect.options].some((o) => o.value === saved)) voiceSelect.value = saved;
	const voiceStyle = document.createElement("style");
	voiceStyle.textContent = "#voice { font-size: 11px; padding: 2px 6px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.12); background: rgba(255,255,255,0.08); color: var(--ink); outline: none; }";
	document.head.appendChild(voiceStyle);
	characterSelect.insertAdjacentElement("afterend", voiceSelect);
	api.setVoice?.(voiceSelect.value);
	voiceSelect.addEventListener("change", () => {
		localStorage.setItem(VOICE_KEY, voiceSelect.value);
		api.setVoice?.(voiceSelect.value);
	});
	// speaking speed (1 = Kokoro's normal pace); slower is easier to follow when listening practice
	const SPEED_KEY = "deskmate.voiceSpeed";
	const speedSelect = document.createElement("select");
	speedSelect.id = "voice-speed";
	speedSelect.title = "말 속도";
	for (const s of ["0.7", "0.75", "0.8", "0.85", "0.9", "0.95", "1"]) {
		const opt = document.createElement("option");
		opt.value = s;
		opt.textContent = `속도 ${s}`;
		speedSelect.appendChild(opt);
	}
	const savedSpeed = localStorage.getItem(SPEED_KEY);
	speedSelect.value = [...speedSelect.options].some((o) => o.value === savedSpeed) ? savedSpeed : "0.85";
	voiceStyle.textContent += " #voice-speed { font-size: 11px; padding: 2px 4px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.12); background: rgba(255,255,255,0.08); color: var(--ink); outline: none; }";
	voiceSelect.insertAdjacentElement("afterend", speedSelect);
	api.setVoiceSpeed?.(speedSelect.value);
	speedSelect.addEventListener("change", () => {
		localStorage.setItem(SPEED_KEY, speedSelect.value);
		api.setVoiceSpeed?.(speedSelect.value);
	});
}
// [/voices patch]
""" % repr([list(o) for o in VOICE_OPTIONS]).replace("'", '"')

# Same cleanup as tts-local/server.py (patch_speech_clean.py), for the browser fallback voice.
RENDERER += r"""// [voices patch] text cleanup for the browser fallback voice: no emoji, *actions*, markdown marks or quotes.
// one word in *stars* is emphasis (*very*) unless it is a stage direction; several words are always an action
const SPEECH_ACTIONS = /^(sighs?|giggles?|laughs?|chuckles?|smiles?|grins?|winks?|waves?|nods?|blushes|blush|pouts?|shrugs?|yawns?|gasps?|hums?|huffs?|snickers?|smirks?|beams?|stretches|stretch|blinks?|tilts|squeals?|whispers?|cheers?|claps?|hugs?|pats?|pokes?|giggling|laughing|sighing|smiling|grinning|winking|waving|nodding|blushing|pouting|yawning)$/i;
function speechClean(text) {
	return String(text ?? "")
		.replace(/(\*\*|__)(.+?)\1/g, "$2")
		.replace(/\*([^*\n]{1,80})\*/g, (_m, inner) => (/^[A-Za-z'-]+$/.test(inner.trim()) && !SPEECH_ACTIONS.test(inner.trim()) ? inner : " "))
		.replace(/https?:\/\/\S+|www\.\S+/g, " ")
		.replace(/[\p{Extended_Pictographic}\p{So}\p{Sk}‍︎️]/gu, " ")
		.replace(/’/g, "'")
		.replace(/[*_#`~>|"“”„«»\[\]{}<>‘‚]/g, " ")
		.replace(/\s+/g, " ")
		.replace(/\s+([,.!?;:])/g, "$1")
		.trim();
}
// [/voices patch]
"""
UTTER_OLD = "new SpeechSynthesisUtterance(text);"
UTTER_NEW = "new SpeechSynthesisUtterance(speechClean(text));"

MAIN = """// [voices patch] the voice dropdown sets the Kokoro voice (or preset) used for every line from now on.
electron.ipcMain.on("voice:set", (_event, voice) => {
	const v = String(voice ?? "").trim();
	if (/^[a-z0-9_]{2,40}$/i.test(v)) {
		process.env.DESKMATE_TTS_VOICE = v;
		console.log(`[voice] ${v}`);
	}
});
electron.ipcMain.on("voice:speed", (_event, speed) => {
	const s = Number(speed);
	if (s >= 0.5 && s <= 1.5) {
		process.env.DESKMATE_TTS_SPEED = String(s);
		console.log(`[voice] speed ${s}`);
	}
});
// [/voices patch]
"""

PRELOAD_LINE = ('\tsetVoice: (v) => electron.ipcRenderer.send("voice:set", v), // [voices patch]\n'
                '\tsetVoiceSpeed: (s) => electron.ipcRenderer.send("voice:speed", s), // [voices patch]\n')


def strip(src: str) -> str:
    return re.sub(r"// \[voices patch\].*?// \[/voices patch\]\n", "", src, flags=re.S)


def patch_renderer(src: str) -> str:
    src = strip(src)
    anchor = 'var characterSelect = document.getElementById("character");\n'
    if anchor not in src:
        raise SystemExit("renderer anchor not found")
    # placed after the last top-level `var` of the block so `api` and `characterSelect` exist
    end = src.index("var config;\n")
    src = src[:end] + RENDERER + src[end:]
    if UTTER_NEW not in src:
        if UTTER_OLD not in src:
            raise SystemExit("browser voice anchor not found")
        src = src.replace(UTTER_OLD, UTTER_NEW, 1)
    return src


def patch_main(src: str) -> str:
    src = strip(src)
    anchor = 'electron.ipcMain.handle("character:set"'
    if anchor not in src:
        raise SystemExit("main anchor not found")
    return src.replace(anchor, MAIN + anchor, 1)


def patch_preload(src: str) -> str:
    src = "".join(l for l in src.splitlines(keepends=True) if "// [voices patch]" not in l)
    anchor = '\tsetCharacter: (id) => electron.ipcRenderer.invoke("character:set", id),\n'
    if anchor not in src:
        raise SystemExit("preload anchor not found")
    return src.replace(anchor, anchor + PRELOAD_LINE, 1)


def edit_in_asar(asar: Path, inner: str, fn) -> None:
    tool = HERE / "asar_tool.py"
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "f.js"
        subprocess.run([sys.executable, str(tool), "get", str(asar), inner, str(f)], check=True, capture_output=True)
        src = f.read_text(encoding="utf-8")
        out = fn(src)
        if out != src:
            f.write_bytes(out.encode("utf-8"))
            subprocess.run([sys.executable, str(tool), "replace", str(asar), inner, str(f)], check=True, capture_output=True)
        print("patched" if out != src else "unchanged", inner)


def main(asar_path: str) -> None:
    sys.path.insert(0, str(HERE))
    import asar_tool
    asar = Path(asar_path)
    backup = asar.with_name(asar.name + ".bak-voices")
    if not backup.exists():
        shutil.copy2(asar, backup)
    _, header, _ = asar_tool.read(asar)
    paths = [p for p, _ in asar_tool.walk(header)]
    bundles = [p for p in paths if p.startswith("out/renderer/assets/index-") and p.endswith(".js")]
    if len(bundles) != 1:
        raise SystemExit(f"expected one renderer index bundle, found {bundles}")
    edit_in_asar(asar, "out/preload/index.js", patch_preload)
    edit_in_asar(asar, "out/main/index.js", patch_main)
    edit_in_asar(asar, bundles[0], patch_renderer)


if __name__ == "__main__":
    main(sys.argv[1])
