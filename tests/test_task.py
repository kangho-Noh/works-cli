"""task 명령 통합 테스트."""

from __future__ import annotations

import json

import respx
from click.testing import CliRunner

from works_cli.cli import cli

from .conftest import FAKE_BASE_URL, FAKE_USER


def _url(path: str) -> str:
    return f"{FAKE_BASE_URL}{path}"


@respx.mock
def test_task_categories(runner: CliRunner) -> None:
    respx.get(_url(f"/users/{FAKE_USER}/task-categories")).respond(
        200, json={"taskCategories": [{"id": "c1", "name": "기본"}]}
    )

    result = runner.invoke(cli, ["task", "categories", "--json"])

    assert result.exit_code == 0, result.output
    assert "c1" in result.output


@respx.mock
def test_task_list_requires_category(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["task", "list", "--json"])
    assert result.exit_code != 0
    # --category가 required이므로 click이 에러


@respx.mock
def test_task_list_with_category(runner: CliRunner) -> None:
    route = respx.get(_url(f"/users/{FAKE_USER}/tasks")).respond(
        200, json={"tasks": [{"taskId": "t1", "title": "do x"}]}
    )

    result = runner.invoke(
        cli, ["task", "list", "--category", "c1", "--limit", "5", "--status", "ALL", "--json"]
    )

    assert result.exit_code == 0, result.output
    sent = route.calls[0].request
    assert b"categoryId=c1" in sent.url.query
    assert b"count=5" in sent.url.query
    assert b"status=ALL" in sent.url.query
    assert "t1" in result.output


@respx.mock
def test_task_show(runner: CliRunner) -> None:
    respx.get(_url("/tasks/t1")).respond(200, json={"taskId": "t1", "title": "X"})

    result = runner.invoke(cli, ["task", "show", "t1", "--json"])

    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["taskId"] == "t1"


@respx.mock
def test_task_create_default_payload(runner: CliRunner) -> None:
    route = respx.post(_url(f"/users/{FAKE_USER}/tasks")).respond(200, json={"taskId": "new"})

    result = runner.invoke(
        cli,
        ["task", "create", "--title", "T", "--description", "D", "--due", "2026-05-23T18:00:00+09:00", "--yes", "--json"],
    )

    assert result.exit_code == 0, result.output
    body = json.loads(route.calls[0].request.content)
    assert body == {"title": "T", "description": "D", "dueDateTime": "2026-05-23T18:00:00+09:00"}


@respx.mock
def test_task_create_dry_run_without_yes(runner: CliRunner) -> None:
    """--yes 없으면 호출하지 않고 exit 4."""
    route = respx.post(_url(f"/users/{FAKE_USER}/tasks")).respond(200, json={"taskId": "new"})

    result = runner.invoke(cli, ["task", "create", "--title", "T"])

    assert result.exit_code == 4
    assert not route.called


@respx.mock
def test_task_complete(runner: CliRunner) -> None:
    respx.post(_url("/tasks/t1/complete")).respond(204)

    result = runner.invoke(cli, ["task", "complete", "t1", "--yes", "--json"])

    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == {"ok": True, "taskId": "t1"}


@respx.mock
def test_task_incomplete(runner: CliRunner) -> None:
    respx.post(_url("/tasks/t1/incomplete")).respond(204)

    result = runner.invoke(cli, ["task", "incomplete", "t1", "--yes", "--json"])

    assert result.exit_code == 0, result.output


@respx.mock
def test_task_delete(runner: CliRunner) -> None:
    respx.delete(_url("/tasks/t1")).respond(204)

    result = runner.invoke(cli, ["task", "delete", "t1", "--yes", "--json"])

    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == {"ok": True, "deleted": "t1"}
