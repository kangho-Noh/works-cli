"""cal(endar) 명령 (Calendar API).

read 명령 (R): list / events / show     — read scope PAT로 동작
write 명령 (W): create                   — write scope PAT 필요
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from zoneinfo import ZoneInfo

import click
from dateutil.rrule import rrulestr

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


def _parse_component_dt(slot: dict, fallback_tz: str) -> datetime:
    """{'dateTime': '...', 'timeZone': '...'}에서 tz-aware datetime."""
    raw = slot.get("dateTime", "")
    dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo(slot.get("timeZone") or fallback_tz))
    return dt


def _component_instance(ec: dict, *, recurring: bool, start_dt: datetime, end_dt: datetime) -> dict:
    """eventComponent → 평면화된 instance dict."""
    return {
        "eventId": ec.get("eventId"),
        "summary": ec.get("summary"),
        "description": ec.get("description"),
        "location": ec.get("location"),
        "organizer": ec.get("organizer"),
        "attendees": ec.get("attendees", []),
        "start": {
            "dateTime": start_dt.isoformat(),
            "timeZone": ec.get("start", {}).get("timeZone"),
        },
        "end": {
            "dateTime": end_dt.isoformat(),
            "timeZone": ec.get("end", {}).get("timeZone"),
        },
        "transparency": ec.get("transparency"),
        "isRecurringInstance": recurring,
    }


def _expand_events(data: dict, from_dt: datetime, to_dt: datetime) -> dict:
    """API 응답의 반복 일정을 RRULE로 펴서 instance 평면 리스트로 변환."""
    instances: list[dict] = []
    for evt in data.get("events", []):
        components = evt.get("eventComponents", [])
        master = next((ec for ec in components if ec.get("recurrence")), None)
        exceptions = [ec for ec in components if not ec.get("recurrence")]

        if master:
            tz_name = master.get("start", {}).get("timeZone") or _DEFAULT_TZ
            ms = _parse_component_dt(master["start"], tz_name)
            me = _parse_component_dt(master["end"], tz_name)
            duration = me - ms
            rule_text = "\n".join(master.get("recurrence", []))
            try:
                rule = rrulestr(rule_text, dtstart=ms, forceset=True)
                # between은 naive dtstart를 요구할 수 있어 aware/naive 일관 유지
                for occ in rule.between(from_dt, to_dt, inc=True):
                    instances.append(
                        _component_instance(
                            master, recurring=True, start_dt=occ, end_dt=occ + duration
                        )
                    )
            except (ValueError, TypeError):
                if from_dt <= ms <= to_dt:
                    instances.append(
                        _component_instance(master, recurring=True, start_dt=ms, end_dt=me)
                    )

        for ec in exceptions:
            tz_name = ec.get("start", {}).get("timeZone") or _DEFAULT_TZ
            try:
                es = _parse_component_dt(ec["start"], tz_name)
                ee = _parse_component_dt(ec["end"], tz_name)
            except (KeyError, ValueError):
                continue
            if from_dt <= es <= to_dt:
                instances.append(
                    _component_instance(ec, recurring=False, start_dt=es, end_dt=ee)
                )

    instances.sort(key=lambda x: x["start"]["dateTime"])
    return {"instances": instances, "totalCount": len(instances)}


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
@click.option(
    "--expand",
    is_flag=True,
    help="반복 일정의 RRULE을 평가해 인스턴스 시각으로 펴서 반환 (응답 형식: {instances, totalCount})",
)
@click.option("--json", "as_json", is_flag=True, help="JSON 출력")
@click.pass_context
@handle_errors
def cal_events(
    ctx: click.Context,
    from_date: str,
    to_date: str,
    calendar_id: Optional[str],
    tz: str,
    expand: bool,
    as_json: bool,
) -> None:
    """캘린더 일정 목록 조회.

    NAVER WORKS API는 반복 일정을 펴서 주지 않고 마스터 + EXDATE 형태로 응답한다.
    오늘/이번 주의 실제 인스턴스 시각이 필요하면 --expand를 쓴다.
    """
    out = resolve_output(ctx.obj, as_json)
    from_str = _normalize_datetime(from_date, "00:00:00", tz)
    to_str = _normalize_datetime(to_date, "23:59:59", tz)
    params = {"fromDateTime": from_str, "untilDateTime": to_str}
    with get_client() as c:
        if calendar_id:
            path = f"/users/{c.user_id}/calendars/{calendar_id}/events"
        else:
            path = f"/users/{c.user_id}/calendar/events"
        data = c.get(path, params=params)
    if expand:
        from_dt = datetime.fromisoformat(from_str)
        to_dt = datetime.fromisoformat(to_str)
        data = _expand_events(data, from_dt, to_dt)
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
