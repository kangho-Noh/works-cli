"""출력 포맷 헬퍼. 기본 텍스트, --json 또는 --output json 시 raw JSON."""

from __future__ import annotations

import json
import sys
from typing import Any, Mapping


def _print_value(value: Any, indent: int = 0) -> None:
    prefix = "  " * indent
    if isinstance(value, Mapping):
        for k, v in value.items():
            if isinstance(v, (Mapping, list)):
                print(f"{prefix}{k}:")
                _print_value(v, indent + 1)
            else:
                print(f"{prefix}{k}: {v}")
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, (Mapping, list)):
                _print_value(item, indent)
                print()
            else:
                print(f"{prefix}- {item}")
    elif value is None:
        return
    else:
        print(f"{prefix}{value}")


def emit(data: Any, output: str = "text") -> None:
    if output == "json":
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return
    _print_value(data)


def warn(message: str) -> None:
    print(message, file=sys.stderr)


def resolve_output(ctx_obj: Mapping[str, Any] | None, as_json_flag: bool) -> str:
    if as_json_flag:
        return "json"
    if ctx_obj and ctx_obj.get("output"):
        return str(ctx_obj["output"])
    return "text"
