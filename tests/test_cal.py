"""cal 명령 통합 테스트."""

from __future__ import annotations

import json

import respx
from click.testing import CliRunner

from works_cli.cli import cli

from .conftest import FAKE_BASE_URL, FAKE_USER


def _url(path: str) -> str:
    return f"{FAKE_BASE_URL}{path}"


@respx.mock
def test_cal_list(runner: CliRunner) -> None:
    respx.get(_url(f"/users/{FAKE_USER}/calendar-personals")).respond(
        200, json={"calendars": []}
    )

    result = runner.invoke(cli, ["cal", "list", "--json"])

    assert result.exit_code == 0, result.output


@respx.mock
def test_cal_events_default_calendar(runner: CliRunner) -> None:
    route = respx.get(_url(f"/users/{FAKE_USER}/calendar/events")).respond(
        200, json={"events": []}
    )

    result = runner.invoke(
        cli,
        ["cal", "events", "--from", "2026-05-22", "--to", "2026-05-23", "--json"],
    )

    assert result.exit_code == 0, result.output
    sent = route.calls[0].request
    # offset이 datetime에 inline (+09:00 → %2B09%3A00), 별도 timeZone param 없음
    assert b"fromDateTime=2026-05-22T00%3A00%3A00%2B09%3A00" in sent.url.query
    assert b"untilDateTime=2026-05-23T23%3A59%3A59%2B09%3A00" in sent.url.query
    assert b"timeZone=" not in sent.url.query


