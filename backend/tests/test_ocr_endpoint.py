import time
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.api.deps import redis_dep
from app.core import security
from app.core.config import settings


class FakeRedisPipeline:
    def __init__(self, redis):
        self.redis = redis
        self.ops = []

    def incr(self, key, amount=1):
        self.ops.append(("incr", key, amount))
        return self

    def expire(self, key, ttl):
        self.ops.append(("expire", key, ttl))
        return self

    async def execute(self):
        results = []
        for op, key, val in self.ops:
            if op == "incr":
                results.append(await self.redis.incr(key, val))
            elif op == "expire":
                results.append(await self.redis.expire(key, val))
        self.ops.clear()
        return results


class FakeRedis:
    def __init__(self):
        self.store = {}
        self.expiry = {}

    async def hgetall(self, key):
        if self._expired(key):
            return {}
        return self.store.get(key, {}).copy()

    async def hset(self, key, mapping):
        if self._expired(key):
            self.store.pop(key, None)
        current = self.store.get(key, {})
        current.update(mapping)
        self.store[key] = current

    async def expire(self, key, ttl):
        self.expiry[key] = time.time() + ttl
        return True

    async def ttl(self, key):
        if key not in self.expiry:
            return -1
        return max(0, int(self.expiry[key] - time.time()))

    async def set(self, key, value, ex=None, nx=False):
        if nx and key in self.store and not self._expired(key):
            return False
        self.store[key] = value
        if ex:
            await self.expire(key, ex)
        return True

    async def delete(self, key):
        self.store.pop(key, None)
        self.expiry.pop(key, None)

    def pipeline(self):
        return FakeRedisPipeline(self)

    async def incr(self, key, amount=1):
        if self._expired(key):
            self.store.pop(key, None)
        self.store[key] = int(self.store.get(key, 0)) + amount
        return self.store[key]

    async def get(self, key):
        if self._expired(key):
            return None
        return self.store.get(key)

    def _expired(self, key):
        exp = self.expiry.get(key)
        return exp is not None and time.time() > exp


def make_app():
    app = create_app()
    fake_redis = FakeRedis()

    async def override_redis():
        yield fake_redis

    def override_subject():
        return "user-test"

    app.dependency_overrides[redis_dep] = override_redis
    app.dependency_overrides[security.get_current_subject] = override_subject
    return app, fake_redis


def test_ocr_cache_miss_then_hit():
    app, _ = make_app()
    client = TestClient(app)
    body = {"image_url": "https://example.com/img1.png"}
    resp1 = client.post("/v1/ocr", json=body, headers={"Authorization": "Bearer x"})
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["cache_hit"] is False

    resp2 = client.post("/v1/ocr", json=body, headers={"Authorization": "Bearer x"})
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["cache_hit"] is True
    assert data2["text"] == data1["text"]


def test_ocr_idempotency_replay():
    app, _ = make_app()
    client = TestClient(app)
    body = {"image_url": "https://example.com/img2.png"}
    headers = {"Authorization": "Bearer x", "idempotency-key": "abc123"}

    first = client.post("/v1/ocr", json=body, headers=headers)
    assert first.status_code == 200

    replay = client.post("/v1/ocr", json=body, headers=headers)
    assert replay.status_code == 200
    data = replay.json()
    assert data["cache_hit"] is True
    assert "request_id" in data
    assert data["request_id"]  # Should be non-empty


def test_rate_limit_exceeded(monkeypatch):
    app, _ = make_app()
    client = TestClient(app)
    original_limit = settings.rate_limit_requests
    monkeypatch.setattr(settings, "rate_limit_requests", 1)
    body = {"image_url": "https://example.com/img3.png"}
    headers = {"Authorization": "Bearer x"}

    first = client.post("/v1/ocr", json=body, headers=headers)
    assert first.status_code == 200
    second = client.post("/v1/ocr", json=body, headers=headers)
    assert second.status_code == 429
    monkeypatch.setattr(settings, "rate_limit_requests", original_limit)

