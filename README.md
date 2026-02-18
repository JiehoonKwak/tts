# tts-speak

Apple Silicon에서 로컬로 동작하는 TTS CLI. Qwen3-TTS + MLX 기반.

## 구조

```
텍스트 ──▶ tts-speak CLI ──▶ mlx_audio (Qwen3-TTS) ──▶ .wav
                │                      │
                ▼                      ▼
           stdin / JSON          HuggingFace 모델
          (hook 입력)            (~/.cache/huggingface/)
```

```
tts/
├── tts_cli.py          # CLI 본체
├── pyproject.toml      # 의존성, entry point
└── README.md
```

## 의존성

- **mlx-audio** (git): Qwen3-TTS 음성 합성 엔진 (PyPI 버전은 구버전이라 GitHub 설치 필수)
- **mlx / mlx-metal**: Apple Silicon GPU 가속
- **Python 3.13+**
- **afplay**: macOS 내장 오디오 재생 (`--play` 옵션용)

## 요구사항

- Apple Silicon Mac (M1/M2/M3/M4)
- [uv](https://docs.astral.sh/uv/) (`curl -LsSf https://astral.sh/uv/install.sh | sh`)

## 설치

### 새 Mac에서 처음부터

```bash
# 1. uv 설치 (없으면)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. 프로젝트 클론
git clone https://github.com/JiehoonKwak/tts.git
cd tts

# 3. 글로벌 CLI로 설치 (어디서든 tts-speak 사용 가능)
uv tool install --force -e . \
  --with "mlx-audio @ git+https://github.com/Blaizzy/mlx-audio.git" \
  --prerelease=allow

# 4. PATH 확인 (~/.local/bin이 PATH에 있어야 함)
#    uv 설치 시 자동 추가되지만, 안 되어 있으면:
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# 5. 확인
tts-speak "Hello" --play
```

### 이미 클론한 경우

```bash
cd tts
uv sync
uv tool install --force -e . \
  --with "mlx-audio @ git+https://github.com/Blaizzy/mlx-audio.git" \
  --prerelease=allow
```

첫 실행 시 모델(~4.5GB)이 `~/.cache/huggingface/`에 자동 다운로드된다.

`tts-speak: command not found` 에러 시 `~/.local/bin`이 PATH에 있는지 확인.

## 사용법

### 기본

```bash
tts-speak "Hello world"
tts-speak "안녕하세요" --lang ko
tts-speak "こんにちは" --lang ja
```

### 음성 커스텀

`--voice`로 원하는 목소리를 자연어로 묘사한다.

```bash
tts-speak "뉴스입니다" --lang ko --voice "A professional female news anchor voice."
tts-speak "Once upon a time" --voice "An elderly male storyteller, slow and gravelly."
tts-speak "알림입니다" --lang ko --voice "A short, clear robotic voice."
```

### 재생

```bash
# 즉시 재생 + 파일 저장
tts-speak "완료" --lang ko --play

# 즉시 재생, 파일 저장 안 함
tts-speak "Done!" --play --no-save
```

### pipe / stdin 입력

pipe 감지는 자동 — 별도 flag 불필요.

```bash
# 텍스트 pipe
echo "빌드 완료" | tts-speak --lang ko --play

# JSON 자동 감지 (message, text, content, body 키 순서로 추출)
echo '{"message":"Task completed"}' | tts-speak --play
echo '{"text":"배포 완료","status":"ok"}' | tts-speak --lang ko --play

# 특정 JSON 키 지정
echo '{"title":"Hello","body":"World"}' | tts-speak --json-key body --play

# 파일 읽기
tts-speak -f article.txt --lang ko --play
tts-speak -f notes.md --play
cat long_document.txt | tts-speak --lang ko --play
```

### 출력 제어

```bash
# 디렉토리 + 파일명
tts-speak "test" --output /tmp --prefix my_audio
# -> /tmp/my_audio_000.wav

# 속도 조절
tts-speak "천천히 말하기" --lang ko --speed 0.8
```

기본 출력 경로: `~/Music/tts/qwen3/`

## 전체 옵션

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `-f, --file` | - | 파일에서 텍스트 읽기 (.txt, .md, .json) |
| `--lang` | `en` | 언어 (`en`, `ko`, `ja`, `zh`) |
| `--voice` | natural female | 음성 묘사 (영어 자연어) |
| `--play` | off | afplay로 즉시 재생 |
| `--no-save` | off | 파일 저장 안 함 (`--play`와 함께) |
| `--json-key` | auto | JSON 입력 시 추출할 키 (기본: message/text/content 순) |
| `--output` | `~/Music/tts/qwen3/` | 출력 디렉토리 |
| `--prefix` | `tts` | 파일명 접두사 |
| `--speed` | `1.0` | 재생 속도 |
| `--max-tokens` | `2048` | 최대 생성 토큰 |
| `--verbose` | off | 디버그 출력 |
| `--model` | Qwen3-TTS-1.7B | HuggingFace 모델 ID |

입력 우선순위: `-f <file>` > 인자 > stdin (pipe 자동 감지). JSON은 모든 입력에서 자동 감지.

## Claude Code hook 연동

`~/.claude/settings.json`에 추가:

```json
{
  "hooks": {
    "Notification": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "echo '{\"message\":\"Claude needs attention\"}' | tts-speak --play --no-save",
            "async": true,
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

agent나 script에서 호출:

```bash
# 빌드 완료 알림
tts-speak "빌드 성공" --lang ko --play --no-save

# subagent 결과 pipe
echo "$RESULT" | tts-speak --play --no-save

# JSON hook 데이터 pipe
echo '{"text":"빌드 완료"}' | tts-speak --lang ko --play --no-save
```

## 지원 언어

| 코드 | 언어 | alias |
|------|------|-------|
| `en` | English | `english` |
| `ko` | Korean | `korean`, `kr` |
| `ja` | Japanese | `japanese`, `jp` |
| `zh` | Chinese | `chinese`, `cn` |

## 참고

- [mlx-audio](https://github.com/Blaizzy/mlx-audio) — MLX 기반 오디오 라이브러리
- [Qwen3-TTS 모델](https://huggingface.co/mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-bf16) — HuggingFace 모델 카드
- [MLX](https://github.com/ml-explore/mlx) — Apple Silicon ML 프레임워크
