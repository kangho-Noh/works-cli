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
    assert b"fromDateTime=2026-05-22T00%3A00%3A00" in sent.url.query
    assert b"untilDateTime=2026-05-23T23%3A59%3A59" in sent.url.query
    assert b"timeZone=Asia%2FSeoul" in sent.url.query


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
    assert ec["start"]["dateTime"] == "2026-05-23T10:00:00"
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