@respx.mock
def test_cal_events_offset_already_present(runner: CliRunner) -> None:
    route = respx.get(_url(f"/users/{FAKE_USER}/calendar/events")).respond(
        200, json={"events": []}
    )

    result = runner.invoke(
        cli,
        [
            "cal",
            "events",
            "--from",
            "2026-05-22T10:00:00+09:00",
            "--to",
            "2026-05-22T11:00:00+09:00",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    # 사용자가 offset을 명시하면 이중으로 붙이지 않음
    sent = route.calls[0].request
    assert b"fromDateTime=2026-05-22T10%3A00%3A00%2B09%3A00" in sent.url.query


@respx.mock
def test_cal_events_specific_calendar(runner: CliRunner) -> None:
    route = respx.get(
        _url(f"/users/{FAKE_USER}/calendars/cal-1/events")
    ).respond(200, json={"events": []})

    result = runner.invoke(
        cli,
        [
            "cal",
            "events",
            "--calendar",
            "cal-1",
            "--from",
            "2026-05-22",
            "--to",
            "2026-05-23",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    assert route.called


@respx.mock
def test_cal_show(runner: CliRunner) -> None:
    respx.get(_url(f"/users/{FAKE_USER}/calendar/events/evt-1")).respond(
        200, json={"id": "evt-1"}
    )

    result = runner.invoke(cli, ["cal", "show", "evt-1", "--json"])

    assert result.exit_code == 0, result.output


@respx.mock
def test_cal_create_default_payload(runner: CliRunner) -> None:
    route = respx.post(_url(f"/users/{FAKE_USER}/calendar/events")).respond(
        200, json={"id": "evt-new"}
    )

    result = runner.invoke(
        cli,
        [
            "cal",
            "create",
            "--summary",
            "회의",
            "--start",
            "2026-05-23T10:00:00",
            "--end",
            "2026-05-23T11:00:00",
            "--description",
            "주간",
            "--attendees",
            "a@x.com,b@x.com",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    body = json.loads(route.calls[0].request.content)
    ec = body["eventComponents"][0]
    assert ec["summary"] == "회의"
    assert ec["start"]["dateTime"] == "2026-05-23T10:00:00+09:00"
    assert ec["start"]["timeZone"] == "Asia/Seoul"
    assert ec["description"] == "주간"
    assert [a["email"] for a in ec["attendees"]] == ["a@x.com", "b@x.com"]


@respx.mock
def test_cal_create_payload_override(runner: CliRunner, tmp_path) -> None:
    payload_file = tmp_path / "p.json"
    payload_file.write_text(json.dumps({"raw": "yes"}))
    route = respx.post(_url(f"/users/{FAKE_USER}/calendar/events")).respond(
        200, json={}
    )

    result = runner.invoke(
        cli,
        [
            "cal",
            "create",
            "--summary",
            "ignored",
            "--start",
            "2026-05-23T10:00:00",
            "--end",
            "2026-05-23T11:00:00",
            "--payload",
            str(payload_file),
        ],
    )

    assert result.exit_code == 0, result.output
    assert json.loads(route.calls[0].request.content) == {"raw": "yes"}


def test_cal_events_bad_date(runner: CliRunner) -> None:
    result = runner.invoke(
        cli,
        ["cal", "events", "--from", "2026/05/22", "--to", "2026-05-23"],
    )
    assert result.exit_code != 0
    assert "날짜" in result.output


@respx.mock
def test_cal_events_expand_weekly_with_exdate(runner: CliRunner) -> None:
    """매주 금요일 반복 + 5/15 EXDATE → 5/4(월)~5/29(금) 범위 expand 시 5/8, 5/22 두 건."""
    api_payload = {
        "events": [
            {
                "eventComponents": [
                    {
                        "eventId": "evt-1",
                        "summary": "주간 회의",
                        "start": {"dateTime": "2026-05-01T11:00:00", "timeZone": "Asia/Seoul"},
                        "end": {"dateTime": "2026-05-01T12:00:00", "timeZone": "Asia/Seoul"},
                        "recurrence": [
                            "RRULE:FREQ=WEEKLY;INTERVAL=1;BYDAY=FR",
                            "EXDATE;TZID=Asia/Seoul:20260515T110000",
                        ],
                        "organizer": {"email": "boss@x.com", "displayName": "팀장"},
                    }
                ]
            }
        ]
    }
    respx.get(_url(f"/users/{FAKE_USER}/calendar/events")).respond(200, json=api_payload)

    result = runner.invoke(
        cli,
        ["cal", "events", "--from", "2026-05-04", "--to", "2026-05-29", "--expand", "--json"],
    )

    assert result.exit_code == 0, result.output
    out = json.loads(result.output)
    # 범위 5/4~5/29에 5/8, 5/22, 5/29 (5/15는 EXDATE 제외)
    assert out["totalCount"] == 3
    starts = [i["start"]["dateTime"] for i in out["instances"]]
    assert starts == [
        "2026-05-08T11:00:00+09:00",
        "2026-05-22T11:00:00+09:00",
        "2026-05-29T11:00:00+09:00",
    ]
    assert not any(s.startswith("2026-05-15") for s in starts)
    assert all(i["isRecurringInstance"] for i in out["instances"])


@respx.mock
def test_cal_events_expand_single_event(runner: CliRunner) -> None:
    """단발 일정도 expand에서 instance로 포함."""
    api_payload = {
        "events": [
            {
                "eventComponents": [
                    {
                        "eventId": "one-shot",
                        "summary": "단발 회의",
                        "start": {"dateTime": "2026-05-22T14:00:00", "timeZone": "Asia/Seoul"},
                        "end": {"dateTime": "2026-05-22T15:00:00", "timeZone": "Asia/Seoul"},
                    }
                ]
            }
        ]
    }
    respx.get(_url(f"/users/{FAKE_USER}/calendar/events")).respond(200, json=api_payload)

    result = runner.invoke(
        cli,
        ["cal", "events", "--from", "2026-05-22", "--to", "2026-05-22", "--expand", "--json"],
    )

    assert result.exit_code == 0, result.output
    out = json.loads(result.output)
    assert out["totalCount"] == 1
    inst = out["instances"][0]
    assert inst["summary"] == "단발 회의"
    assert inst["isRecurringInstance"] is False


@respx.mock
def test_cal_events_expand_filters_out_of_range(runner: CliRunner) -> None:
    """범위 밖 인스턴스는 제외."""
    api_payload = {
        "events": [
            {
                "eventComponents": [
                    {
                        "summary": "매일 회의",
                        "start": {"dateTime": "2026-05-01T09:00:00", "timeZone": "Asia/Seoul"},
                        "end": {"dateTime": "2026-05-01T09:30:00", "timeZone": "Asia/Seoul"},
                        "recurrence": ["RRULE:FREQ=DAILY;COUNT=10"],
                    }
                ]
            }
        ]
    }
    respx.get(_url(f"/users/{FAKE_USER}/calendar/events")).respond(200, json=api_payload)

    result = runner.invoke(
        cli,
        ["cal", "events", "--from", "2026-05-03", "--to", "2026-05-05", "--expand", "--json"],
    )

    assert result.exit_code == 0, result.output
    out = json.loads(result.output)
    # 5/1, 5/2, ..., 5/10 중 5/3, 5/4, 5/5만
    assert out["totalCount"] == 3
    assert [i["start"]["dateTime"][:10] for i in out["instances"]] == [
        "2026-05-03",
        "2026-05-04",
        "2026-05-05",
    ]


@respx.mock
def test_cal_events_expand_master_plus_exception(runner: CliRunner) -> None:
    """master + exception component (recurrence 없음) 케이스 — exception도 instance로 포함."""
    api_payload = {
        "events": [
            {
                "eventComponents": [
                    {
                        "summary": "주간 회의",
                        "start": {"dateTime": "2026-05-01T11:00:00", "timeZone": "Asia/Seoul"},
                        "end": {"dateTime": "2026-05-01T12:00:00", "timeZone": "Asia/Seoul"},
                        "recurrence": [
                            "RRULE:FREQ=WEEKLY;BYDAY=FR",
                            "EXDATE;TZID=Asia/Seoul:20260508T110000",
                        ],
                    },
                    {
                        "summary": "[대면] 주간 회의",
                        "start": {"dateTime": "2026-05-08T13:00:00", "timeZone": "Asia/Seoul"},
                        "end": {"dateTime": "2026-05-08T14:00:00", "timeZone": "Asia/Seoul"},
                    },
                ]
            }
        ]
    }
    respx.get(_url(f"/users/{FAKE_USER}/calendar/events")).respond(200, json=api_payload)

    result = runner.invoke(
        cli,
        ["cal", "events", "--from", "2026-05-01", "--to", "2026-05-15", "--expand", "--json"],
    )

    assert result.exit_code == 0, result.output
    out = json.loads(result.output)
    summaries = [i["summary"] for i in out["instances"]]
    starts = [i["start"]["dateTime"] for i in out["instances"]]
    # 마스터: 5/1, 5/15 (5/8은 EXDATE) + exception: 5/8 [대면]
    assert "[대면] 주간 회의" in summaries
    assert "2026-05-08T13:00:00+09:00" in starts
    assert "2026-05-08T11:00:00+09:00" not in starts  # EXDATE로 master 인스턴스는 제거


@respx.mock
def test_cal_events_no_expand_returns_raw(runner: CliRunner) -> None:
    """--expand 없으면 raw API 응답 그대로."""
    api_payload = {"events": [{"eventComponents": [{"summary": "x"}]}]}
    respx.get(_url(f"/users/{FAKE_USER}/calendar/events")).respond(200, json=api_payload)

    result = runner.invoke(
        cli, ["cal", "events", "--from", "2026-05-22", "--to", "2026-05-22", "--json"]
    )

    assert result.exit_code == 0, result.output
    out = json.loads(result.output)
    assert "events" in out
    assert "instances" not in out
