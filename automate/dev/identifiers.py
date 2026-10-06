"""Shared deterministic identity and canonical serialization helpers."""
from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def sha256(value: Any) -> str:
    data = value if isinstance(value, (bytes, bytearray)) else canonical_json(value).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def deterministic_id(prefix: str, *parts: Any) -> str:
    return f"{prefix}_{sha256(parts)[:32]}"
