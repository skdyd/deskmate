# 패치 목록

설치된 Deskmate(`app\resources\app.asar`)를 직접 고치는 방식입니다. 처음 적용할 때 원본은 `app.asar.orig`로 남고, 되돌리려면 그 파일을 `app.asar`로 다시 복사하면 됩니다. Deskmate를 업데이트하면 다시 적용해야 합니다.

- `multi-monitor.patch` : 모든 모니터를 캡처해 왼쪽부터 한 장으로 이어 붙임 (기본 전체 폭 2048px, 환경변수 `DESKMATE_CAPTURE_WIDTH`로 조절). 원본 소스(`src/main/index.ts`, `brain.ts`) 기준 diff.
- `patch_multi_monitor.py` : 위 변경을 소스(ts) 또는 빌드된 `out/main/index.js`(js)에 적용하는 스크립트.
- `asar_tool.py` : Node 없이 app.asar 안의 파일 하나를 꺼내거나 교체하는 도구.
- `patch_keep_alive.py` : Ollama 모델을 30분 대신 5분 쉬면 내리도록 바꿈.

## 듀얼 모니터 적용 순서
```
python asar_tool.py get     app.asar out/main/index.js index.js
python patch_multi_monitor.py js index.js
python asar_tool.py replace app.asar out/main/index.js index.js
```

## Live2D 30fps 제한 (2026-11-25)
- `patch_live2d_fps.py` : Live2D 아바타 렌더링을 30fps로 제한 (PIXI 앱 ticker + 공유 ticker). 모니터 주사율(165Hz)만큼 그리던 것을 줄여 대기 CPU를 낮춤.
- `live2d-fps.patch` : 같은 변경의 원본 소스(`src/renderer/live2d.ts`) 기준 diff.
```
python patch_live2d_fps.py js "...\app\resources\app.asar" 30
```
다시 실행하면 값만 바뀝니다. 0을 주면 제한 해제. 적용 전 백업은 `app.asar.bak-fps`.

## 점 컨트롤 + 클릭 통과 (2026-11-25)
- `patch_dots.py` : 캐릭터 창을 점 5개(발 아래)만 클릭되게 바꿈. 왼쪽부터 클릭 반응 켜기/끄기, 작게(−), 끌어서 이동, 크게(+), 대화창 보이기/숨기기. 나머지(캐릭터 몸, 말풍선)는 클릭이 뒤 창으로 통과. 반응/대화창/크기(60~130%)는 다음 실행에도 유지.
  이동할 때는 캐릭터 몸(투명 여백 제외)만 커서가 있는 모니터 안에 있으면 되고, 말풍선은 폭 280px로 화면 안쪽에 맞춰 놓여 옆 모니터로 넘어가지 않음. renderer 번들, preload, main(`window:move-by`, `window:zoom`)을 고침.
- `dots.patch` : 같은 변경의 원본 소스(`src/renderer/main.ts`, `src/preload/index.ts`, `src/shared/types.ts`, `src/main/index.ts`) 기준 diff.
```
python patch_dots.py js "...\app\resources\app.asar"
```
다시 실행하면 이전 버전을 교체합니다. 적용 전 백업은 `app.asar.bak-dots`.

## 목소리 전환 + 말 속도 (2026-11-25)
- `patch_voices_server.py` : 로컬 음성 서버(`app\resources\tts-local\server.py`, asar 밖)에 프리셋 추가. Kokoro 목소리를 섞고 리샘플링으로 음높이를 올려 더 젊은 톤으로 만듦: `bella_up13`, `bella_up15`, `heart_up15`, `bellasky_up15`(bella 70% + sky 30%), `heartbella_up20`(heart+bella 반반). 백업 `server.py.bak-voices`.
- `patch_voices.py` : 대화창 캐릭터 드롭다운 옆에 목소리 메뉴와 속도 메뉴(0.7~1, 기본 0.85) 추가. 선택은 localStorage에 기억되고, main이 `DESKMATE_TTS_VOICE` / `DESKMATE_TTS_SPEED`를 바꿔 다음 말(교정 포함)부터 적용. 브라우저 대체 목소리에도 기호 정리 적용. 백업 `app.asar.bak-voices`.
```
python patch_voices_server.py "...\app\resources\tts-local\server.py"
python patch_voices.py "...\app\resources\app.asar"
```

