"""
Redis Cache Layer for SapioCode
Handles: Session state, frustration scores, mastery cache, hint rate limiting
"""
import os
import json
from typing import Optional, Dict, Any

try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


class RedisCache:
    """Async Redis cache for real-time state management"""

    def __init__(self):
        self._client = None
        self._connected = False

    async def connect(self):
        if not REDIS_AVAILABLE:
            print("[Redis] redis package not installed, running without cache")
            return
        try:
            self._client = aioredis.from_url(
                REDIS_URL, encoding="utf-8", decode_responses=True
            )
            await self._client.ping()
            self._connected = True
            print(f"[Redis] Connected to {REDIS_URL}")
        except Exception as e:
            print(f"[Redis] Connection failed: {e}. Running without cache.")
            self._connected = False

    async def disconnect(self):
        if self._client and self._connected:
            await self._client.close()
            self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    # ─── Session State ─────────────────────────────────────
    async def set_session(self, student_id: str, problem_id: str,
                          state: Dict[str, Any], ttl: int = 3600):
        if not self._connected:
            return
        key = f"session:{student_id}:{problem_id}"
        await self._client.setex(key, ttl, json.dumps(state))

    async def get_session(self, student_id: str, problem_id: str) -> Optional[Dict[str, Any]]:
        if not self._connected:
            return None
        key = f"session:{student_id}:{problem_id}"
        data = await self._client.get(key)
        return json.loads(data) if data else None

    async def delete_session(self, student_id: str, problem_id: str):
        if not self._connected:
            return
        await self._client.delete(f"session:{student_id}:{problem_id}")

    # ─── Frustration Score (Real-time from Face-API.js) ────
    async def set_frustration(self, student_id: str, score: float,
                              emotions: Dict[str, float] = None):
        if not self._connected:
            return
        key = f"frustration:{student_id}"
        data = {"score": score, "emotions": emotions or {}}
        await self._client.setex(key, 30, json.dumps(data))  # 30s TTL

    async def get_frustration(self, student_id: str) -> Optional[Dict[str, Any]]:
        if not self._connected:
            return None
        key = f"frustration:{student_id}"
        data = await self._client.get(key)
        return json.loads(data) if data else None

    # ─── BKT Mastery Cache ─────────────────────────────────
    async def cache_mastery(self, student_id: str, concept: str, mastery: float):
        if not self._connected:
            return
        key = f"mastery:{student_id}:{concept}"
        await self._client.setex(key, 300, str(mastery))  # 5 min TTL

    async def get_cached_mastery(self, student_id: str, concept: str) -> Optional[float]:
        if not self._connected:
            return None
        key = f"mastery:{student_id}:{concept}"
        data = await self._client.get(key)
        return float(data) if data else None

    # ─── Hint Rate Limiting ────────────────────────────────
    async def increment_hint_count(self, student_id: str, problem_id: str) -> int:
        if not self._connected:
            return 0
        key = f"hints:{student_id}:{problem_id}"
        count = await self._client.incr(key)
        if count == 1:
            await self._client.expire(key, 3600)
        return count

    async def get_hint_count(self, student_id: str, problem_id: str) -> int:
        if not self._connected:
            return 0
        key = f"hints:{student_id}:{problem_id}"
        count = await self._client.get(key)
        return int(count) if count else 0

    # ─── Collaboration Room State ──────────────────────────
    async def set_room_state(self, room_id: str, state: Dict[str, Any]):
        if not self._connected:
            return
        await self._client.setex(f"room:{room_id}", 7200, json.dumps(state))

    async def get_room_state(self, room_id: str) -> Optional[Dict[str, Any]]:
        if not self._connected:
            return None
        data = await self._client.get(f"room:{room_id}")
        return json.loads(data) if data else None

    # ─── Class Pulse (Teacher Dashboard) ───────────────────
    async def update_class_pulse(self, class_id: str, student_id: str,
                                  data: Dict[str, Any]):
        if not self._connected:
            return
        key = f"pulse:{class_id}"
        await self._client.hset(key, student_id, json.dumps(data))
        await self._client.expire(key, 7200)

    async def get_class_pulse(self, class_id: str) -> Dict[str, Any]:
        if not self._connected:
            return {}
        raw = await self._client.hgetall(f"pulse:{class_id}")
        return {k: json.loads(v) for k, v in raw.items()}


# ─── Singleton ─────────────────────────────────────────────
_redis_cache: Optional[RedisCache] = None


def get_redis_cache() -> RedisCache:
    global _redis_cache
    if _redis_cache is None:
        _redis_cache = RedisCache()
    return _redis_cache
