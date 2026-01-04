from types import SimpleNamespace

import pytest

from backend.app.api import routes_store


@pytest.mark.anyio
async def test_store_status_uses_access_helper(monkeypatch):
    called: dict[str, object] = {}

    async def fake_get_or_raise_telegram_id(request, allow_debug=True):
        called["get_or_raise_telegram_id"] = True
        return 123456

    async def fake_get_or_create_user_by_telegram_id(session, telegram_id):
        called["get_or_create_user_by_telegram_id"] = telegram_id
        return SimpleNamespace(id=1, telegram_id=telegram_id)

    async def fake_build_access_status(session, user):
        called["build_access_status"] = True
        return {
            "has_subscription": False,
            "access_status": "trial_usage",
            "images": {"remaining_paid": 0, "remaining_free_today": 0},
        }

    async def fake_get_active_subscription(session, user_id):
        called["get_active_subscription"] = user_id
        return None

    async def fake_get_image_quota(session, user, has_subscription=False):
        called["get_image_quota"] = has_subscription
        return {"remaining_paid": 0, "remaining_free_today": 0}

    async def fake_collect_feature_states(session, user):
        called["collect_feature_states"] = True
        return {}

    monkeypatch.setattr(routes_store, "get_or_raise_telegram_id", fake_get_or_raise_telegram_id)
    monkeypatch.setattr(routes_store, "get_or_create_user_by_telegram_id", fake_get_or_create_user_by_telegram_id)
    monkeypatch.setattr(routes_store, "build_access_status", fake_build_access_status)
    monkeypatch.setattr(routes_store, "get_active_subscription", fake_get_active_subscription)
    monkeypatch.setattr(routes_store, "get_image_quota", fake_get_image_quota)
    monkeypatch.setattr(routes_store, "collect_feature_states", fake_collect_feature_states)

    result = await routes_store.store_status(request=SimpleNamespace(), session=object())

    assert result["has_active_subscription"] is False
    assert result["remaining_images_today"] == 0
    assert result["remaining_paid_images"] == 0
    assert result["unlocked_features"] == []
    assert called["build_access_status"] is True
