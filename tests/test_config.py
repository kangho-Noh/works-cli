"""config 로드/마스킹 테스트 (env-var only)."""

from __future__ import annotations

import pytest

from works_cli.config import DEFAULT_BASE_URL, DEFAULT_TZ, ConfigError, load_config, mask_pat


def test_load_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WORKS_PAT", "env-pat")
    monkeypatch.setenv("WORKS_BASE_URL", "https://override.example/v1.0")
    monkeypatch.setenv("WORKS_DEFAULT_TZ", "America/Los_Angeles")
    monkeypatch.setenv("WORKS_INTERNAL_DOMAINS", "a.com, b.com")

    cfg = load_config()

    assert cfg.pat == "env-pat"
    assert cfg.base_url == "https://override.example/v1.0"
    assert cfg.default_tz == "America/Los_Angeles"
    assert cfg.internal_domains == ("a.com", "b.com")


def test_load_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WORKS_PAT", "p")
    monkeypatch.delenv("WORKS_BASE_URL", raising=False)
    monkeypatch.delenv("WORKS_DEFAULT_TZ", raising=False)
    monkeypatch.delenv("WORKS_INTERNAL_DOMAINS", raising=False)

    cfg = load_config()

    assert cfg.base_url == DEFAULT_BASE_URL
    assert cfg.default_tz == DEFAULT_TZ
    assert cfg.internal_domains == ()


def test_load_missing_pat_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WORKS_PAT", raising=False)

    with pytest.raises(ConfigError) as exc:
        load_config()
    assert "WORKS_PAT" in str(exc.value)
    # 디스크 저장 가이드는 안 나와야 함 (env-var only)
    assert "config" not in str(exc.value).lower() or "환경변수" in str(exc.value)


@pytest.mark.parametrize(
    ("pat", "is_short"),
    [("", True), ("abcd", True), ("12345678", True), ("0123456789abcd", False)],
)
def test_mask_pat(pat: str, is_short: bool) -> None:
    result = mask_pat(pat)
    if not pat:
        assert result == ""
    elif is_short:
        assert result == "*" * len(pat)
    else:
        assert result.startswith("****")
        assert result.endswith(pat[-4:])
