"""client.py 에러 매핑 / 헤더 / 직렬화 테스트."""

from __future__ import annotations

import httpx
import pytest
import respx

from works_cli.client import WorksAPIError, WorksClient
from works_cli.config import Config

from .conftest import FAKE_BASE_URL


def _client() -> WorksClient:
    return WorksClient(Config(pat="test-pat", user_id="u@e", base_url=FAKE_BASE_URL))


@respx.mock
def test_get_success_returns_json() -> None:
    respx.get(f"{FAKE_BASE_URL}/ping").respond(200, json={"ok": True})

    with _client() as c:
        result = c.get("/ping")

    assert result == {"ok": True}


@respx.mock
def test_authorization_header_sent() -> None:
    route = respx.get(f"{FAKE_BASE_URL}/ping").respond(200, json={})

    with _client() as c:
        c.get("/ping")

    request = route.calls[0].request
    assert request.headers["Authorization"] == "Bearer test-pat"


@respx.mock
def test_401_maps_to_pat_error() -> None:
    respx.get(f"{FAKE_BASE_URL}/x").respond(401, json={"message": "Unauthorized"})

    with _client() as c, pytest.raises(WorksAPIError) as exc:
        c.get("/x")

    assert exc.value.status_code == 401
    assert "PAT" in str(exc.value)
    assert "set-pat" in str(exc.value)


@respx.mock
def test_403_maps_to_scope_error() -> None:
    respx.get(f"{FAKE_BASE_URL}/x").respond(403, json={"message": "Forbidden"})

    with _client() as c, pytest.raises(WorksAPIError) as exc:
        c.get("/x")

    assert exc.value.status_code == 403
    assert "Scope" in str(exc.value)


@respx.mock
def test_404_maps_to_not_found() -> None:
    respx.get(f"{FAKE_BASE_URL}/x").respond(404, json={"message": "not found"})

    with _client() as c, pytest.raises(WorksAPIError) as exc:
        c.get("/x")

    assert exc.value.status_code == 404
    assert "찾을 수 없" in str(exc.value)


@respx.mock
def test_429_maps_to_rate_limit() -> None:
    respx.get(f"{FAKE_BASE_URL}/x").respond(429)

    with _client() as c, pytest.raises(WorksAPIError) as exc:
        c.get("/x")

    assert exc.value.status_code == 429
    assert "한도" in str(exc.value)


@respx.mock
def test_5xx_maps_to_server_error() -> None:
    respx.get(f"{FAKE_BASE_URL}/x").respond(503)

    with _client() as c, pytest.raises(WorksAPIError) as exc:
        c.get("/x")

    assert exc.value.status_code == 503
    assert "서버 오류" in str(exc.value)


@respx.mock
def test_204_returns_none() -> None:
    respx.delete(f"{FAKE_BASE_URL}/x").respond(204)

    with _client() as c:
        result = c.delete("/x")

    assert result is None


@respx.mock
def test_post_passes_json_body() -> None:
    route = respx.post(f"{FAKE_BASE_URL}/x").respond(200, json={"id": "1"})

    with _client() as c:
        result = c.post("/x", json={"foo": "bar"})

    assert result == {"id": "1"}
    sent = route.calls[0].request
    assert b'"foo"' in sent.content
    assert b'"bar"' in sent.content


@respx.mock
def test_network_error_wrapped() -> None:
    respx.get(f"{FAKE_BASE_URL}/x").mock(side_effect=httpx.ConnectError("boom"))

    with _client() as c, pytest.raises(WorksAPIError) as exc:
        c.get("/x")

    assert exc.value.status_code == 0
    assert "네트워크" in str(exc.value)


@respx.mock
def test_error_body_message_appended() -> None:
    respx.get(f"{FAKE_BASE_URL}/x").respond(
        400, json={"message": "Bad field 'foo'"}
    )

    with _client() as c, pytest.raises(WorksAPIError) as exc:
        c.get("/x")

    assert "Bad field" in str(exc.value)
