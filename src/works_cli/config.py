"""환경변수 → ~/.works-cli/config.json 순으로 PAT/userId/baseUrl 로드."""

from __future__ import annotations

import json
import os
import stat
from dataclasses import dataclass
from pathlib import Path

DEFAULT_BASE_URL = "https://corp.worksapis.com/v1.0"


def _config_dir() -> Path:
    return Path.home() / ".works-cli"


def _config_file() -> Path:
    return _config_dir() / "config.json"


class ConfigError(Exception):
    """설정 누락/손상."""


@dataclass(frozen=True)
class Config:
    pat: str
    user_id: str
    base_url: str


def load_config() -> Config:
    pat = os.environ.get("WORKS_PAT") or None
    user_id = os.environ.get("WORKS_USER_ID") or None
    base_url = os.environ.get("WORKS_BASE_URL") or None

    cfg_file = _config_file()
    if cfg_file.exists() and (pat is None or user_id is None or base_url is None):
        try:
            data = json.loads(cfg_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise ConfigError(f"설정 파일({cfg_file})이 손상되었습니다: {e}") from e
        if pat is None:
            pat = data.get("pat")
        if user_id is None:
            user_id = data.get("user_id")
        if base_url is None:
            base_url = data.get("base_url")

    if base_url is None:
        base_url = DEFAULT_BASE_URL

    if not pat:
        raise ConfigError(
            "WORKS_PAT가 설정되지 않았습니다. `works-cli config set-pat`을 실행하거나 환경변수 WORKS_PAT를 설정하세요."
        )
    if not user_id:
        raise ConfigError(
            "WORKS_USER_ID가 설정되지 않았습니다. `works-cli config set-pat`을 실행하거나 환경변수 WORKS_USER_ID를 설정하세요."
        )

    return Config(pat=pat, user_id=user_id, base_url=base_url)


def save_config(cfg: Config) -> Path:
    cfg_dir = _config_dir()
    cfg_dir.mkdir(parents=True, exist_ok=True)
    cfg_file = _config_file()
    cfg_file.write_text(
        json.dumps(
            {"pat": cfg.pat, "user_id": cfg.user_id, "base_url": cfg.base_url},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    cfg_file.chmod(stat.S_IRUSR | stat.S_IWUSR)
    return cfg_file


def mask_pat(pat: str) -> str:
    if not pat:
        return ""
    if len(pat) <= 8:
        return "*" * len(pat)
    return f"****{pat[-4:]}"
