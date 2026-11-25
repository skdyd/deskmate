"""[stt-model switch] voice server (app/resources/tts-local/server.py, outside the asar):
- POST /v1/stt/model {"model": "base.en" | "small.en" | "medium.en" | "gpu"} switches the speech model live.
  "gpu" starts whisper.cpp's server (Vulkan build, voice/whispercpp/bin/whisper-server.exe) with large-v3-turbo on
  port 8881 and forwards transcriptions to it; the CPU model is freed.
- POST /v1/audio/transcriptions?prompt=... passes hint words (the character's name) to Whisper.
usage: python patch_stt_server.py <server.py>   (backup server.py.bak-sttmodel; re-runnable)"""
import shutil, sys
from pathlib import Path

p = Path(sys.argv[1])
s = p.read_text(encoding="utf-8")
if "[stt-model switch]" in s:
    sys.exit("already patched")
shutil.copy2(p, p.with_name(p.name + ".bak-sttmodel"))

CONST_ANCHOR = 'STT_MODEL = os.environ.get("DESKMATE_STT_MODEL", "").strip() or "small.en"\n'
CONST = CONST_ANCHOR + r'''# [stt-model switch] optional GPU speech model: whisper.cpp (Vulkan build) server with large-v3-turbo
_WC = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "voice", "whispercpp")
GPU_STT_EXE = os.environ.get("DESKMATE_GPU_STT_EXE") or os.path.join(_WC, "bin", "whisper-server.exe")
GPU_STT_MODEL = os.environ.get("DESKMATE_GPU_STT_MODEL") or os.path.join(_WC, "models", "ggml-large-v3-turbo-q8_0.bin")
GPU_STT_PORT = int(os.environ.get("DESKMATE_GPU_STT_PORT") or 8881)
'''

OLD_INIT = '''    def __init__(self) -> None:
        self._model = None
        self._lock = threading.Lock()
        self.loaded = False

    def model(self):
        if self._model is None:
            from faster_whisper import WhisperModel  # slow import; done once

            t0 = time.time()
            self._model = WhisperModel(STT_MODEL, device=STT_DEVICE, compute_type=STT_COMPUTE)
            self.loaded = True
            print(f"[stt-local] loaded whisper {STT_MODEL} device={STT_DEVICE} compute={STT_COMPUTE} in {time.time() - t0:.1f}s", flush=True)
        return self._model
'''
NEW_INIT = r'''    def __init__(self) -> None:
        self._model = None
        self._lock = threading.Lock()
        self.loaded = False
        self.name = STT_MODEL  # [stt-model switch] faster-whisper model name, or "gpu" (whisper.cpp Vulkan server)
        self._gpu_proc = None

    def model(self):
        if self._model is None:
            from faster_whisper import WhisperModel  # slow import; done once

            t0 = time.time()
            self._model = WhisperModel(self.name, device=STT_DEVICE, compute_type=STT_COMPUTE)
            self.loaded = True
            print(f"[stt-local] loaded whisper {self.name} device={STT_DEVICE} compute={STT_COMPUTE} in {time.time() - t0:.1f}s", flush=True)
        return self._model

    def _gpu_up(self) -> bool:
        import urllib.request
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{GPU_STT_PORT}/", timeout=1)
            return True
        except Exception:  # noqa: BLE001 - not answering (yet)
            return False

    def start_gpu(self) -> None:
        """Start whisper.cpp's server (Vulkan build) with large-v3-turbo on the GPU, unless it already answers."""
        import subprocess
        if self._gpu_up():
            return
        if not (os.path.exists(GPU_STT_EXE) and os.path.exists(GPU_STT_MODEL)):
            raise RuntimeError(f"GPU speech model is not installed ({GPU_STT_EXE})")
        t0 = time.time()
        self._gpu_proc = subprocess.Popen(
            [GPU_STT_EXE, "-m", GPU_STT_MODEL, "--host", "127.0.0.1", "--port", str(GPU_STT_PORT), "-l", "en", "-nt"],
            cwd=os.path.dirname(GPU_STT_EXE), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        for _ in range(120):
            if self._gpu_up():
                print(f"[stt-local] GPU whisper (large-v3-turbo, whisper.cpp Vulkan) ready in {time.time() - t0:.1f}s", flush=True)
                return
            time.sleep(0.5)
        raise RuntimeError("GPU speech server did not start")

    def stop_gpu(self) -> None:
        if self._gpu_proc and self._gpu_proc.poll() is None:
            self._gpu_proc.terminate()
        elif self._gpu_up():  # one left over from an earlier voice server: free its VRAM too
            import subprocess
            subprocess.run(["taskkill", "/IM", "whisper-server.exe", "/F"], capture_output=True,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        self._gpu_proc = None

    def set_model(self, name: str) -> None:
        with self._lock:
            if name == self.name and (name != "gpu" or self._gpu_up()):
                return
            if name == "gpu":
                self.start_gpu()
            else:
                self.stop_gpu()
            self._model = None  # free the old CPU model
            self.name = name
            self.loaded = name == "gpu"
        if name != "gpu":
            self.model()
        print(f"[stt-local] speech model now {name}", flush=True)

    def _transcribe_gpu(self, audio, language, prompt: str) -> dict:
        import uuid
        import urllib.request
        import numpy as np
        import soundfile as sf
        if not isinstance(audio, np.ndarray):
            raise RuntimeError("GPU speech model needs WAV input")
        wav = io.BytesIO()
        sf.write(wav, audio, 16000, format="WAV", subtype="PCM_16")
        b = uuid.uuid4().hex
        parts = []

        def field(k, v):
            parts.append(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())

        field("response_format", "json")
        field("temperature", "0.0")
        if language:
            field("language", language)
        if prompt:
            field("prompt", prompt)
        parts.append(f'--{b}\r\nContent-Disposition: form-data; name="file"; filename="a.wav"\r\nContent-Type: audio/wav\r\n\r\n'.encode() + wav.getvalue() + b"\r\n")
        parts.append(f"--{b}--\r\n".encode())
        req = urllib.request.Request(f"http://127.0.0.1:{GPU_STT_PORT}/inference", data=b"".join(parts),
                                     headers={"Content-Type": f"multipart/form-data; boundary={b}"})
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read() or b"{}")
        text = " ".join(str(data.get("text", "")).split())
        if text.startswith("[") and text.endswith("]") or text.startswith("(") and text.endswith(")"):
            text = ""  # [BLANK_AUDIO], (music)...
        return {"text": text, "language": language or "en", "duration": round(len(audio) / 16000, 2),
                "no_speech_prob": 0.0 if text else 1.0, "avg_logprob": None}
'''

