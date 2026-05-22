"""cli config 명령(set-pat, show) 테스트."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from works_cli.cli import cli


def test_config_show(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["config", "show"])
    assert result.exit_code == 0, result.output
    assert "USER_ID" in result.output
    assert "tester@example.com" in result.output
    # PAT는 마스킹돼야 한다 — 원본 문자열이 그대로 나오면 안 됨
    assert "test-pat-do-not-use" not in result.output


def test_config_set_pat_prompts_and_saves(
    runner: CliRunner, monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    # set-pat은 env가 없어도 동작해야 함
    monkeypatch.delenv("WORKS_PAT", raising=False)
    monkeypatch.delenv("WORKS_USER_ID", raising=False)

    result = runner.invoke(
        cli,
        ["config", "set-pat"],
        input="new-pat\nuser@me.com\n\n",
    )

    assert result.exit_code == 0, result.output
    cfg_path = tmp_path / ".works-cli" / "config.json"
    assert cfg_path.exists()
    data = json.loads(cfg_path.read_text())
    assert data["pat"] == "new-pat"
    assert data["user_id"] == "user@me.com"
