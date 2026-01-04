import asyncio

import pytest

from backend.app import main


@pytest.mark.anyio
async def test_startup_calls_persona_seed(monkeypatch):
    called = {}

    async def fake_ensure_default_personas(session):
        called["seed_called"] = True

    class FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FakeSessionFactory:
        def __call__(self):
            return self

        async def __aenter__(self):
            return FakeSession()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(main, "async_session_factory", FakeSessionFactory())
    monkeypatch.setattr(main, "ensure_default_personas", fake_ensure_default_personas)

    await main.on_startup()

    assert called.get("seed_called") is True
