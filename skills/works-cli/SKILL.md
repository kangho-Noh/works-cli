---
name: works-cli
description: 사내 NAVER WORKS API CLI 도구. PAT(Personal Access Token) 기반 메일/캘린더/Bot 메시지 조회·발송에 사용한다. 사용자가 "works 메일", "naver works", "회사 메일", "안 읽은 메일", "메일 보내기", "캘린더 일정", "오늘 일정", "회의 잡아줘", "bot 메시지", "Bot으로 알림", "works 알림", "naver works api" 등을 요청할 때 이 스킬을 사용한다. 사내 nworks(MCP/SSO 기반, 주 1회 재로그인 필요)의 PAT 기반 후속 도구다. 사내망에서만 동작한다.
---

# works-cli — NAVER WORKS API CLI

`works-cli`는 NAVER WORKS API(`https://corp.worksapis.com/v1.0`)를 PAT(Personal Access Token)로 호출하는 CLI다. **사내 `nworks`(MCP/SSO 기반)의 후속 도구**로, 장기 유효한 PAT를 써서 주 1회 재로그인이 필요 없다.

## 사전 점검 (반드시 첫 단계)

이 스킬을 실행하기 전에 항상 다음을 확인한다.

1. **설치 확인**: `which works-cli` — 없으면 사용자에게 `pipx install works-cli`(또는 레포 clone 후 `pipx install .`)를 안내하고 중단
2. **설정 확인**: `works-cli config show` — `PAT가 설정되지 않았습니다` 오류가 나면 사용자에게 다음 중 하나를 안내한다:
   - 환경변수 설정: `export WORKS_PAT="..." WORKS_USER_ID="user@yourdomain.com"`
   - 또는 대화형: `works-cli config set-pat`
3. **PAT는 절대 메시지/로그에 평문 출력 금지**. 사용자에게 PAT를 입력받더라도 그 값을 다시 echo하거나 명령 출력에 포함시키지 않는다.

## 명령 cheatsheet

### 메일 (`works-cli mail`)

| 명령 | Scope | 설명 |
|------|-------|------|
| `works-cli mail unread` | R | 안 읽은 메일 수 |
| `works-cli mail folders` | R | 메일함 목록 |
| `works-cli mail list --folder <id> [--limit N] [--cursor C] [--unread] [--filter all|mark|attach|tome]` | R | 메일함의 메일 목록 (unread/첨부 필터) |
| `works-cli mail read <mailId>` | R | 메일 상세 |
| `works-cli mail send --to <e> --subject <s> --body <b> [--cc <e>] [--html]` | W | 메일 발송 |

### 캘린더 (`works-cli cal`)

| 명령 | Scope | 설명 |
|------|-------|------|
| `works-cli cal list` | R | 개인 캘린더 목록 |
| `works-cli cal events --from <YYYY-MM-DD> --to <YYYY-MM-DD> [--calendar <id>] [--expand]` | R | 일정 목록 (--expand로 반복 일정 인스턴스 펴기) |
| `works-cli cal show <eventId> [--calendar <id>]` | R | 일정 상세 |
| `works-cli cal create --summary <t> --start <ISO> --end <ISO> [--description] [--attendees a,b]` | W | 일정 생성 |

### Bot (`works-cli bot`)

| 명령 | Scope | 설명 |
|------|-------|------|
| `works-cli bot list` | R | Bot 목록 |
| `works-cli bot info <botId>` | R | Bot 상세 |
| `works-cli bot send --bot <id> --user <userId> --message <msg>` | W | DM 전송 |
| `works-cli bot send-channel --bot <id> --channel <id> --message <msg>` | W | 채널 전송 |

### Task (`works-cli task`)

| 명령 | Scope | 설명 |
|------|-------|------|
| `works-cli task categories` | R | 개인 카테고리 목록 (`list` 전에 필수) |
| `works-cli task list --category <id> [--status TODO\|ALL] [--filter ALL\|ASSIGNEE\|ASSIGNOR]` | R | 카테고리의 할일 목록 |
| `works-cli task show <taskId>` | R | 할일 상세 |
| `works-cli task create --title <t> [--description] [--due <ISO>]` | W | 할일 생성 |
| `works-cli task complete <taskId>` / `task incomplete <taskId>` | W | 완료/미완료 토글 |
| `works-cli task delete <taskId>` | W | 삭제 |

> [!IMPORTANT]
> `task list`는 `--category` 필수. 항상 `task categories`로 categoryId 먼저 확인. 보통 첫 카테고리가 "미분류 할 일"이며 categoryId가 `"default"` 같은 짧은 값일 때가 많다.

### Note (`works-cli note`) — 조직/그룹 단위

