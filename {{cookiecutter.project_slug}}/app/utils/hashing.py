"""Generic hashing utilities."""

from __future__ import annotations

import hashlib


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()
