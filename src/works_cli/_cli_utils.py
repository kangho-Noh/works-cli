"""commands/*.py가 공유하는 CLI 헬퍼."""

from __future__ import annotations

import sys
from functools import wraps
from typing import Any, Callable

import click

from .client import WorksAPIError, WorksClient
from .config import ConfigError, load_config


def handle_errors(f: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(f)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return f(*args, **kwargs)
        except WorksAPIError as e:
            click.echo(f"오류: {e}", err=True)
            sys.exit(2)
        except ConfigError as e:
            click.echo(f"오류: {e}", err=True)
            sys.exit(3)

    return wrapper


def get_client() -> WorksClient:
    return WorksClient(load_config())
