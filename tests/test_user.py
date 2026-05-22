"""user(Directory) 명령 통합 테스트."""

from __future__ import annotations

import json

import respx
from click.testing import CliRunner

from works_cli.cli import cli

from .conftest import FAKE_BASE_URL


def _url(path: str) -> str:
    return f"{FAKE_BASE_URL}{path}"


@respx.mock
def test_user_search_basic(runner: CliRunner) -> None:
    respx.get(_url("/users")).respond(200, json={"users": []})

    result = runner.invoke(cli, ["user", "search", "--json"])

    assert result.exit_code == 0, result.output


@respx.mock
def test_user_search_with_query(runner: CliRunner) -> None:
    route = respx.get(_url("/users")).respond(200, json={"users": []})

    result = runner.invoke(
        cli, ["user", "search", "--query", "kangho", "--limit", "10", "--json"]
    )

    assert result.exit_code == 0, result.output
    sent = route.calls[0].request
    assert b"query=kangho" in sent.url.query
    assert b"count=10" in sent.url.query


@respx.mock
def test_user_show(runner: CliRunner) -> None:
    respx.get(_url("/users/me@x.com")).respond(
        200, json={"email": "me@x.com", "name": "Me"}
    )

    result = runner.invoke(cli, ["user", "show", "me@x.com", "--json"])

    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["name"] == "Me"


@respx.mock
def test_user_orgs(runner: CliRunner) -> None:
    respx.get(_url("/orgunits")).respond(200, json={"orgUnits": []})

    result = runner.invoke(cli, ["user", "orgs", "--json"])

    assert result.exit_code == 0, result.output


@respx.mock
def test_user_org_show(runner: CliRunner) -> None:
    respx.get(_url("/orgunits/o1")).respond(200, json={"orgUnitId": "o1"})

    result = runner.invoke(cli, ["user", "org-show", "o1", "--json"])

    assert result.exit_code == 0, result.output


@respx.mock
def test_user_org_members(runner: CliRunner) -> None:
    route = respx.get(_url("/orgunits/o1/members")).respond(200, json={"members": []})

    result = runner.invoke(
        cli, ["user", "org-members", "o1", "--limit", "20", "--json"]
    )

    assert result.exit_code == 0, result.output
    assert b"count=20" in route.calls[0].request.url.query
