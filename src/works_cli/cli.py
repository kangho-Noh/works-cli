"""works-cli 엔트리포인트."""

from __future__ import annotations

import click

from . import __version__
from ._cli_utils import handle_errors
from .config import DEFAULT_BASE_URL, Config, load_config, mask_pat, save_config


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
@click.pass_context
def cli(ctx: click.Context, output: str, as_json: bool) -> None:
    """NAVER WORKS API용 PAT 기반 CLI."""
    ctx.ensure_object(dict)
    ctx.obj["output"] = "json" if as_json else output


@cli.group()
def config() -> None:
    """PAT 및 사용자 설정."""


@config.command("set-pat")
def config_set_pat() -> None:
    """PAT / USER_ID / BASE_URL 대화형 입력 및 ~/.works-cli/config.json 저장."""
    pat = click.prompt("WORKS_PAT", hide_input=True).strip()
    user_id = click.prompt("WORKS_USER_ID (이메일 형식)").strip()
    base_url = click.prompt("WORKS_BASE_URL", default=DEFAULT_BASE_URL).strip()
    path = save_config(Config(pat=pat, user_id=user_id, base_url=base_url))
    click.echo(f"저장됨: {path} (권한 0600)")


@config.command("show")
@handle_errors
def config_show() -> None:
    """현재 설정 출력 (PAT 마스킹)."""
    cfg = load_config()
    click.echo(f"PAT:      {mask_pat(cfg.pat)}")
    click.echo(f"USER_ID:  {cfg.user_id}")
    click.echo(f"BASE_URL: {cfg.base_url}")


from .commands.bot import bot as _bot_group  # noqa: E402
from .commands.cal import cal as _cal_group  # noqa: E402
from .commands.mail import mail as _mail_group  # noqa: E402

cli.add_command(_mail_group)
cli.add_command(_cal_group)
cli.add_command(_bot_group)


def main() -> None:
    cli(obj={})


__all__ = ["cli", "main"]
