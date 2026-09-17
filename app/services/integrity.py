"""HMAC signing for baselines and the tamper-evident audit chain."""

from __future__ import annotations

import hashlib
import hmac
import json
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

from app.config import get_hmac_key


def _get(obj: Any, name: str) -> Any:
    return obj[name] if isinstance(obj, dict) else getattr(obj, name, None)


def sign_baseline(target_path: str, follow_symlinks: bool, entries: Iterable[Any]) -> str:
    """HMAC-SHA256 over a canonical, order-independent form of the baseline."""
    mac = hmac.new(get_hmac_key(), digestmod=hashlib.sha256)
    mac.update(json.dumps([target_path, bool(follow_symlinks)]).encode() + b"\n")
    rows = sorted(
        [_get(e, k) for k in ("file_path", "sha256", "size_bytes", "mode", "uid", "gid")]
        for e in entries
    )
    for row in rows:
        mac.update(json.dumps(row, separators=(",", ":")).encode() + b"\n")
    return mac.hexdigest()


def verify_baseline(baseline: Any) -> bool:
    if not baseline.signature:
        return False
    expected = sign_baseline(baseline.target_path, baseline.follow_symlinks, baseline.entries)
    return hmac.compare_digest(expected, baseline.signature)


def _ts(dt: datetime) -> str:
    if dt.tzinfo is not None:
        dt = dt.astimezone(UTC).replace(tzinfo=None)
    return dt.isoformat(timespec="microseconds")


def audit_entry_hash(
    prev_hash: str, timestamp: datetime, action: str, actor: str, detail: str | None
) -> str:
    payload = json.dumps([prev_hash, _ts(timestamp), action, actor, detail or ""])
    return hmac.new(get_hmac_key(), payload.encode(), hashlib.sha256).hexdigest()
