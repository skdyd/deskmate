# deskmate 개인 설정 백업

[deskmate](https://github.com/MuhammadMurtuzaHussain/deskmate)를 내 PC에 맞게 고친 부분만 모아 두는 백업 저장소입니다.
원본 코드 전체나 모델 파일은 넣지 않습니다.

## 구성
- `config/env.example` : `%APPDATA%\deskmate\.env` 설정 (API 키 같은 비밀값은 지우고 저장)
- `character/<id>/` : 성격 파일(`persona.md`), `character.json` 등 캐릭터 설정
- `patches/` : 원본 코드를 고친 경우 그 변경분 (`.patch`)

## 넣지 않는 것
- Live2D, VRM, Whisper, Kokoro, Ollama 모델 같은 큰 파일
- `.env` 원본, API 키, 대화 기록과 메모리
