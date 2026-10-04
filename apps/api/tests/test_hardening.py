from __future__ import annotations

from uuid import UUID

from fastapi.testclient import TestClient


def test_api_responses_include_safety_and_trace_headers(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["permissions-policy"] == (
        "camera=(), microphone=(), geolocation=()"
    )
    assert response.headers["content-security-policy"] == "frame-ancestors 'none'"
    assert response.headers["cache-control"] == "no-store"
    UUID(response.headers["x-request-id"])


def test_each_response_gets_a_distinct_request_id(client: TestClient) -> None:
    first = client.get("/api/health")
    second = client.get("/api/health")

    assert first.headers["x-request-id"] != second.headers["x-request-id"]


def test_error_responses_are_not_cacheable(client: TestClient) -> None:
    response = client.get("/api/does-not-exist")

    assert response.status_code == 404
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
