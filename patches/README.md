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
