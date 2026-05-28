"""works-cli 엔트리포인트."""

from __future__ import annotations

import sys

import click

from . import __version__
from ._cli_utils import EXIT_USAGE, get_client, handle_errors
from .config import DEFAULT_BASE_URL, DEFAULT_TZ, ConfigError, load_config, mask_pat


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, prog_name="works-cli")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="출력 포맷 (기본: text)",
)
@click.option("--json", "as_json", is_flag=True, default=False, help="--output json 단축")
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="HTTP 요청/응답을 stderr로 (Authorization은 마스킹)",
)
@click.pass_context
def cli(ctx: click.Context, output: str, as_json: bool, verbose: bool) -> None:
    """NAVER WORKS API용 PAT 기반 CLI.

    PAT는 WORKS_PAT 환경변수에서만 읽습니다 (디스크에 저장하지 않습니다).
    """
    ctx.ensure_object(dict)
    ctx.obj["output"] = "json" if as_json else output
    ctx.obj["verbose"] = verbose


@cli.group()
def config() -> None:
    """현재 설정 확인."""


@config.command("show")
@click.pass_context
@handle_errors
def config_show(ctx: click.Context) -> None:
    """환경변수에서 로드된 설정 표시 (PAT 마스킹)."""
    cfg = load_config()
    click.echo(f"PAT:              {mask_pat(cfg.pat)}  (env: WORKS_PAT)")
    click.echo(f"BASE_URL:         {cfg.base_url}")
    click.echo(f"DEFAULT_TZ:       {cfg.default_tz}")
    click.echo(f"INTERNAL_DOMAINS: {', '.join(cfg.internal_domains) or '(none)'}")


@cli.command("whoami")
@click.option("--json", "as_json", is_flag=True, default=False, help="JSON 출력")
@click.pass_context
@handle_errors
def whoami(ctx: click.Context, as_json: bool) -> None:
    """현재 PAT 보유자 정보 — 토큰 health check."""
    from .output import emit, resolve_output

    out = resolve_output(ctx.obj, as_json)
    with get_client(ctx) as c:
        data = c.get(f"/users/{c.user_id}")
    emit(data, out)


from .commands.bot import bot as _bot_group  # noqa: E402
from .commands.cal import cal as _cal_group  # noqa: E402
from .commands.mail import mail as _mail_group  # noqa: E402
from .commands.note import note as _note_group  # noqa: E402
from .commands.task import task as _task_group  # noqa: E402
from .commands.user import user as _user_group  # noqa: E402

cli.add_command(_mail_group)
cli.add_command(_cal_group)
cli.add_command(_bot_group)
cli.add_command(_task_group)
cli.add_command(_note_group)
cli.add_command(_user_group)


def main() -> None:
    try:
        cli(obj={}, standalone_mode=False)
    except click.exceptions.UsageError as e:
        e.show()
        sys.exit(EXIT_USAGE)
    except click.exceptions.Abort:
        click.echo("Aborted!", err=True)
        sys.exit(1)
    except (click.exceptions.Exit, SystemExit):
        raise
    except ConfigError as e:
        click.echo(f"오류: {e}", err=True)
        sys.exit(2)


__all__ = ["cli", "main"]
