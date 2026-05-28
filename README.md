# works-cli

> PAT(Personal Access Token) 기반 NAVER WORKS API CLI — 메일, 캘린더, Bot 메시지를 사내망에서 호출합니다.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](pyproject.toml)

`works-cli`는 NAVER WORKS API(`https://corp.worksapis.com/v1.0`)를 CLI로 다루기 위한 도구입니다. 사내 `nworks`(MCP/SSO 기반, 주 1회 재로그인 필요)의 **PAT 기반 후속 도구**로, 장기 유효한 토큰으로 스크립트/자동화에 적합합니다.

> [!IMPORTANT]
> 사내망 전용입니다. VPN/사내망 외부에서는 동작하지 않습니다.

---

## TL;DR

```bash
git clone https://github.com/kangho-Noh/works-cli.git
cd works-cli
pipx install .
works-cli config set-pat            # PAT, userId 대화형 입력
works-cli mail unread               # 동작 확인
```

---

## 요구사항

- **Python 3.11+**
- **pipx** (권장) 또는 일반 pip
- **사내망 접근** (VPN 등)
- **NAVER WORKS PAT** (필요 scope는 [아래 표](#pat-발급--scope-가이드) 참고)

---

## 설치

### pipx (권장)

```bash
git clone https://github.com/kangho-Noh/works-cli.git
cd works-cli
pipx install .
works-cli --version
```

### pip + venv

```bash
git clone https://github.com/kangho-Noh/works-cli.git
cd works-cli
python3 -m venv .venv && source .venv/bin/activate
pip install .
```

### 개발자용 (editable + dev deps)

```bash
pip install -e ".[dev]"
pytest
```

---

## PAT 발급 & scope 가이드

NAVER WORKS PAT는 사내 PAT 발급 페이지에서 발급할 수 있습니다(자세한 발급 절차는 사내 문서를 참고).

**필요 scope (명령별):**

| 명령 | 최소 scope |
|------|-----------|
| `mail unread/folders/list/read` | `mail.read` |
| `mail send` | `mail.send` (또는 `mail`) |
| `cal list/events/show` | `calendar.read` |
| `cal create` | `calendar.write` (또는 `calendar`) |
| `bot list/info` | `bot.read` (또는 `bot`) |
| `bot send / send-channel` | `bot.message` |

> [!WARNING]
> PAT는 비밀번호와 동등한 권한을 가집니다. 코드/커밋/이슈/Slack에 절대 평문으로 붙여넣지 마세요. 노출되면 즉시 사내 페이지에서 만료(rotate)하세요.

---

## 토큰 설정 (env var only)

`works-cli`는 PAT를 **환경변수에서만 읽습니다**. 디스크에 저장하지 않습니다.

```bash
export WORKS_PAT='<your-pat>'
works-cli whoami     # 토큰 검증 + 내 정보
```

`~/.zshrc`에 PAT를 두기 싫다면 `chmod 600`한 파일에서 셸 시작 시 로드:

```bash
chmod 600 ~/.works-pat
export WORKS_PAT="$(cat ~/.works-pat)"
```

> [!IMPORTANT]
> 의도적으로 **지원하지 않는** 패턴:
> - `--token` CLI 인자 (shell history에 누설)
> - `.env` 파일 (git/공유로 누설)
> - `~/.works-cli/config.yaml` 류의 dotfile 저장 (백업/sync로 누설)
>
> 토큰 회전은 **환경변수 한 줄 수정**으로 끝납니다.

### 환경변수 전체

| 변수 | 효과 | 기본값 |
|------|------|--------|
| `WORKS_PAT` | Personal Access Token | (필수) |
| `WORKS_BASE_URL` | API base URL 오버라이드 | `https://corp.worksapis.com/v1.0` (사내 tenant) |
| `WORKS_DEFAULT_TZ` | calendar / `--tz` fallback에 사용 (IANA) | `Asia/Seoul` |
| `WORKS_INTERNAL_DOMAINS` | `mail send` 외부 수신자 분류에 internal로 추가 인정할 도메인 (콤마) | (없음 — 본인 도메인만) |

> **첫 명령에서 400 BAD_REQUEST?** Base URL이 tenant와 안 맞을 가능성. `WORKS_BASE_URL`을 확인하세요.

### 설정 확인

```bash
works-cli config show          # 마스킹된 PAT + base URL + tz
works-cli whoami               # PAT 유효성 + 본인 정보 (token healthcheck)
```

## 보안 모델

| 항목 | 동작 |
|------|------|
| 토큰 source | `WORKS_PAT` 환경변수 단일 출처. 디스크 저장 없음 |
| `--verbose` / `-v` | Authorization 헤더 자동 마스킹 (`Bearer ****abcd`) |
| 401 / 403 | 즉시 abort, 재시도 없음 (계정 잠금 방지) |
| 429 | abort + `Retry-After` hint, 자동 재시도 없음 |
| TLS | verify 항상 on, `--insecure` 없음 |
| 사용자 식별자 | `me` self-alias만 사용, 타 사용자 호출 불가 (`user show <id>`는 별도 read-only 명령) |
| Exit codes | `0` ok / `1` generic / `2` auth(401/403) / `3` rate-limit(429) / `4` confirm / `5` usage |

---

## 명령 카탈로그

### Mail

```bash
works-cli mail unread                                 # 안 읽은 메일 수 (모든 폴더 합산)
works-cli mail folders                                # 메일함 목록 (각 폴더의 unreadMailCount 포함)
works-cli mail list --folder 0 --limit 10             # 메일 목록 (folder 0 = 받은메일함)
works-cli mail list --folder 0 --unread               # 해당 폴더의 안 읽은 메일만
works-cli mail list --folder 0 --filter attach        # 첨부 있는 메일만 (all/mark/attach/tome)
works-cli mail read <mailId>                          # 메일 상세
works-cli mail send --to a@x.com --subject hi --body world
works-cli mail send --to a@x.com --subject hi --html --body '<b>hi</b>'
works-cli mail send --to a@x.com --subject hi --payload @/tmp/mail.json  # raw JSON
```

### Calendar

```bash
works-cli cal list                                    # 내 캘린더 목록
works-cli cal events --from 2026-05-22 --to 2026-05-23
works-cli cal events --from 2026-05-22 --to 2026-05-22 --expand   # 오늘 인스턴스만 (반복 일정 펴기)
works-cli cal events --calendar <calId> --from 2026-05-22 --to 2026-05-23
works-cli cal show <eventId>
works-cli cal create --summary "회의" --start 2026-05-23T10:00:00 --end 2026-05-23T11:00:00
works-cli cal create --summary "회의" --start ... --end ... --attendees a@x.com,b@x.com
```

> [!IMPORTANT]
> NAVER WORKS Calendar API는 **반복 일정을 펴서 주지 않습니다**. 응답의 `start.dateTime`은 일정 원본 시각이라, "오늘/이번 주 일정"을 구하려면 `--expand`가 필요합니다. `--expand`는 RRULE/EXDATE/UNTIL/COUNT를 평가해 `{instances: [...], totalCount: N}` 형식으로 펴서 반환합니다.

### Bot

```bash
works-cli bot list                                            # Bot 목록
works-cli bot info <botId>                                    # Bot 상세
works-cli bot send --bot <botId> --user user@yourdomain.com --message "안녕"
works-cli bot send-channel --bot <botId> --channel <chId> --message "공지"
works-cli bot send --bot <botId> --user u@x.com --payload @/tmp/sticker.json
```

### Task (할일)

```bash
works-cli task categories                                     # 개인 카테고리 목록 (list 전에 필수)
works-cli task list --category <categoryId>                   # 카테고리의 할일 (기본 status=TODO)
works-cli task list --category <categoryId> --status ALL      # 완료 포함 전체
works-cli task show <taskId>
works-cli task create --title "백업 점검" --due 2026-05-30T18:00:00+09:00
works-cli task complete <taskId>
works-cli task incomplete <taskId>
works-cli task delete <taskId>
```

> [!NOTE]
> `task list`는 `--category`가 필수입니다. 보통 첫 카테고리가 "미분류 할 일"이고 `categoryId`는 `"default"` 같은 짧은 값입니다. `task categories --json | jq '.taskCategories[0].categoryId'`로 추출하세요.

### Note (조직/그룹 노트)

```bash
works-cli note list --group <groupId>                         # 그룹 노트 게시글 목록
works-cli note show <postId> --group <groupId>
works-cli note create --group <groupId> --title T --body B
works-cli note delete <postId> --group <groupId>
```

### User (Directory)

```bash
works-cli user search                                         # 구성원 목록
works-cli user search --query 홍길동                           # 이름/이메일로 검색
works-cli user show user@yourdomain.com                       # 본인/타인 정보
works-cli user orgs                                           # 조직 목록
works-cli user org-show <orgUnitId>                           # 조직 상세
works-cli user org-members <orgUnitId>                        # 조직 구성원
```

### 글로벌 옵션

| 옵션 | 설명 |
|------|------|
| `-o, --output {text,json}` | 출력 포맷 |
| `--json` | `-o json` 단축 |
| `-h, --help` | 도움말 |
| `--version` | 버전 |

명령별 `--json`도 동일하게 동작합니다.

---

## AI 에이전트용 빠른 가이드

다른 사람이 이 레포 링크를 자신의 AI 에이전트에게 "설치하고 사용 가능하게 해줘"라고 요청하는 시나리오를 가정한 가이드입니다.

### 자동 설치 절차

```bash
# 1) clone & install
git clone https://github.com/kangho-Noh/works-cli.git ~/works-cli
cd ~/works-cli && pipx install .

# 2) PAT 입력 (대화형)
works-cli config set-pat

# 3) 동작 확인
works-cli --help
works-cli config show
works-cli mail unread
```

### Skill 등록 (Claude Code / 호환 에이전트)

이 레포에는 `skills/works-cli/SKILL.md`이 동봉되어 있습니다. AI 에이전트의 skill 디렉토리에 복사하면 자연어 요청("안 읽은 메일 몇 개야?")에 자동으로 `works-cli`를 활용합니다.

```bash
# Claude Code
cp -r skills/works-cli ~/.claude/skills/

# 다른 에이전트 — 해당 에이전트의 skill 디렉토리로 복사
```

### AI 에이전트가 따라야 할 원칙

- PAT를 사용자로부터 받았더라도 **평문으로 echo하거나 다른 명령 출력/로그에 포함시키지 않습니다**
- write 명령(`mail send`, `cal create`, `bot send/send-channel`)은 회수 어려운 사이드 이펙트가 있으므로 **실행 전 사용자에게 한 번 더 확인합니다**
- API 페이로드 스키마가 사내 문서와 다르면 `--payload @file.json`으로 raw JSON을 전달합니다

---

## 보안 주의

- **PAT는 비밀번호와 동등**합니다. 절대 코드/커밋/이슈/Slack/스크린샷에 평문으로 포함하지 마세요.
- 노출되면 즉시 사내 PAT 페이지에서 만료(rotate)하고 새로 발급하세요.
- 이 레포는 secret scanning(`gitleaks` + `pre-commit`)이 구성되어 있습니다. 첫 커밋 전에 반드시:
  ```bash
  pre-commit install
  pre-commit run --all-files
  ```
- 이슈/PR 본문에 토큰 형태 문자열이 포함되지 않도록 GitHub의 secret scanning 알림도 활성화하세요.

---

## `nworks` → `works-cli` 마이그레이션

| nworks | works-cli | 비고 |
|--------|-----------|------|
| `nworks auth login/logout` | (불필요) | PAT는 장기 유효 |
| `nworks mail list --unread` | `works-cli mail list --folder INBOX --json | jq '...'` | 또는 `mail unread`로 카운트만 |
| `nworks mail folders` | `works-cli mail folders` | |
| `nworks mail read <id>` | `works-cli mail read <id>` | |
| `nworks calendar list` | `works-cli cal events --from <d> --to <d>` | |
| `nworks bot send ...` | `works-cli bot send --bot <id> --user <u> --message <m>` | |

`nworks`는 `works-cli`의 안정화 이후 deprecated 될 예정입니다. 마이그레이션 기간 동안 두 도구를 병행 사용할 수 있습니다.

---

## 에러 메시지 카탈로그

| HTTP | 메시지 | 의미 / 대응 |
|------|--------|------------|
| 401 | "PAT가 만료되었거나 잘못되었습니다…" | `works-cli config set-pat`으로 재설정 |
| 403 | "Scope 부족 또는 권한 없음" | PAT 발급 시 필요한 scope 확인 |
| 404 | "리소스를 찾을 수 없습니다" | ID 재확인 |
| 429 | "요청 한도를 초과했습니다…" | 잠시 후 재시도 |
| 5xx | "서버 오류 (status N)" | 사내 운영팀 문의 |
| (네트워크) | "네트워크 오류: …" | VPN/사내망 연결 확인 |

---

## 개발

```bash
git clone https://github.com/kangho-Noh/works-cli.git
cd works-cli
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install

# 테스트
pytest

# 로컬 설치 확인
pipx install -e . --force
works-cli --help
```

테스트는 모두 `respx`로 httpx를 mock하므로 실제 네트워크 호출이 발생하지 않습니다. 테스트용 PAT는 항상 `"test-pat-do-not-use"` 형태의 명백한 placeholder입니다.

### 디렉토리 구조

```
works-cli/
├── src/works_cli/
│   ├── cli.py              # 엔트리포인트
│   ├── config.py           # PAT/userId 로드 (env → file)
│   ├── client.py           # httpx + Bearer + 에러 매핑
│   ├── output.py           # text/json 출력
│   └── commands/{mail,cal,bot}.py
├── skills/works-cli/SKILL.md
├── tests/
└── pyproject.toml
```

---

## 기여

이슈/PR 환영합니다. 다만:

- 토큰 형태 문자열을 본문/예시에 포함하지 마세요 (CI에서 차단됩니다)
- `pre-commit run --all-files`를 통과해야 합니다
- 새 명령을 추가할 때는 `tests/`에 mock 기반 단위 테스트를 함께 추가해주세요

---

## 라이선스

MIT — [`LICENSE`](LICENSE) 참고.