## 음성 기호 정리 (2026-11-25)
- `patch_speech_clean.py` : 음성 서버가 읽기 전에 이모지, *행동 묘사*(*sigh*), 마크다운 기호, 따옴표, 괄호, 링크를 뺌. 한 단어 강조(*very*)는 단어만 읽음. 말풍선 글자는 그대로. 읽을 게 없으면 오류 대신 0.3초 무음. 백업 `server.py.bak-clean`.
```
python patch_speech_clean.py "...\app\resources\tts-local\server.py"
```

## 마지막 상태 기억 (2026-11-25)
- `patch_remember_character.py` : `.env`의 `DESKMATE_CHARACTER`보다 마지막에 고른 캐릭터(settings.json `activeCharacter`)를 우선. 백업 `app.asar.bak-remember`.
- `patch_remember_toggles.py` : 마이크(listening)와 watch 켜짐/꺼짐을 settings.json(`micOn`, `watchOn`)에 저장하고 다음 실행 때 복원. 추가한 줄은 모두 `// [remember-toggles patch]` 표시. 백업 `app.asar.bak-toggles`.
```
python patch_remember_character.py "...\app\resources\app.asar"
python patch_remember_toggles.py "...\app\resources\app.asar"
```
모든 스크립트는 다시 실행해도 안전합니다(이미 적용돼 있으면 교체하거나 그대로 둠). Deskmate는 반드시 `start_deskmate.bat`(또는 바탕화면 아이콘)으로 실행해야 음성 서버가 같이 뜹니다.

## 2026-11-25 저녁 추가분 (버전 1.0.0)
모두 `python <스크립트> "...\app\resources\app.asar"` 형식이고, 적용 전 백업(`app.asar.bak-*`)을 남깁니다. 위에서 아래 순서로 적용하세요.

| 스크립트 | 내용 |
|---|---|
| `patch_grammar_check.py` | 영어 대화 뒤 Ollama로 문법 검사, 교정 한 줄을 덧붙임 (`DESKMATE_GRAMMAR_CHECK=0`으로 끔) |
| `patch_select_options.py` | 드롭다운 옵션 정리 |
| `patch_upper_body.py` | 발을 패널 바로 위에 붙이고, 6번째 점으로 보이는 부분을 전신→4/5→…→1/5 (캐릭터별 기억) |
| `patch_zoom_max.py` | 크기 최대 2배, 커질 때 창 폭도 같이 넓힘 |
| `patch_fullheight.py` | 창이 모니터 높이일 때 머리가 화면 꼭대기까지, 말풍선은 머리 위 |
| `patch_accessories.py` | "소품" 드롭다운: 모델의 표현식(앞치마, 안경…) 켜고 끄기, 캐릭터별 기억. exp3.json에 `"DeskmateHidden": true`면 목록에서 숨김 |
| `patch_touch.py` | 터치 14부위(+ `touchLayout: "chibi"`), 톡/연타/쓰다듬기/길게 누르기/끌기, `touch-prompts.json`(config/) 지시문 |
| `patch_ontop.py` + `patch_ontop_fix.py` | 2초마다 항상 위 재설정 (포커스 중엔 moveTop 안 함) |
| `patch_watch.py` (+ `patch_watch_blinkfix.py`) | 화면 보기: 마우스 있는 모니터만 1280px, 활성 창 제목·프로그램을 텍스트로, 추측 금지, 최근 말 반복 금지 |
| `patch_ears_queue.py` | 대답 중 들은 말을 버리지 않고 하나 기억했다가 이어서 대답 |
| `patch_capture_exclude.py` + `patch_capture_toggle.py` | 캡처에서 캐릭터 제외(깜빡임 없음), 트레이 "캡처에서 숨기기"로 켜고 끔 |
| `patch_compact_panel.py` + `patch_panel_rows.py` | 패널 최대 420px, 3줄 고정(상태 / 선택창 / 입력) |
| `patch_chatlog.py` + `patch_chatlog_pos.py` | 트레이 "대화 기록 보기" 창, 위치·크기 기억 |
| `patch_stt_server.py` (server.py 대상) + `patch_stt_menu.py` | 음성 인식 모델 선택(base/small CPU, large-v3-turbo GPU via whisper.cpp Vulkan), 캐릭터 이름 힌트 |
| `patch_version.py` | 트레이 맨 위에 패치 버전 표시 (`VERSION` 파일) |

GPU 음성 인식: LunarG Vulkan SDK 설치 후 `tools/whispercpp-build.cmd`로 whisper.cpp(공식 소스)를 빌드하고 `ggml-large-v3-turbo-q8_0.bin`을 `voice\whispercpp\models`에 둡니다.
