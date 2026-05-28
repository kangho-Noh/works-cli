"""cli config show / whoami / --verbose 테스트."""

from __future__ import annotations

import respx
from click.testing import CliRunner

from works_cli.cli import cli

from .conftest import FAKE_BASE_URL, FAKE_USER


def _url(path: str) -> str:
    return f"{FAKE_BASE_URL}{path}"


def test_config_show(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["config", "show"])
    assert result.exit_code == 0, result.output
    assert "BASE_URL" in result.output
    # 마스킹 확인 — 원본 평문 노출 금지
    assert "test-pat-do-not-use" not in result.output


def test_config_set_pat_removed(runner: CliRunner) -> None:
    """env-var only 정책에 따라 set-pat 명령은 제거됨."""
    result = runner.invoke(cli, ["config", "set-pat"])
    assert result.exit_code != 0


@respx.mock
def test_whoami_success(runner: CliRunner) -> None:
    respx.get(_url(f"/users/{FAKE_USER}")).respond(
        200, json={"email": "me@x.com", "userName": {"lastName": "Tester"}}
    )

    result = runner.invoke(cli, ["whoami", "--json"])

    assert result.exit_code == 0, result.output
    assert "me@x.com" in result.output


@respx.mock
def test_whoami_401_exits_2(runner: CliRunner) -> None:
    respx.get(_url(f"/users/{FAKE_USER}")).respond(401, json={"message": "bad"})

    result = runner.invoke(cli, ["whoami"])

    # 표준 exit code: 401 → 2 (auth)
    assert result.exit_code == 2


@respx.mock
def test_whoami_429_exits_3(runner: CliRunner) -> None:
    respx.get(_url(f"/users/{FAKE_USER}")).respond(429)

    result = runner.invoke(cli, ["whoami"])

    # 표준 exit code: 429 → 3 (rate-limit)
    assert result.exit_code == 3


@respx.mock
def test_verbose_masks_authorization(runner: CliRunner) -> None:
    respx.get(_url(f"/users/{FAKE_USER}")).respond(200, json={"email": "me@x.com"})

    result = runner.invoke(cli, ["-v", "whoami", "--json"])

    assert result.exit_code == 0, result.output
    # PAT 평문이 stderr에 노출되면 안 됨
    combined = (result.output or "") + (result.stderr or "")
    assert "test-pat-do-not-use" not in combined
    # 마스킹된 헤더는 stderr에 표시
    assert "Bearer" in (result.stderr or "") or "Bearer" in result.output