| 명령 | Scope | 설명 |
|------|-------|------|
| `works-cli note list --group <groupId>` | R | 그룹 노트 게시글 목록 |
| `works-cli note show <postId> --group <groupId>` | R | 게시글 상세 |
| `works-cli note create --group <id> --title <t> --body <b>` | W | 작성 |
| `works-cli note delete <postId> --group <groupId>` | W | 삭제 |

### User (Directory) (`works-cli user`)

| 명령 | Scope | 설명 |
|------|-------|------|
| `works-cli user search [--query <q>] [--limit N]` | R | 구성원 검색/목록 |
| `works-cli user show <userId>` | R | 구성원 정보 (이메일로) |
| `works-cli user orgs` | R | 조직 목록 |
| `works-cli user org-show <orgUnitId>` | R | 조직 상세 |
| `works-cli user org-members <orgUnitId>` | R | 조직 구성원 |

**범례**: `R` = read scope만 필요 / `W` = write scope 필요 (`mail.send`, `calendar.write`, `bot.message`, `task`, `group.note` 등)

## 출력 포맷

- 기본은 사람이 읽기 좋은 텍스트
- `--json` 또는 `-o json` 플래그로 raw JSON 출력 → 파이프/jq 처리에 적합
- 페이지네이션 응답은 `nextCursor`가 stderr로 출력됨

## 활용 시나리오

**메일 확인:**
```bash
works-cli mail unread                                              # 전체 unread 수 (모든 폴더 합산)
works-cli mail folders --json | jq '.mailFolders[] | {folderId, folderName, unreadMailCount}'
works-cli mail list --folder 0 --limit 10 --json                   # 받은메일함 최근 10건 (folder 0)
works-cli mail list --folder 0 --unread --json                     # 받은메일함의 unread만
works-cli mail read <mailId>
```

> [!TIP]
> `mail unread`는 모든 폴더 합산이지만, `mail list --folder X --unread`는 특정 폴더만이다. 두 값이 다를 수 있으니 폴더별 unreadMailCount(`mail folders` 응답)로 어디에 흩어져 있는지 먼저 확인하면 좋다.

**오늘/이번 주 일정 (반드시 `--expand`):**
```bash
works-cli cal events --from $(date +%F) --to $(date +%F) --expand --json     # 오늘 인스턴스
works-cli cal events --from 2026-05-22 --to 2026-05-28 --expand --json       # 한 주
# expand 응답: {instances: [{summary, start, end, organizer, attendees, isRecurringInstance}, ...], totalCount}
```

> [!IMPORTANT]
> NAVER WORKS Calendar API는 반복 일정을 펴서 주지 않는다. raw `cal events` 응답의 `start.dateTime`은 원본(마스터) 시각이라 "오늘 일정"을 구하려고 그대로 비교하면 인스턴스를 놓친다. **오늘/이번 주 일정을 구할 때는 반드시 `--expand`를 쓰고 응답의 `instances` 평면 리스트를 사용한다.** RRULE/EXDATE/UNTIL/COUNT는 클라이언트(dateutil)가 평가한다.

**Bot 알림 (write scope PAT 필요):**
```bash
works-cli bot list                                         # 사용 가능한 Bot 확인
works-cli bot send --bot <botId> --user me@corp.com --message "배포 완료"
```

**복잡한 페이로드:**
```bash
# 사내 API 스펙이 기본 페이로드와 다르면 raw JSON을 직접 전달
works-cli mail send --to a@x.com --subject s --payload @/tmp/mail.json
works-cli bot send --bot <id> --user u@x.com --payload @/tmp/sticker.json
```

## 에러 코드 매핑

| HTTP | 의미 | 대응 |
|------|------|------|
| 401 | PAT 만료/잘못됨 | `works-cli config set-pat`으로 재설정 |
| 403 | Scope 부족 | PAT 발급 시 필요한 scope 확인 (mail.send, calendar.write 등) |
| 404 | 리소스 없음 | ID 재확인 |
| 429 | Rate limit | 잠시 대기 후 재시도 |
| 5xx | 서버 오류 | 잠시 후 재시도, 지속되면 사내 운영팀 문의 |

## 주의사항

- **사내망 전용**: VPN/사내망 외부에서는 동작하지 않음
- **Base URL**: `https://corp.worksapis.com/v1.0` — `www.worksapis.com`(대고객용)과 혼동 금지
- **userId**: 이메일 형식 (`user@yourdomain.com`)
- **write 명령은 사이드 이펙트가 큼**: 메일 발송/일정 생성/Bot 메시지는 한 번 보내면 회수 어려움. 사용자에게 명령 내용을 한 번 더 확인받은 뒤 실행한다
- **PAT 보안**: 토큰을 받아서 명령에 쓸 때도, 토큰 값을 다시 사용자에게 보여주거나 다른 명령 출력에 포함시키지 않는다
- **`nworks`도 사용 가능**: SSO 기반의 기존 CLI. PAT가 아닌 SSO를 선호하면 `nworks`로 대체 가능 (다만 주 1회 재로그인 필요)
