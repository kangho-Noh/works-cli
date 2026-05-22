"""테스트 공용 fixture.

실제 PAT는 절대 사용하지 않는다. 모든 테스트는 가짜 PAT + respx mock으로 동작.
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner

FAKE_PAT = "test-pat-do-not-use"
FAKE_USER = "tester@example.com"
FAKE_BASE_URL = "https://test.example/v1.0"


@pytest.fixture(autouse=True)
def fake_env(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """모든 테스트에 가짜 env 주입. HOME도 격리해 실제 ~/.works-cli를 건드리지 않음."""
    monkeypatch.setenv("WORKS_PAT", FAKE_PAT)
    monkeypatch.setenv("WORKS_USER_ID", FAKE_USER)
    monkeypatch.setenv("WORKS_BASE_URL", FAKE_BASE_URL)
    monkeypatch.setenv("HOME", str(tmp_path))


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()
