"""mail 명령 (Mail API).

read 명령 (R): unread / folders / list / read  — read scope PAT로 동작
write 명령 (W): send                            — write scope PAT 필요
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import click

from .._cli_utils import (
    burst_check_and_mark,
    classify_external,
    get_client,
    handle_errors,
    hash_payload,
    redact_if_no_pii,
    require_yes,
)
from ..output import emit, resolve_output


@click.group()
def mail() -> None:
    """메일 명령."""


@mail.command("unread")
@click.option("--json", "as_json", is_flag=True, help="JSON 출력")
@click.pass_context
@handle_errors
def mail_unread(ctx: click.Context, as_json: bool) -> None:
    """안 읽은 메일 수 조회."""
    out = resolve_output(ctx.obj, as_json)
    with get_client(ctx) as c:
        data = c.get(f"/users/{c.user_id}/mail/unread-count")
    emit(data, out)


@mail.command("folders")
@click.option("--json", "as_json", is_flag=True, help="JSON 출력")
@click.pass_context
@handle_errors
def mail_folders(ctx: click.Context, as_json: bool) -> None:
    """메일함 목록 조회."""
    out = resolve_output(ctx.obj, as_json)
    with get_client(ctx) as c:
        data = c.get(f"/users/{c.user_id}/mail/mailfolders")
    emit(data, out)


@mail.command("list")
@click.option("--folder", required=True, help="메일함 ID (folders 명령으로 확인)")
@click.option("--limit", type=int, default=None, help="가져올 메일 수 (5~200, 기본 30)")
@click.option("--cursor", type=str, default=None, help="페이지네이션 커서")
@click.option("--unread", is_flag=True, help="안 읽은 메일만")
@click.option(
    "--filter",
    "search_filter",
    type=click.Choice(["all", "mark", "attach", "tome"]),
    default=None,
    help="검색 필터 (all/mark/attach/tome)",
)
@click.option("--json", "as_json", is_flag=True, help="JSON 출력")
@click.pass_context
@handle_errors
def mail_list(
    ctx: click.Context,
    folder: str,
    limit: Optional[int],
    cursor: Optional[str],
    unread: bool,
    search_filter: Optional[str],
    as_json: bool,
) -> None:
    """특정 메일함의 메일 목록."""
    out = resolve_output(ctx.obj, as_json)
    params: dict[str, object] = {}
    if limit is not None:
        params["count"] = limit
    if cursor:
        params["cursor"] = cursor
    if unread:
        params["isUnread"] = "true"
    if search_filter:
        params["searchFilterType"] = search_filter
    with get_client(ctx) as c:
        data = c.get(
            f"/users/{c.user_id}/mail/mailfolders/{folder}/children",
            params=params,
        )
    emit(data, out)


@mail.command("read")
@click.argument("mail_id")
@click.option("--show-pii", is_flag=True, help="본문(body)을 redact하지 않고 그대로 노출")
@click.option("--json", "as_json", is_flag=True, help="JSON 출력")
@click.pass_context
@handle_errors
def mail_read(ctx: click.Context, mail_id: str, show_pii: bool, as_json: bool) -> None:
    """메일 상세 조회. 기본은 본문을 redact, --show-pii로 노출."""
    out = resolve_output(ctx.obj, as_json)
    with get_client(ctx) as c:
        data = c.get(f"/users/{c.user_id}/mail/{mail_id}")
    if isinstance(data, dict):
        m = data.get("mail")
        if isinstance(m, dict) and "body" in m:
            m["body"] = redact_if_no_pii(m.get("body"), show_pii, hint="메일 본문")
    emit(data, out)


@mail.command("send")
@click.option("--to", multiple=True, required=True, help="수신자 이메일 (반복 가능)")
@click.option("--cc", multiple=True, help="참조 이메일 (반복 가능)")
@click.option("--subject", required=True, help="제목")
@click.option("--body", help="본문 (--payload 사용 시 생략 가능)")
@click.option("--html", is_flag=True, help="본문을 HTML로 발송")
@click.option(
    "--payload",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="JSON payload 파일 (이 옵션 사용 시 다른 옵션은 무시되고 raw payload 그대로 전송)",
)
@click.option("--yes", is_flag=True, help="실제 발송 (생략 시 dry-run + exit 4)")
@click.option(
    "--allow-external",
    is_flag=True,
    help="본인/INTERNAL_DOMAINS 외 수신자가 있어도 발송 (외부 게이트)",
)
@click.option("--json", "as_json", is_flag=True, help="JSON 출력")
@click.pass_context
@handle_errors
def mail_send(
    ctx: click.Context,
    to: tuple[str, ...],
    cc: tuple[str, ...],
    subject: str,
    body: Optional[str],
    html: bool,
    payload: Optional[Path],
    yes: bool,
    allow_external: bool,
    as_json: bool,
) -> None:
    """메일 발송 (write scope, 기본 dry-run, 외부 수신자/burst 추가 게이트)."""
    out = resolve_output(ctx.obj, as_json)
    if payload is not None:
        body_payload = json.loads(payload.read_text(encoding="utf-8"))
        all_to = body_payload.get("to", "")
        all_cc = body_payload.get("cc", "")
        to_emails = [e.strip() for e in str(all_to).split(";") if e.strip()] if all_to else []
        cc_emails = [e.strip() for e in str(all_cc).split(";") if e.strip()] if all_cc else []
    else:
        if body is None:
            raise click.UsageError("--body 또는 --payload 중 하나가 필요합니다")
        body_payload: dict[str, object] = {
            "subject": subject,
            "body": body,
            "contentType": "html" if html else "text",
            "to": ";".join(to),
        }
        if cc:
            body_payload["cc"] = ";".join(cc)
        to_emails = list(to)
        cc_emails = list(cc)

    with get_client(ctx) as c:
        # 본인 도메인은 whoami로 1회 확보 (env-var only이므로 캐시 안 함)
        if not allow_external and (to_emails or cc_emails):
            me = c.get(f"/users/{c.user_id}")
            sender_email = me.get("email", "") if isinstance(me, dict) else ""
            sender_domain = sender_email.split("@", 1)[1].lower() if "@" in sender_email else ""
            externals = classify_external(
                sender_domain=sender_domain,
                internal_domains=c.config.internal_domains,
                recipients=to_emails + cc_emails,
            )
            if externals:
                click.echo(
                    f"오류: 외부 도메인 수신자 {len(externals)}명 발견 → {', '.join(externals)}. "
                    "외부 발송을 의도했다면 --allow-external을 추가하세요.",
                    err=True,
                )
                ctx.exit(4)

        require_yes(yes, "POST", f"/users/{c.user_id}/mail", payload=body_payload)
        burst_check_and_mark(hash_payload(body_payload))
        data = c.post(f"/users/{c.user_id}/mail", json=body_payload)
    emit(data, out)
