"""cal(endar) 명령 (Calendar API).

read 명령 (R): list / events / show     — read scope PAT로 동작
write 명령 (W): create                   — write scope PAT 필요
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

import click

from .._cli_utils import get_client, handle_errors
from ..output import emit, resolve_output

_DEFAULT_TZ = "Asia/Seoul"


def _tz_offset(tz: str) -> str:
    """'Asia/Seoul' → '+09:00'. 이미 '+HH:MM' / '-HH:MM' 형식이면 그대로 반환."""
    if tz.startswith("+") or tz.startswith("-"):
        return tz
    try:
        offset = datetime.now(ZoneInfo(tz)).strftime("%z")  # '+0900'
    except Exception as e:
        raise click.BadParameter(f"타임존을 인식할 수 없습니다: {tz}") from e
    return f"{offset[:3]}:{offset[3:]}"


def _normalize_datetime(value: str, default_time: str, tz: str) -> str:
    """YYYY-MM-DD → YYYY-MM-DDTdefault_time±HH:MM. 이미 offset이 있으면 그대로."""
    has_offset = ("+" in value[10:]) or ("-" in value[10:]) or value.endswith("Z")
    if "T" in value:
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as e:
            raise click.BadParameter(f"날짜 형식이 잘못되었습니다: {value}") from e
        return value if has_offset else f"{value}{_tz_offset(tz)}"
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError as e:
        raise click.BadParameter(f"날짜 형식이 잘못되었습니다: {value}") from e
    return f"{value}T{default_time}{_tz_offset(tz)}"


@click.group()
def cal() -> None:
    """캘린더 명령."""


@cal.command("list")
@click.option("--json", "as_json", is_flag=True, help="JSON 출력")
@click.pass_context
@handle_errors
def cal_list(ctx: click.Context, as_json: bool) -> None:
    """개인 캘린더 목록 조회."""
    out = resolve_output(ctx.obj, as_json)
    with get_client() as c:
        data = c.get(f"/users/{c.user_id}/calendar-personals")
    emit(data, out)


@cal.command("events")
@click.option("--from", "from_date", required=True, help="조회 시작일 (YYYY-MM-DD 또는 ISO 8601)")
@click.option("--to", "to_date", required=True, help="조회 종료일 (YYYY-MM-DD 또는 ISO 8601)")
@click.option("--calendar", "calendar_id", help="캘린더 ID (생략 시 기본 캘린더)")
@click.option("--timezone", "tz", default=_DEFAULT_TZ, help="타임존 (기본: Asia/Seoul)")
@click.option("--json", "as_json", is_flag=True, help="JSON 출력")
@click.pass_context
@handle_errors
def cal_events(
    ctx: click.Context,
    from_date: str,
    to_date: str,
    calendar_id: Optional[str],
    tz: str,
    as_json: bool,
) -> None:
    """캘린더 일정 목록 조회."""
    out = resolve_output(ctx.obj, as_json)
    params = {
        "fromDateTime": _normalize_datetime(from_date, "00:00:00", tz),
        "untilDateTime": _normalize_datetime(to_date, "23:59:59", tz),
    }
    with get_client() as c:
        if calendar_id:
            path = f"/users/{c.user_id}/calendars/{calendar_id}/events"
        else:
            path = f"/users/{c.user_id}/calendar/events"
        data = c.get(path, params=params)
    emit(data, out)


@cal.command("show")
@click.argument("event_id")
@click.option("--calendar", "calendar_id", help="캘린더 ID (생략 시 기본 캘린더)")
@click.option("--json", "as_json", is_flag=True, help="JSON 출력")
@click.pass_context
@handle_errors
def cal_show(
    ctx: click.Context,
    event_id: str,
    calendar_id: Optional[str],
    as_json: bool,
) -> None:
    """일정 상세 조회."""
    out = resolve_output(ctx.obj, as_json)
    with get_client() as c:
        if calendar_id:
            path = f"/users/{c.user_id}/calendars/{calendar_id}/events/{event_id}"
        else:
            path = f"/users/{c.user_id}/calendar/events/{event_id}"
        data = c.get(path)
    emit(data, out)


@cal.command("create")
@click.option("--summary", required=True, help="일정 제목")
@click.option("--start", required=True, help="시작 (ISO 8601, e.g. 2026-05-22T10:00:00)")
@click.option("--end", required=True, help="종료 (ISO 8601)")
@click.option("--description", default=None, help="설명")
@click.option("--attendees", default=None, help="참석자 이메일 콤마 구분")
@click.option("--calendar", "calendar_id", help="캘린더 ID")
@click.option("--timezone", "tz", default=_DEFAULT_TZ, help="타임존")
@click.option(
    "--payload",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="JSON payload 파일 (이 옵션 사용 시 다른 옵션은 무시)",
)
@click.option("--json", "as_json", is_flag=True, help="JSON 출력")
@click.pass_context
@handle_errors
def cal_create(
    ctx: click.Context,
    summary: str,
    start: str,
    end: str,
    description: Optional[str],
    attendees: Optional[str],
    calendar_id: Optional[str],
    tz: str,
    payload: Optional[Path],
    as_json: bool,
) -> None:
    """일정 생성 (write scope 필요).

    실제 API 페이로드 스키마는 사내 문서를 참조하세요. 스키마가 맞지 않으면
    `--payload @file.json`으로 raw payload를 직접 전달할 수 있습니다.
    """
    out = resolve_output(ctx.obj, as_json)
    if payload is not None:
        body = json.loads(payload.read_text(encoding="utf-8"))
    else:
        body = {
            "eventComponents": [
                {
                    "summary": summary,
                    "start": {
                        "dateTime": _normalize_datetime(start, "00:00:00", tz),
                        "timeZone": tz,
                    },
                    "end": {
                        "dateTime": _normalize_datetime(end, "00:00:00", tz),
                        "timeZone": tz,
                    },
                }
            ]
        }
        ec = body["eventComponents"][0]
        if description:
            ec["description"] = description
        if attendees:
            ec["attendees"] = [{"email": a.strip()} for a in attendees.split(",") if a.strip()]
    with get_client() as c:
        if calendar_id:
            path = f"/users/{c.user_id}/calendars/{calendar_id}/events"
        else:
            path = f"/users/{c.user_id}/calendar/events"
        data = c.post(path, json=body)
    emit(data, out)
