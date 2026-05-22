"""mail 명령 통합 테스트 (CliRunner + respx)."""

from __future__ import annotations

import json

import respx
from click.testing import CliRunner

from works_cli.cli import cli

from .conftest import FAKE_BASE_URL, FAKE_USER


def _url(path: str) -> str:
    return f"{FAKE_BASE_URL}{path}"


@respx.mock
def test_mail_unread(runner: CliRunner) -> None:
    respx.get(_url(f"/users/{FAKE_USER}/mail/unread-count")).respond(
        200, json={"count": 7}
    )

    result = runner.invoke(cli, ["mail", "unread", "--json"])

    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == {"count": 7}


@respx.mock
def test_mail_folders(runner: CliRunner) -> None:
    respx.get(_url(f"/users/{FAKE_USER}/mail/mailfolders")).respond(
        200, json={"mailFolders": [{"id": "INBOX", "name": "Inbox"}]}
    )

    result = runner.invoke(cli, ["mail", "folders", "--json"])

    assert result.exit_code == 0, result.output
    assert "INBOX" in result.output


@respx.mock
def test_mail_list_with_params(runner: CliRunner) -> None:
    route = respx.get(_url(f"/users/{FAKE_USER}/mail/mailfolders/0/children")).respond(
        200, json={"mails": []}
    )

    result = runner.invoke(
        cli,
        ["mail", "list", "--folder", "0", "--limit", "10", "--cursor", "c1", "--json"],
    )

    assert result.exit_code == 0, result.output
    sent = route.calls[0].request
    assert b"count=10" in sent.url.query
    assert b"cursor=c1" in sent.url.query


@respx.mock
def test_mail_list_unread_flag(runner: CliRunner) -> None:
    route = respx.get(_url(f"/users/{FAKE_USER}/mail/mailfolders/0/children")).respond(
        200, json={"mails": []}
    )

    result = runner.invoke(
        cli, ["mail", "list", "--folder", "0", "--unread", "--json"]
    )

    assert result.exit_code == 0, result.output
    assert b"isUnread=true" in route.calls[0].request.url.query


@respx.mock
def test_mail_list_search_filter(runner: CliRunner) -> None:
    route = respx.get(_url(f"/users/{FAKE_USER}/mail/mailfolders/0/children")).respond(
        200, json={"mails": []}
    )

    result = runner.invoke(
        cli, ["mail", "list", "--folder", "0", "--filter", "mark", "--json"]
    )

    assert result.exit_code == 0, result.output
    assert b"searchFilterType=mark" in route.calls[0].request.url.query


@respx.mock
def test_mail_read(runner: CliRunner) -> None:
    respx.get(_url(f"/users/{FAKE_USER}/mail/12345")).respond(
        200, json={"id": "12345", "subject": "hi"}
    )

    result = runner.invoke(cli, ["mail", "read", "12345", "--json"])

    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["id"] == "12345"


@respx.mock
def test_mail_send_default_payload(runner: CliRunner) -> None:
    route = respx.post(_url(f"/users/{FAKE_USER}/mail")).respond(200, json={"id": "m1"})

    result = runner.invoke(
        cli,
        [
            "mail",
            "send",
            "--to",
            "a@x.com",
            "--to",
            "b@x.com",
            "--cc",
            "c@x.com",
            "--subject",
            "hello",
            "--body",
            "world",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    body = json.loads(route.calls[0].request.content)
    assert body["subject"] == "hello"
    assert body["body"] == "world"
    assert body["contentType"] == "text"
    # to/cc는 세미콜론 구분 문자열
    assert body["to"] == "a@x.com;b@x.com"
    assert body["cc"] == "c@x.com"


@respx.mock
def test_mail_send_html_flag(runner: CliRunner) -> None:
    route = respx.post(_url(f"/users/{FAKE_USER}/mail")).respond(200, json={})

    result = runner.invoke(
        cli,
        ["mail", "send", "--to", "a@x.com", "--subject", "s", "--body", "<b>", "--html"],
    )

    assert result.exit_code == 0, result.output
    assert json.loads(route.calls[0].request.content)["contentType"] == "html"


@respx.mock
def test_mail_send_with_payload_override(runner: CliRunner, tmp_path) -> None:
    payload_file = tmp_path / "payload.json"
    payload_file.write_text(json.dumps({"custom": True}))
    route = respx.post(_url(f"/users/{FAKE_USER}/mail")).respond(200, json={})

    result = runner.invoke(
        cli,
        [
            "mail",
            "send",
            "--to",
            "a@x.com",
            "--subject",
            "s",
            "--payload",
            str(payload_file),
        ],
    )

    assert result.exit_code == 0, result.output
    assert json.loads(route.calls[0].request.content) == {"custom": True}


@respx.mock
def test_mail_send_missing_body_errors(runner: CliRunner) -> None:
    result = runner.invoke(
        cli, ["mail", "send", "--to", "a@x.com", "--subject", "s"]
    )
    assert result.exit_code != 0
    assert "--body" in result.output or "payload" in result.output


@respx.mock
def test_mail_unread_403_message(runner: CliRunner) -> None:
    respx.get(_url(f"/users/{FAKE_USER}/mail/unread-count")).respond(
        403, json={"message": "forbidden"}
    )

    result = runner.invoke(cli, ["mail", "unread"])

    assert result.exit_code == 2
    assert "Scope" in result.output or "Scope" in (result.stderr or "")
