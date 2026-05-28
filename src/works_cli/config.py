"""환경변수에서 PAT/base URL을 로드. 토큰 안전성을 위해 디스크 저장은 지원하지 않는다.

WORKS_PAT만 필수. WORKS_BASE_URL/DEFAULT_TZ/INTERNAL_DOMAINS는 옵션.
사용자 식별자는 NAVER Works 'me' self-alias를 사용해 별도 설정 불필요.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_BASE_URL = "https://corp.worksapis.com/v1.0"
DEFAULT_TZ = "Asia/Seoul"


class ConfigError(Exception):
    """설정 누락/잘못됨."""


@dataclass(frozen=True)
class Config:
    pat: str
    base_url: str
    default_tz: str
    internal_domains: tuple[str, ...]


def load_config() -> Config:
    pat = os.environ.get("WORKS_PAT") or None
    if not pat:
        raise ConfigError(
            "WORKS_PAT 환경변수가 설정되지 않았습니다. "
            "PAT는 디스크에 저장하지 않습니다 — 셸에서 `export WORKS_PAT='<your-pat>'`로 주입하세요. "
            "안전한 패턴은 README의 '토큰 설정' 섹션을 참고."
        )

    base_url = os.environ.get("WORKS_BASE_URL") or DEFAULT_BASE_URL
    default_tz = os.environ.get("WORKS_DEFAULT_TZ") or DEFAULT_TZ
    raw_domains = os.environ.get("WORKS_INTERNAL_DOMAINS") or ""
    internal_domains = tuple(
        d.strip().lower() for d in raw_domains.split(",") if d.strip()
    )

    return Config(
        pat=pat,
        base_url=base_url,
        default_tz=default_tz,
        internal_domains=internal_domains,
    )


def mask_pat(pat: str) -> str:
    if not pat:
        return ""
    if len(pat) <= 8:
        return "*" * len(pat)
    return f"****{pat[-4:]}"
