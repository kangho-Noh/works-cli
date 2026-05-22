"""httpx 기반 NAVER WORKS API 클라이언트."""

from __future__ import annotations

from typing import Any

import httpx

from .config import Config

_ERROR_MESSAGES: dict[int, str] = {
    401: "PAT가 만료되었거나 잘못되었습니다. `works-cli config set-pat`으로 재설정하세요.",
    403: "Scope 부족 또는 권한 없음. PAT 발급 시 필요한 scope를 확인하세요.",
    404: "리소스를 찾을 수 없습니다.",
    429: "요청 한도를 초과했습니다. 잠시 후 다시 시도하세요.",
}


class WorksAPIError(Exception):
    def __init__(self, status_code: int, message: str, body: Any = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.body = body


class WorksClient:
    def __init__(self, config: Config, timeout: float = 30.0) -> None:
        self._config = config
        self._client = httpx.Client(
            base_url=config.base_url,
            headers={
                "Authorization": f"Bearer {config.pat}",
                "Accept": "application/json",
            },
            timeout=timeout,
        )

    @property
    def user_id(self) -> str:
        return self._config.user_id

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "WorksClient":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def request(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            response = self._client.request(method, path, **kwargs)
        except httpx.RequestError as e:
            raise WorksAPIError(0, f"네트워크 오류: {e}") from e

        if response.is_success:
            if response.status_code == 204 or not response.content:
                return None
            try:
                return response.json()
            except ValueError:
                return response.text

        try:
            body: Any = response.json()
        except ValueError:
            body = response.text or None

        msg = _ERROR_MESSAGES.get(response.status_code)
        if msg is None:
            if response.status_code >= 500:
                msg = f"서버 오류 (status {response.status_code})"
            else:
                msg = f"요청 실패 (status {response.status_code})"

        if isinstance(body, dict):
            api_msg = body.get("message") or body.get("error_description") or body.get("error")
            if api_msg:
                msg = f"{msg} — {api_msg}"

        raise WorksAPIError(response.status_code, msg, body=body)

    def get(self, path: str, **kwargs: Any) -> Any:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> Any:
        return self.request("POST", path, **kwargs)

    def put(self, path: str, **kwargs: Any) -> Any:
        return self.request("PUT", path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> Any:
        return self.request("DELETE", path, **kwargs)
