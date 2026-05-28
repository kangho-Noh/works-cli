"""user 명령 (Directory API: 구성원/조직).

read 명령 (R): search / show / orgs / org-show / org-members  — user.read / directory scope
"""

from __future__ import annotations

from typing import Optional

import click

from .._cli_utils import get_client, handle_errors
from ..output import emit, resolve_output


@click.group()
def user() -> None:
    """구성원/조직(Directory) 명령."""


@user.command("search")
@click.option("--query", default=None, help="검색어 (이름/이메일/직책 등; 옵션)")
@click.option("--limit", type=int, default=None, help="가져올 인원 수")
@click.option("--cursor", default=None, help="페이지네이션 커서")
@click.option("--json", "as_json", is_flag=True, help="JSON 출력")
@click.pass_context
@handle_errors
def user_search(
    ctx: click.Context,
    query: Optional[str],
    limit: Optional[int],
    cursor: Optional[str],
    as_json: bool,
) -> None:
    """구성원 목록 조회 (검색)."""
    out = resolve_output(ctx.obj, as_json)
    params: dict[str, object] = {}
    if query:
        params["query"] = query
    if limit is not None:
        params["count"] = limit
    if cursor:
        params["cursor"] = cursor
    with get_client(ctx) as c:
        data = c.get("/users", params=params)
    emit(data, out)


@user.command("show")
@click.argument("user_id")
@click.option("--json", "as_json", is_flag=True, help="JSON 출력")
@click.pass_context
@handle_errors
def user_show(ctx: click.Context, user_id: str, as_json: bool) -> None:
    """구성원 정보 조회 (userId는 이메일 형식)."""
    out = resolve_output(ctx.obj, as_json)
    with get_client(ctx) as c:
        data = c.get(f"/users/{user_id}")
    emit(data, out)


@user.command("orgs")
@click.option("--json", "as_json", is_flag=True, help="JSON 출력")
@click.pass_context
@handle_errors
def user_orgs(ctx: click.Context, as_json: bool) -> None:
    """조직 목록 조회."""
    out = resolve_output(ctx.obj, as_json)
    with get_client(ctx) as c:
        data = c.get("/orgunits")
    emit(data, out)


@user.command("org-show")
@click.argument("org_id")
@click.option("--json", "as_json", is_flag=True, help="JSON 출력")
@click.pass_context
@handle_errors
def user_org_show(ctx: click.Context, org_id: str, as_json: bool) -> None:
    """조직 상세 조회."""
    out = resolve_output(ctx.obj, as_json)
    with get_client(ctx) as c:
        data = c.get(f"/orgunits/{org_id}")
    emit(data, out)


@user.command("org-members")
@click.argument("org_id")
@click.option("--limit", type=int, default=None, help="가져올 인원 수")
@click.option("--cursor", default=None, help="페이지네이션 커서")
@click.option("--json", "as_json", is_flag=True, help="JSON 출력")
@click.pass_context
@handle_errors
def user_org_members(
    ctx: click.Context,
    org_id: str,
    limit: Optional[int],
    cursor: Optional[str],
    as_json: bool,
) -> None:
    """조직 구성원 목록."""
    out = resolve_output(ctx.obj, as_json)
    params: dict[str, object] = {}
    if limit is not None:
        params["count"] = limit
    if cursor:
        params["cursor"] = cursor
    with get_client(ctx) as c:
        data = c.get(f"/orgunits/{org_id}/members", params=params)
    emit(data, out)
