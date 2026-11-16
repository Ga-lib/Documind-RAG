"""Tests for the shared API-key dependency."""

import pytest
from fastapi import HTTPException

from app.api.security import require_api_key
from app.config.settings import settings


def test_api_key_is_not_required_when_unconfigured(monkeypatch):
    monkeypatch.setattr(settings, "documind_api_key", None)
    assert require_api_key(None) is None


def test_api_key_rejects_missing_or_invalid_values(monkeypatch):
    monkeypatch.setattr(settings, "documind_api_key", "a" * 32)
    with pytest.raises(HTTPException) as missing:
        require_api_key(None)
    assert missing.value.status_code == 401
    with pytest.raises(HTTPException) as invalid:
        require_api_key("wrong-key")
    assert invalid.value.status_code == 401


def test_api_key_accepts_matching_value(monkeypatch):
    key = "a" * 32
    monkeypatch.setattr(settings, "documind_api_key", key)
    assert require_api_key(key) is None
