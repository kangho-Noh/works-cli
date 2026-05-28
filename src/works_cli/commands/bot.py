"""bot 명령 (Bot API).

read 명령 (R): list / info               — read scope PAT로 동작
write 명령 (W): send / send-channel       — write scope (bot.message) PAT 필요
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import click

from .._cli_utils import get_client, handle_errors, require_yes
from ..output import emit, resolve_output


@click.group()
def bot() -> None:
    """Bot 명령."""


@bot.command("list")
@click.option("--json", "as_json", is_flag=True, help="JSON 출력")
@click.pass_context
@handle_errors
def bot_list(ctx: click.Context, as_json: bool) -> None:
    """Bot 목록 조회."""
    out = resolve_output(ctx.obj, as_json)
    with get_client(ctx) as c:
        data = c.get("/bots")
    emit(data, out)


@bot.command("info")
@click.argument("bot_id")
@click.option("--json", "as_json", is_flag=True, help="JSON 출력")
@click.pass_context
@handle_errors
def bot_info(ctx: click.Context, bot_id: str, as_json: bool) -> None:
    """Bot 상세 정보."""
    out = resolve_output(ctx.obj, as_json)
    with get_client(ctx) as c:
        data = c.get(f"/bots/{bot_id}")
    emit(data, out)


def _text_message_payload(message: str) -> dict:
    return {"content": {"type": "text", "text": message}}


@bot.command("send")
@click.option("--bot", "bot_id", required=True, help="발신 Bot ID")
@click.option("--user", "target_user", required=True, help="수신자 userId (이메일)")
@click.option("--message", help="본문 텍스트 (--payload 사용 시 생략)")
@click.option(
    "--payload",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="JSON payload 파일 (이 옵션 사용 시 --message 무시)",
)
@click.option("--yes", is_flag=True, help="실제 호출 (생략 시 dry-run + exit 4)")
@click.option("--json", "as_json", is_flag=True, help="JSON 출력")
@click.pass_context
@handle_errors
def bot_send(
    ctx: click.Context,
    bot_id: str,
    target_user: str,
    message: Optional[str],
    payload: Optional[Path],
    yes: bool,
    as_json: bool,
) -> None:
    """특정 사용자에게 Bot 메시지 전송 (write scope, 기본 dry-run)."""
    out = resolve_output(ctx.obj, as_json)
    if payload is not None:
        body = json.loads(payload.read_text(encoding="utf-8"))
    else:
        if message is None:
            raise click.UsageError("--message 또는 --payload 중 하나가 필요합니다")
        body = _text_message_payload(message)
    path = f"/bots/{bot_id}/users/{target_user}/messages"
    require_yes(yes, "POST", path, payload=body)
    with get_client(ctx) as c:
        data = c.post(path, json=body)
    emit(data, out)


@bot.command("send-channel")
@click.option("--bot", "bot_id", required=True, help="발신 Bot ID")
@click.option("--channel", "channel_id", required=True, help="채널 ID")
@click.option("--message", help="본문 텍스트 (--payload 사용 시 생략)")
@click.option(
    "--payload",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="JSON payload 파일",
)
@click.option("--yes", is_flag=True, help="실제 호출 (생략 시 dry-run + exit 4)")
@click.option("--json", "as_json", is_flag=True, help="JSON 출력")
@click.pass_context
@handle_errors
def bot_send_channel(
    ctx: click.Context,
    bot_id: str,
    channel_id: str,
    message: Optional[str],
    payload: Optional[Path],
    yes: bool,
    as_json: bool,
) -> None:
    """채널에 Bot 메시지 전송 (write scope, 기본 dry-run)."""
    out = resolve_output(ctx.obj, as_json)
    if payload is not None:
        body = json.loads(payload.read_text(encoding="utf-8"))
    else:
        if message is None:
            raise click.UsageError("--message 또는 --payload 중 하나가 필요합니다")
        body = _text_message_payload(message)
    path = f"/bots/{bot_id}/channels/{channel_id}/messages"
    require_yes(yes, "POST", path, payload=body)
    with get_client(ctx) as c:
        data = c.post(path, json=body)
    emit(data, out)
