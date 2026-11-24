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
