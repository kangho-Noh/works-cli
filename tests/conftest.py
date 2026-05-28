"""테스트 공용 fixture.

env-var only 정책에 맞춰 가짜 PAT만 inject. user 식별자는 'me' self-alias.
실제 PAT는 절대 사용하지 않으며, 모든 테스트는 respx mock으로 동작.
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner

FAKE_PAT = "test-pat-do-not-use"
FAKE_USER = "me"  # NAVER Works self-alias
FAKE_BASE_URL = "https://test.example/v1.0"


@pytest.fixture(autouse=True)
def fake_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """모든 테스트에 가짜 env 주입."""
    monkeypatch.setenv("WORKS_PAT", FAKE_PAT)
    monkeypatch.setenv("WORKS_BASE_URL", FAKE_BASE_URL)
    monkeypatch.delenv("WORKS_DEFAULT_TZ", raising=False)
    monkeypatch.delenv("WORKS_INTERNAL_DOMAINS", raising=False)


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()
