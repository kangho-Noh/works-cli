"""commands/*.py가 공유하는 CLI 헬퍼."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import sys
import time
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Iterable

import click

from .client import WorksAPIError, WorksClient
from .config import ConfigError, load_config

# 표준 exit codes — 셸 스크립팅 안정성
EXIT_OK = 0
EXIT_GENERIC = 1
EXIT_AUTH = 2  # 401 / 403
EXIT_RATE_LIMIT = 3  # 429
EXIT_CONFIRM = 4  # --yes 누락 / burst guard / external 게이트
EXIT_USAGE = 5  # CLI 인자 잘못

_BURST_WINDOW_SEC = 10
_BURST_PATH = Path.home() / ".works-cli" / "last-send"


def handle_errors(f: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(f)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return f(*args, **kwargs)
        except WorksAPIError as e:
            click.echo(f"오류: {e}", err=True)
            if e.status_code in (401, 403):
                sys.exit(EXIT_AUTH)
            if e.status_code == 429:
                sys.exit(EXIT_RATE_LIMIT)
            sys.exit(EXIT_GENERIC)
        except ConfigError as e:
            click.echo(f"오류: {e}", err=True)
            sys.exit(EXIT_AUTH)

    return wrapper


def get_client(ctx: click.Context | None = None) -> WorksClient:
    """현재 컨텍스트의 verbose flag를 반영한 WorksClient."""
    verbose = False
    if ctx is not None and ctx.obj is not None:
        verbose = bool(ctx.obj.get("verbose"))
    return WorksClient(load_config(), verbose=verbose)


def require_yes(yes: bool, method: str, path: str, payload: Any = None) -> None:
    """Write 명령의 dry-run/--yes 게이트. yes=False면 호출 직전 정보를 stderr로 출력하고 exit 4."""
    if yes:
        return
    click.echo(f"[dry-run] {method} {path}", err=True)
    if payload is not None:
        click.echo("payload:", err=True)
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2), err=True)
    click.echo("실제 호출하려면 --yes를 추가하세요.", err=True)
    sys.exit(EXIT_CONFIRM)


def _split_emails(addr: str) -> list[str]:
    return [e.strip() for e in addr.split(";") if e.strip()]


def _domain_of(email: str) -> str:
    return email.split("@", 1)[1].lower() if "@" in email else ""


def classify_external(
    *,
    sender_domain: str,
    internal_domains: Iterable[str],
    recipients: Iterable[str],
) -> list[str]:
    """본인 도메인 + internal_domains 외 수신자 반환 (이메일 리스트)."""
    inner = {sender_domain.lower()} | {d.lower() for d in internal_domains if d}
    return [r for r in recipients if _domain_of(r) and _domain_of(r) not in inner]


def burst_check_and_mark(payload_hash: str) -> None:
    """동일 payload가 _BURST_WINDOW_SEC 이내에 다시 시도되면 exit 4. 통과 시 기록."""
    now = time.time()
    if _BURST_PATH.exists():
        try:
            parts = _BURST_PATH.read_text(encoding="utf-8").strip().split()
            last_hash = parts[0]
            last_epoch = float(parts[1])
            if last_hash == payload_hash and (now - last_epoch) < _BURST_WINDOW_SEC:
                wait = int(_BURST_WINDOW_SEC - (now - last_epoch))
                click.echo(
                    f"오류: 동일 페이로드로 {_BURST_WINDOW_SEC}초 이내 재발송 시도. "
                    f"{wait}초 더 기다리거나 내용을 바꾸세요. (burst guard)",
                    err=True,
                )
                sys.exit(EXIT_CONFIRM)
        except (ValueError, OSError):
            pass
    custom_path = os.environ.get("WORKS_BURST_PATH")
    path = Path(custom_path) if custom_path else _BURST_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{payload_hash} {now}\n", encoding="utf-8")
    path.chmod(stat.S_IRUSR | stat.S_IWUSR)


def hash_payload(payload: Any) -> str:
    s = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def redact_if_no_pii(text: str | None, show_pii: bool, *, hint: str = "본문") -> str | None:
    """기본은 redact, --show-pii가 켜졌을 때만 원문 노출."""
    if show_pii or not text:
        return text
    return f"[redacted — {hint} {len(text)}자. --show-pii로 노출]"
