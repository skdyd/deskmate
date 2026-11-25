# Deskmate launcher (called by start_deskmate.bat).
# 1. starts Ollama if needed, 2. starts the local voice server (Kokoro TTS + Whisper STT) if not answering,
# 3. runs Deskmate and waits, 4. stops the voice server it started when Deskmate exits.
# The voice server is started here instead of by Deskmate because deskmate's --parent-pid watchdog
# (os.kill(pid, 0)) does not work on Windows and makes the server exit right after start.
$ErrorActionPreference = 'Continue'
$Root    = 'C:\Users\jywhy\Desktop\deskmate AI'
$Logs    = Join-Path $Root 'logs'
$Python  = Join-Path $Root 'voice\.venv\Scripts\python.exe'
$Server  = Join-Path $Root 'app\resources\tts-local\server.py'
$App     = Join-Path $Root 'app\Deskmate.exe'
New-Item -ItemType Directory -Force $Logs | Out-Null

function Test-Url($url) { try { Invoke-RestMethod $url -TimeoutSec 2 | Out-Null; $true } catch { $false } }

if (Get-Process Deskmate -ErrorAction SilentlyContinue) { exit 0 }

if (-not (Test-Url 'http://127.0.0.1:11434/api/version')) {
  Start-Process "$env:LOCALAPPDATA\Programs\Ollama\ollama app.exe"
  for ($i = 0; $i -lt 30 -and -not (Test-Url 'http://127.0.0.1:11434/api/version'); $i++) { Start-Sleep 1 }
}

# Same settings the server would get from Deskmate (.env in %APPDATA%\deskmate).
$env:DESKMATE_TTS_VOICE = 'af_heart'
$env:DESKMATE_STT = 'local'
$env:DESKMATE_STT_MODEL = 'base.en'
$env:OMP_NUM_THREADS = '4'
$env:MKL_NUM_THREADS = '4'
$env:HF_HOME = Join-Path $Root 'voice\hf-cache'
$env:HF_HUB_DISABLE_SYMLINKS_WARNING = '1'
$env:PYTHONUTF8 = '1'
$env:PYTHONUNBUFFERED = '1'

$voice = $null
if (-not (Test-Url 'http://127.0.0.1:8880/health')) {
  $voice = Start-Process $Python -ArgumentList '-W', 'ignore', "`"$Server`"", '--port', '8880' -WorkingDirectory (Split-Path $Server) `
    -WindowStyle Hidden -PassThru -RedirectStandardOutput "$Logs\voice.log" -RedirectStandardError "$Logs\voice.err.log"
  # first start can take over 40 s (model load + HF hub check); Deskmate must not start before it answers
  for ($i = 0; $i -lt 120 -and -not (Test-Url 'http://127.0.0.1:8880/health'); $i++) { Start-Sleep 1 }
}

$app = Start-Process $App -WorkingDirectory (Split-Path $App) -PassThru `
  -RedirectStandardOutput "$Logs\deskmate.log" -RedirectStandardError "$Logs\deskmate.err.log"
$app.WaitForExit()
# Electron may leave helper processes for a moment; wait until the main app is fully gone.
while (Get-Process Deskmate -ErrorAction SilentlyContinue) { Start-Sleep 2 }
if ($voice -and -not $voice.HasExited) { Stop-Process -Id $voice.Id -Force }
