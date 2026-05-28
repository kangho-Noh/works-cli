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
    # 외부 게이트 우회를 위해 --allow-external 사용 (whoami GET 안 함)
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
            "--allow-external",
            "--yes",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    body = json.loads(route.calls[0].request.content)
    assert body["subject"] == "hello"
    assert body["body"] == "world"
    assert body["contentType"] == "text"
    assert body["to"] == "a@x.com;b@x.com"
    assert body["cc"] == "c@x.com"


@respx.mock
def test_mail_send_html_flag(runner: CliRunner) -> None:
    route = respx.post(_url(f"/users/{FAKE_USER}/mail")).respond(200, json={})

    result = runner.invoke(
        cli,
        ["mail", "send", "--to", "a@x.com", "--subject", "s", "--body", "<b>", "--html", "--allow-external", "--yes"],
    )

    assert result.exit_code == 0, result.output
    assert json.loads(route.calls[0].request.content)["contentType"] == "html"


@respx.mock
def test_mail_send_with_payload_override(runner: CliRunner, tmp_path) -> None:
    payload_file = tmp_path / "payload.json"
    payload_file.write_text(json.dumps({"custom": True, "to": "x@example.com"}))
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
            "--allow-external",
            "--yes",
        ],
    )

    assert result.exit_code == 0, result.output
    sent = json.loads(route.calls[0].request.content)
    assert sent["custom"] is True


@respx.mock
def test_mail_send_missing_body_errors(runner: CliRunner) -> None:
    result = runner.invoke(
        cli, ["mail", "send", "--to", "a@x.com", "--subject", "s", "--allow-external", "--yes"]
    )
    assert result.exit_code != 0
    assert "--body" in result.output or "payload" in result.output


@respx.mock
def test_mail_send_dry_run_default(runner: CliRunner) -> None:
    """--yes 없으면 호출하지 않고 exit 4."""
    route = respx.post(_url(f"/users/{FAKE_USER}/mail")).respond(200, json={})

    result = runner.invoke(
        cli,
        ["mail", "send", "--to", "a@x.com", "--subject", "s", "--body", "b", "--allow-external"],
    )

    assert result.exit_code == 4
    assert not route.called


@respx.mock
def test_mail_send_external_gate_blocks(runner: CliRunner) -> None:
    """--allow-external 없으면 외부 수신자 차단."""
    # whoami로 sender 도메인 확인
    respx.get(_url(f"/users/{FAKE_USER}")).respond(
        200, json={"email": "me@inside.com"}
    )
    route = respx.post(_url(f"/users/{FAKE_USER}/mail")).respond(200, json={})

    result = runner.invoke(
        cli,
        ["mail", "send", "--to", "outside@x.com", "--subject", "s", "--body", "b", "--yes"],
    )

    assert result.exit_code == 4
    assert not route.called
    assert "외부" in result.output


@respx.mock
def test_mail_send_internal_passes_external_gate(runner: CliRunner) -> None:
    """본인 도메인 수신자는 외부 게이트 통과."""
    respx.get(_url(f"/users/{FAKE_USER}")).respond(
        200, json={"email": "me@inside.com"}
    )
    route = respx.post(_url(f"/users/{FAKE_USER}/mail")).respond(200, json={"id": "m1"})

    result = runner.invoke(
        cli,
        ["mail", "send", "--to", "colleague@inside.com", "--subject", "s", "--body", "b", "--yes"],
    )

    assert result.exit_code == 0, result.output
    assert route.called


@respx.mock
def test_mail_send_burst_guard_blocks_repeat(runner: CliRunner) -> None:
    """동일 페이로드 10초 내 재호출 차단."""
    route = respx.post(_url(f"/users/{FAKE_USER}/mail")).respond(200, json={})

    args = [
        "mail",
        "send",
        "--to",
        "a@x.com",
        "--subject",
        "s",
        "--body",
        "b",
        "--allow-external",
        "--yes",
    ]
    r1 = runner.invoke(cli, args)
    r2 = runner.invoke(cli, args)

    assert r1.exit_code == 0, r1.output
    assert r2.exit_code == 4
    assert "burst" in r2.output.lower()
    assert route.call_count == 1


@respx.mock
def test_mail_read_redacts_body_by_default(runner: CliRunner) -> None:
    respx.get(_url(f"/users/{FAKE_USER}/mail/m1")).respond(
        200, json={"mail": {"mailId": "m1", "subject": "hi", "body": "비밀 본문"}}
    )

    result = runner.invoke(cli, ["mail", "read", "m1", "--json"])

    assert result.exit_code == 0, result.output
    out = json.loads(result.output)
    body = out["mail"]["body"]
    assert "비밀" not in body
    assert "redacted" in body


@respx.mock
def test_mail_read_show_pii_exposes_body(runner: CliRunner) -> None:
    respx.get(_url(f"/users/{FAKE_USER}/mail/m1")).respond(
        200, json={"mail": {"mailId": "m1", "subject": "hi", "body": "비밀 본문"}}
    )

    result = runner.invoke(cli, ["mail", "read", "m1", "--show-pii", "--json"])

    assert result.exit_code == 0, result.output
    assert "비밀 본문" in result.output


@respx.mock
def test_mail_unread_403_message(runner: CliRunner) -> None:
    respx.get(_url(f"/users/{FAKE_USER}/mail/unread-count")).respond(
        403, json={"message": "forbidden"}
    )

    result = runner.invoke(cli, ["mail", "unread"])

    assert result.exit_code == 2
    assert "Scope" in result.output or "Scope" in (result.stderr or "")
