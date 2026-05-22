"""bot 명령 통합 테스트."""

from __future__ import annotations

import json

import respx
from click.testing import CliRunner

from works_cli.cli import cli

from .conftest import FAKE_BASE_URL


def _url(path: str) -> str:
    return f"{FAKE_BASE_URL}{path}"


@respx.mock
def test_bot_list(runner: CliRunner) -> None:
    respx.get(_url("/bots")).respond(200, json={"bots": [{"botId": "b1"}]})

    result = runner.invoke(cli, ["bot", "list", "--json"])

    assert result.exit_code == 0, result.output
    assert "b1" in result.output


@respx.mock
def test_bot_info(runner: CliRunner) -> None:
    respx.get(_url("/bots/b1")).respond(200, json={"botId": "b1", "name": "tester"})

    result = runner.invoke(cli, ["bot", "info", "b1", "--json"])

    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["name"] == "tester"


@respx.mock
def test_bot_send_default_text(runner: CliRunner) -> None:
    route = respx.post(_url("/bots/b1/users/u@x.com/messages")).respond(
        200, json={"ok": True}
    )

    result = runner.invoke(
        cli,
        ["bot", "send", "--bot", "b1", "--user", "u@x.com", "--message", "안녕"],
    )

    assert result.exit_code == 0, result.output
    body = json.loads(route.calls[0].request.content)
    assert body == {"content": {"type": "text", "text": "안녕"}}


@respx.mock
def test_bot_send_channel(runner: CliRunner) -> None:
    route = respx.post(_url("/bots/b1/channels/ch1/messages")).respond(
        200, json={}
    )

    result = runner.invoke(
        cli,
        ["bot", "send-channel", "--bot", "b1", "--channel", "ch1", "--message", "ping"],
    )

    assert result.exit_code == 0, result.output
    body = json.loads(route.calls[0].request.content)
    assert body["content"]["text"] == "ping"


@respx.mock
def test_bot_send_payload_override(runner: CliRunner, tmp_path) -> None:
    p = tmp_path / "p.json"
    p.write_text(json.dumps({"content": {"type": "sticker", "packageId": 1}}))
    route = respx.post(_url("/bots/b1/users/u@x.com/messages")).respond(200, json={})

    result = runner.invoke(
        cli,
        [
            "bot",
            "send",
            "--bot",
            "b1",
            "--user",
            "u@x.com",
            "--payload",
            str(p),
        ],
    )

    assert result.exit_code == 0, result.output
    body = json.loads(route.calls[0].request.content)
    assert body["content"]["type"] == "sticker"


def test_bot_send_missing_message_errors(runner: CliRunner) -> None:
    result = runner.invoke(
        cli, ["bot", "send", "--bot", "b1", "--user", "u@x.com"]
    )
    assert result.exit_code != 0
