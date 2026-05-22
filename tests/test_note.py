"""note 명령 통합 테스트."""

from __future__ import annotations

import json

import respx
from click.testing import CliRunner

from works_cli.cli import cli

from .conftest import FAKE_BASE_URL


def _url(path: str) -> str:
    return f"{FAKE_BASE_URL}{path}"


@respx.mock
def test_note_list(runner: CliRunner) -> None:
    respx.get(_url("/groups/g1/note/posts")).respond(
        200, json={"posts": [{"postId": "p1"}]}
    )

    result = runner.invoke(cli, ["note", "list", "--group", "g1", "--json"])

    assert result.exit_code == 0, result.output
    assert "p1" in result.output


@respx.mock
def test_note_show(runner: CliRunner) -> None:
    respx.get(_url("/groups/g1/note/posts/p1")).respond(
        200, json={"postId": "p1", "title": "hi"}
    )

    result = runner.invoke(
        cli, ["note", "show", "p1", "--group", "g1", "--json"]
    )

    assert result.exit_code == 0, result.output


@respx.mock
def test_note_create(runner: CliRunner) -> None:
    route = respx.post(_url("/groups/g1/note/posts")).respond(200, json={"postId": "new"})

    result = runner.invoke(
        cli,
        ["note", "create", "--group", "g1", "--title", "T", "--body", "B", "--json"],
    )

    assert result.exit_code == 0, result.output
    body = json.loads(route.calls[0].request.content)
    assert body == {"title": "T", "body": "B"}


def test_note_create_missing_body(runner: CliRunner) -> None:
    result = runner.invoke(
        cli, ["note", "create", "--group", "g1", "--title", "T"]
    )
    assert result.exit_code != 0


@respx.mock
def test_note_delete(runner: CliRunner) -> None:
    respx.delete(_url("/groups/g1/note/posts/p1")).respond(204)

    result = runner.invoke(
        cli, ["note", "delete", "p1", "--group", "g1", "--json"]
    )

    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == {"ok": True, "deleted": "p1"}
