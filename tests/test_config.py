"""config 로드/저장/마스킹 테스트."""

from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest

from works_cli.config import (
    DEFAULT_BASE_URL,
    Config,
    ConfigError,
    load_config,
    mask_pat,
    save_config,
)


def test_load_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WORKS_PAT", "env-pat")
    monkeypatch.setenv("WORKS_USER_ID", "env-user@example.com")
    monkeypatch.setenv("WORKS_BASE_URL", "https://override.example/v1.0")

    cfg = load_config()

    assert cfg.pat == "env-pat"
    assert cfg.user_id == "env-user@example.com"
    assert cfg.base_url == "https://override.example/v1.0"


def test_load_default_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WORKS_PAT", "p")
    monkeypatch.setenv("WORKS_USER_ID", "u@e")
    monkeypatch.delenv("WORKS_BASE_URL", raising=False)

    cfg = load_config()

    assert cfg.base_url == DEFAULT_BASE_URL


def test_load_falls_back_to_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("WORKS_PAT", raising=False)
    monkeypatch.delenv("WORKS_USER_ID", raising=False)
    monkeypatch.delenv("WORKS_BASE_URL", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))

    cfg_dir = tmp_path / ".works-cli"
    cfg_dir.mkdir()
    (cfg_dir / "config.json").write_text(
        json.dumps(
            {
                "pat": "file-pat",
                "user_id": "file-user@example.com",
                "base_url": "https://file.example/v1.0",
            }
        )
    )

    cfg = load_config()

    assert cfg.pat == "file-pat"
    assert cfg.user_id == "file-user@example.com"
    assert cfg.base_url == "https://file.example/v1.0"


def test_load_missing_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("WORKS_PAT", raising=False)
    monkeypatch.delenv("WORKS_USER_ID", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))

    with pytest.raises(ConfigError):
        load_config()


def test_save_config_writes_0600(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))

    path = save_config(
        Config(pat="p", user_id="u@e", base_url="https://b.example/v1.0")
    )

    assert path == tmp_path / ".works-cli" / "config.json"
    mode = stat.S_IMODE(path.stat().st_mode)
    assert mode == 0o600

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data == {"pat": "p", "user_id": "u@e", "base_url": "https://b.example/v1.0"}


@pytest.mark.parametrize(
    ("pat", "expected"),
    [
        ("", ""),
        ("abcd", "****"),
        ("12345678", "********"),
        ("0123456789abcd", "****9abcd"[:-1] + "abcd"),
    ],
)
def test_mask_pat(pat: str, expected: str) -> None:
    # 마지막 케이스 expected는 위에서 동적 계산하지 말고 직접 단언
    result = mask_pat(pat)
    if pat and len(pat) > 8:
        assert result.startswith("****")
        assert result.endswith(pat[-4:])
    else:
        assert result == expected


def test_load_corrupt_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("WORKS_PAT", raising=False)
    monkeypatch.delenv("WORKS_USER_ID", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))

    cfg_dir = tmp_path / ".works-cli"
    cfg_dir.mkdir()
    (cfg_dir / "config.json").write_text("{not valid json")

    with pytest.raises(ConfigError) as exc:
        load_config()
    assert "손상" in str(exc.value)
