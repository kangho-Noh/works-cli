"""task 명령 (Task API).

read 명령 (R): list / show                   — task.read scope
write 명령 (W): create / complete / incomplete / delete  — task scope
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import click

from .._cli_utils import get_client, handle_errors
from ..output import emit, resolve_output


@click.group()
def task() -> None:
    """할일(Task) 명령."""


@task.command("categories")
@click.option("--json", "as_json", is_flag=True, help="JSON 출력")
@click.pass_context
@handle_errors
def task_categories(ctx: click.Context, as_json: bool) -> None:
    """할일 개인 카테고리 목록 (task list 전에 categoryId 확인용)."""
    out = resolve_output(ctx.obj, as_json)
    with get_client() as c:
        data = c.get(f"/users/{c.user_id}/task-categories")
    emit(data, out)


@task.command("list")
@click.option("--category", "category_id", required=True, help="카테고리 ID (task categories로 확인)")
@click.option(
    "--status",
    type=click.Choice(["TODO", "ALL"]),
    default=None,
    help="상태 필터 (기본: TODO)",
)
@click.option(
    "--filter",
    "search_filter",
    type=click.Choice(["ALL", "ASSIGNEE", "ASSIGNOR"]),
    default=None,
    help="검색 범위 (기본: ALL)",
)
@click.option("--limit", type=int, default=None, help="가져올 할일 수 (0~100)")
@click.option("--cursor", default=None, help="페이지네이션 커서")
@click.option("--json", "as_json", is_flag=True, help="JSON 출력")
@click.pass_context
@handle_errors
def task_list(
    ctx: click.Context,
    category_id: str,
    status: Optional[str],
    search_filter: Optional[str],
    limit: Optional[int],
    cursor: Optional[str],
    as_json: bool,
) -> None:
    """내 할일 목록 조회 (categoryId 필수)."""
    out = resolve_output(ctx.obj, as_json)
    params: dict[str, object] = {"categoryId": category_id}
    if status:
        params["status"] = status
    if search_filter:
        params["searchFilterType"] = search_filter
    if limit is not None:
        params["count"] = limit
    if cursor:
        params["cursor"] = cursor
    with get_client() as c:
        data = c.get(f"/users/{c.user_id}/tasks", params=params)
    emit(data, out)


@task.command("show")
@click.argument("task_id")
@click.option("--json", "as_json", is_flag=True, help="JSON 출력")
@click.pass_context
@handle_errors
def task_show(ctx: click.Context, task_id: str, as_json: bool) -> None:
    """할일 상세 조회."""
    out = resolve_output(ctx.obj, as_json)
    with get_client() as c:
        data = c.get(f"/tasks/{task_id}")
    emit(data, out)


@task.command("create")
@click.option("--title", required=True, help="할일 제목")
@click.option("--description", default=None, help="설명")
@click.option("--due", default=None, help="마감 (ISO 8601, 예: 2026-05-23T18:00:00+09:00)")
@click.option(
    "--payload",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="JSON payload 파일 (이 옵션 사용 시 다른 옵션 무시)",
)
@click.option("--json", "as_json", is_flag=True, help="JSON 출력")
@click.pass_context
@handle_errors
def task_create(
    ctx: click.Context,
    title: str,
    description: Optional[str],
    due: Optional[str],
    payload: Optional[Path],
    as_json: bool,
) -> None:
    """할일 생성 (write scope 필요)."""
    out = resolve_output(ctx.obj, as_json)
    if payload is not None:
        body = json.loads(payload.read_text(encoding="utf-8"))
    else:
        body = {"title": title}
        if description:
            body["description"] = description
        if due:
            body["dueDateTime"] = due
    with get_client() as c:
        data = c.post(f"/users/{c.user_id}/tasks", json=body)
    emit(data, out)


@task.command("complete")
@click.argument("task_id")
@click.option("--json", "as_json", is_flag=True, help="JSON 출력")
@click.pass_context
@handle_errors
def task_complete(ctx: click.Context, task_id: str, as_json: bool) -> None:
    """할일 완료 처리 (write scope)."""
    out = resolve_output(ctx.obj, as_json)
    with get_client() as c:
        data = c.post(f"/tasks/{task_id}/complete")
    emit(data if data is not None else {"ok": True, "taskId": task_id}, out)


@task.command("incomplete")
@click.argument("task_id")
@click.option("--json", "as_json", is_flag=True, help="JSON 출력")
@click.pass_context
@handle_errors
def task_incomplete(ctx: click.Context, task_id: str, as_json: bool) -> None:
    """할일 미완료 처리 (write scope)."""
    out = resolve_output(ctx.obj, as_json)
    with get_client() as c:
        data = c.post(f"/tasks/{task_id}/incomplete")
    emit(data if data is not None else {"ok": True, "taskId": task_id}, out)


@task.command("delete")
@click.argument("task_id")
@click.option("--json", "as_json", is_flag=True, help="JSON 출력")
@click.pass_context
@handle_errors
def task_delete(ctx: click.Context, task_id: str, as_json: bool) -> None:
    """할일 삭제 (write scope)."""
    out = resolve_output(ctx.obj, as_json)
    with get_client() as c:
        data = c.delete(f"/tasks/{task_id}")
    emit(data if data is not None else {"ok": True, "deleted": task_id}, out)
