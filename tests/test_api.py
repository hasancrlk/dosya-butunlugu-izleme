"""End-to-end API tests using FastAPI TestClient."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient

# Ensure in-memory DB
os.environ["FIM_DATABASE_URL"] = "sqlite:///:memory:"

from app.db.session import reset_engine  # noqa: E402
from app.main import create_app  # noqa: E402


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    """Yield a TestClient whose lifespan (init_db) has been triggered."""
    reset_engine()
    app = create_app()
    with TestClient(app) as c:
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
