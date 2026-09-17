"""End-to-end API tests using FastAPI TestClient."""

from __future__ import annotations

import json
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.db.session import get_session, reset_engine
from app.main import create_app
from app.models.audit_log import AuditLog
from app.models.baseline import BaselineEntry


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    """Authenticated TestClient allowed to scan only tmp_path."""
    monkeypatch.setenv("FIM_ALLOWED_PATHS", json.dumps([str(tmp_path)]))
    get_settings.cache_clear()
    reset_engine()
    with TestClient(create_app(), headers={"X-API-Key": "test-api-key"}) as c:
        yield c


def test_health(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_baseline_then_scan_then_report(
    client: TestClient, sample_dir: Path
) -> None:
    """Full workflow: baseline → scan (no changes) → report."""
    # 1. Create baseline
    resp = client.post("/api/v1/baseline", json={"target_path": str(sample_dir)})
    assert resp.status_code == 201
    data = resp.json()
    assert data["file_count"] >= 1
    baseline_id = data["id"]

    # 2. Scan (no modifications → zero findings expected)
    resp = client.post("/api/v1/scan", json={"baseline_id": baseline_id})
    assert resp.status_code == 201
    scan_data = resp.json()
    scan_id = scan_data["id"]
    assert scan_data["total_modified"] == 0
    assert scan_data["total_added"] == 0
    assert scan_data["total_deleted"] == 0

    # 3. Report — JSON
    resp = client.get(f"/api/v1/reports/{scan_id}?format=json")
    assert resp.status_code == 200
    report = resp.json()
    assert report["scan_id"] == scan_id

    # 4. Report — CSV
    resp = client.get(f"/api/v1/reports/{scan_id}?format=csv")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]


def test_scan_detects_modification(
    client: TestClient, sample_dir: Path
) -> None:
    # Baseline
    resp = client.post("/api/v1/baseline", json={"target_path": str(sample_dir)})
    baseline_id = resp.json()["id"]

    # Mutate
    (sample_dir / "file_a.txt").write_text("TAMPERED CONTENT")

    # Scan
    resp = client.post("/api/v1/scan", json={"baseline_id": baseline_id})
    assert resp.status_code == 201
    scan_data = resp.json()
    assert scan_data["total_modified"] >= 1


def test_baseline_not_found(client: TestClient) -> None:
    resp = client.post("/api/v1/scan", json={"baseline_id": 9999})
    assert resp.status_code == 404


def test_report_not_found(client: TestClient) -> None:
    resp = client.get("/api/v1/reports/9999")
    assert resp.status_code == 404


def test_missing_api_key_rejected(client: TestClient) -> None:
    resp = client.post("/api/v1/scan", json={"baseline_id": 1}, headers={"X-API-Key": "wrong"})
    assert resp.status_code == 401


def test_path_outside_allowlist_forbidden(client: TestClient) -> None:
    resp = client.post("/api/v1/baseline", json={"target_path": "/etc"})
    assert resp.status_code == 403


def test_tampered_baseline_detected(client: TestClient, sample_dir: Path) -> None:
    baseline_id = client.post(
        "/api/v1/baseline", json={"target_path": str(sample_dir)}
    ).json()["id"]

    # Attacker modifies the file AND rewrites the stored hash to hide it
    (sample_dir / "file_a.txt").write_text("backdoor")
    with get_session() as db:
        entry = db.query(BaselineEntry).filter(BaselineEntry.file_path.like("%file_a.txt")).one()
        entry.sha256 = "0" * 64

    resp = client.post("/api/v1/scan", json={"baseline_id": baseline_id})
    assert resp.status_code == 409


def test_audit_chain_detects_edit(client: TestClient, sample_dir: Path) -> None:
    client.post("/api/v1/baseline", json={"target_path": str(sample_dir)})
    assert client.get("/api/v1/audit/verify").json()["intact"] is True

    with get_session() as db:
        db.query(AuditLog).first().detail = "rewritten"

    body = client.get("/api/v1/audit/verify").json()
    assert body["intact"] is False
    assert body["first_broken_id"] == 1
