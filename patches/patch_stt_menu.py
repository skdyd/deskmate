"""[stt-menu patch] tray submenu "음성 인식 모델": base.en (fast, CPU) / small.en (CPU, more accurate) /
large-v3-turbo on the GPU (whisper.cpp Vulkan, see patch_stt_server.py). The choice is saved (settings.json sttModel)
and sent to the voice server at start-up. Every transcription also sends the character's name as a hint.
usage: python patch_stt_menu.py <app.asar>   (re-runnable)"""
import shutil, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import asar_tool
asar = Path(sys.argv[1]); inner = "out/main/index.js"

EDITS = [
    ('async function transcribe(audio, mime = "audio/wav") {\n	const res = await fetch(sttUrl(), {',
     '''// [stt-menu patch] speech model choice + the character's name as a hint
var STT_MODELS = [["base.en", "빠름 (base, CPU)"], ["small.en", "보통 (small, CPU)"], ["gpu", "정확 (large-v3-turbo, GPU)"]];
var sttModel = null; // read lazily: settings is created further down the file
function sttCurrent() {
	return sttModel ?? (sttModel = settings.get().sttModel || "base.en");
}
async function setSttModel(id, quiet) {
	const prev = sttCurrent();
	sttModel = id;
	settings.set({ sttModel: id });
	refreshTray();
	if (!quiet) status("음성 인식 모델 바꾸는 중…");
	try {
		const res = await fetch(new URL(sttUrl()).origin + "/v1/stt/model", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ model: id }), signal: AbortSignal.timeout(12e4) });
		const data = await res.json().catch(() => ({}));
		if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
		console.log(`[ears] speech model ${id}`);
		if (!quiet) status(`음성 인식: ${STT_MODELS.find((m) => m[0] === id)?.[1] ?? id}`);
	} catch (err) {
		console.warn("[ears] model switch failed:", err.message);
		status(`음성 모델 변경 실패: ${err.message}`);
		sttModel = prev;
		settings.set({ sttModel: prev });
		refreshTray();
	}
}
async function transcribe(audio, mime = "audio/wav") {
	const sttTarget = new URL(sttUrl());
	if (character?.name) sttTarget.searchParams.set("prompt", `${character.name}.`);
	const res = await fetch(sttTarget.toString(), {'''),
    ('''		{
			label: "대화 기록 보기",''', '''		{
			label: "음성 인식 모델",
			submenu: STT_MODELS.map(([id, label]) => ({ label, type: "radio", checked: sttCurrent() === id, click: () => void setSttModel(id) })) // [stt-menu patch]
		},
		{
			label: "대화 기록 보기",'''),
    ("electron.app.whenReady().then(async () => {\n",
     "electron.app.whenReady().then(async () => {\n	setTimeout(() => { if (sttCurrent() !== \"base.en\") void setSttModel(sttCurrent(), true); }, 4e3); // [stt-menu patch] re-apply the saved speech model\n"),
]
bak = asar.with_name("app.asar.bak-sttmenu")
if not bak.exists(): shutil.copy2(asar, bak)
f = Path(tempfile.mkdtemp()) / "index.js"; asar_tool.cmd_get(asar, inner, f)
s = f.read_bytes().decode("utf-8")
if "[stt-menu patch]" in s: sys.exit("already patched")
for a, b in EDITS:
    if s.count(a) != 1: sys.exit(f"anchor not found: {a[:60]!r} ({s.count(a)})")
    s = s.replace(a, b)
f.write_bytes(s.encode("utf-8")); asar_tool.cmd_replace(asar, inner, f); print("patched")
