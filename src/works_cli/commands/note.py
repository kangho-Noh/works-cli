"""note 명령 (조직/그룹 노트 API).

read 명령 (R): list / show           — group.note.read scope
write 명령 (W): create / update / delete  — group.note scope

NAVER WORKS 노트는 조직/그룹 단위로만 제공되며, groupId가 필요하다.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import click

from .._cli_utils import get_client, handle_errors
from ..output import emit, resolve_output


@click.group()
def note() -> None:
    """노트 명령 (조직/그룹 단위)."""


@note.command("list")
@click.option("--group", "group_id", required=True, help="그룹/조직 ID")
@click.option("--limit", type=int, default=None, help="가져올 게시글 수")
@click.option("--cursor", default=None, help="페이지네이션 커서")
@click.option("--json", "as_json", is_flag=True, help="JSON 출력")
@click.pass_context
@handle_errors
def note_list(
    ctx: click.Context,
    group_id: str,
    limit: Optional[int],
    cursor: Optional[str],
    as_json: bool,
) -> None:
    """그룹 노트 게시글 목록."""
    out = resolve_output(ctx.obj, as_json)
    params: dict[str, object] = {}
    if limit is not None:
        params["count"] = limit
    if cursor:
        params["cursor"] = cursor
    with get_client(ctx) as c:
        data = c.get(f"/groups/{group_id}/note/posts", params=params)
    emit(data, out)


@note.command("show")
@click.argument("post_id")
@click.option("--group", "group_id", required=True, help="그룹/조직 ID")
@click.option("--json", "as_json", is_flag=True, help="JSON 출력")
@click.pass_context
@handle_errors
def note_show(
    ctx: click.Context, post_id: str, group_id: str, as_json: bool
) -> None:
    """그룹 노트 게시글 상세."""
    out = resolve_output(ctx.obj, as_json)
    with get_client(ctx) as c:
        data = c.get(f"/groups/{group_id}/note/posts/{post_id}")
    emit(data, out)


@note.command("create")
@click.option("--group", "group_id", required=True, help="그룹/조직 ID")
@click.option("--title", required=True, help="제목")
@click.option("--body", help="본문 (--payload 사용 시 생략)")
@click.option(
    "--payload",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="JSON payload 파일",
)
@click.option("--json", "as_json", is_flag=True, help="JSON 출력")
@click.pass_context
@handle_errors
def note_create(
    ctx: click.Context,
    group_id: str,
    title: str,
    body: Optional[str],
    payload: Optional[Path],
    as_json: bool,
) -> None:
    """그룹 노트 게시글 작성 (write scope 필요)."""
    out = resolve_output(ctx.obj, as_json)
    if payload is not None:
        body_payload = json.loads(payload.read_text(encoding="utf-8"))
    else:
        if body is None:
            raise click.UsageError("--body 또는 --payload 중 하나가 필요합니다")
        body_payload = {"title": title, "body": body}
    with get_client(ctx) as c:
        data = c.post(f"/groups/{group_id}/note/posts", json=body_payload)
    emit(data, out)


@note.command("delete")
@click.argument("post_id")
@click.option("--group", "group_id", required=True, help="그룹/조직 ID")
@click.option("--json", "as_json", is_flag=True, help="JSON 출력")
@click.pass_context
@handle_errors
def note_delete(
    ctx: click.Context, post_id: str, group_id: str, as_json: bool
) -> None:
    """그룹 노트 게시글 삭제 (write scope)."""
    out = resolve_output(ctx.obj, as_json)
    with get_client(ctx) as c:
        data = c.delete(f"/groups/{group_id}/note/posts/{post_id}")
    emit(data if data is not None else {"ok": True, "deleted": post_id}, out)