EDITS = [
    (CONST_ANCHOR, CONST),
    (OLD_INIT, NEW_INIT),
    ('''    def transcribe(self, data: bytes, language: str | None) -> dict:
        audio = self._audio(data)
        with self._lock:
            model = self.model()''', '''    def transcribe(self, data: bytes, language: str | None, prompt: str = "") -> dict:
        audio = self._audio(data)
        if self.name == "gpu":  # [stt-model switch]
            return self._transcribe_gpu(audio, language, prompt)
        with self._lock:
            model = self.model()'''),
    ('''                condition_on_previous_text=False,
                without_timestamps=True,
            )''', '''                condition_on_previous_text=False,
                without_timestamps=True,
                initial_prompt=prompt or None,  # hint words, e.g. the character's name
            )'''),
    ('"stt": {"enabled": STT_ENABLED, "model": STT_MODEL, "loaded": ears.loaded},',
     '"stt": {"enabled": STT_ENABLED, "model": ears.name, "loaded": ears.loaded},'),
    ('''        if path == "/v1/audio/transcriptions":
            return self._transcribe()
        return self._json(404, {"error": "not found"})''', '''        if path == "/v1/audio/transcriptions":
            return self._transcribe()
        if path == "/v1/stt/model":  # [stt-model switch] {"model": "base.en" | "small.en" | "medium.en" | "gpu"}
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
                name = str(body.get("model") or "").strip()
                if name not in ("base.en", "small.en", "medium.en", "gpu"):
                    return self._json(400, {"error": f"unknown model {name!r}"})
                ears.set_model(name)
                return self._json(200, {"ok": True, "model": ears.name})
            except Exception as err:  # noqa: BLE001
                print(f"[stt-local] model switch failed: {err!r}", flush=True)
                return self._json(500, {"error": str(err), "model": ears.name})
        return self._json(404, {"error": "not found"})'''),
    ('''        for pair in query.split("&"):
            if pair.startswith("language=") and pair[9:]:
                language = pair[9:]
        t0 = time.time()
        try:
            result = ears.transcribe(data, language)''', '''        prompt = ""
        for pair in query.split("&"):
            if pair.startswith("language=") and pair[9:]:
                language = pair[9:]
            if pair.startswith("prompt="):  # [stt-model switch] hint words, e.g. the character's name
                from urllib.parse import unquote_plus
                prompt = unquote_plus(pair[7:])[:200]
        t0 = time.time()
        try:
            result = ears.transcribe(data, language, prompt)'''),
]
for a, b in EDITS:
    if s.count(a) != 1:
        sys.exit(f"anchor not found: {a[:70]!r}")
    s = s.replace(a, b)
p.write_text(s, encoding="utf-8")
print("patched", p)
