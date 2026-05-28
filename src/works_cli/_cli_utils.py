"""commands/*.py가 공유하는 CLI 헬퍼."""

from __future__ import annotations

import sys
from functools import wraps
from typing import Any, Callable

import click

from .client import WorksAPIError, WorksClient
from .config import ConfigError, load_config

# 표준 exit codes — 셸 스크립팅 안정성
EXIT_OK = 0
EXIT_GENERIC = 1
EXIT_AUTH = 2  # 401 / 403
EXIT_RATE_LIMIT = 3  # 429
EXIT_CONFIRM = 4  # --yes 누락
EXIT_USAGE = 5  # CLI 인자 잘못


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
