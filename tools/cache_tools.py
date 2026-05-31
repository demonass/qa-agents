import hashlib
import json
from typing import Optional, Any
from config.settings import LLMConfig

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

_redis_client: Optional[Any] = None


def get_redis_client():
    global _redis_client

    if not LLMConfig.LLM_CACHE_ENABLED:
        return None

    if not REDIS_AVAILABLE:
        print(f"⚠️ Redis module not installed, caching disabled (pip install redis)")
        return None

    if _redis_client is None:
        try:
            _redis_client = redis.Redis(
                host=LLMConfig.REDIS_HOST,
                port=LLMConfig.REDIS_PORT,
                db=LLMConfig.REDIS_DB,
                password=LLMConfig.REDIS_PASSWORD,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2
            )
            _redis_client.ping()
            print(f"✅ Redis connected: {LLMConfig.REDIS_HOST}:{LLMConfig.REDIS_PORT}")
        except Exception as e:
            print(f"⚠️ Redis error: {e}, caching disabled")
            _redis_client = None

    return _redis_client


def generate_cache_key(intent_type: str, query: str, model_name: Optional[str] = None) -> str:
    content = f"{intent_type}:{query}:{model_name or 'default'}"
    return f"llm_cache:{hashlib.sha256(content.encode()).hexdigest()}"


def get_cached_response(intent_type: str, query: str, model_name: Optional[str] = None) -> Optional[str]:
    if not LLMConfig.LLM_CACHE_ENABLED:
        return None

    client = get_redis_client()
    if client is None:
        return None

    try:
        key = generate_cache_key(intent_type, query, model_name)
        cached = client.get(key)
        if cached:
            print(f"🎯 Cache HIT for '{query[:50]}...' → {intent_type}")
        else:
            print(f"📭 Cache MISS for '{query[:50]}...'")
        return cached
    except Exception as e:
        print(f"⚠️ Cache get error: {e}")
        return None


def set_cached_response(
    intent_type: str,
    query: str,
    response: str,
    model_name: Optional[str] = None
) -> bool:
    if not LLMConfig.LLM_CACHE_ENABLED:
        return False

    client = get_redis_client()
    if client is None:
        return False

    try:
        key = generate_cache_key(intent_type, query, model_name)
        client.setex(key, LLMConfig.LLM_CACHE_TTL, response)
        return True
    except Exception as e:
        print(f"⚠️ Cache set error: {e}")
        return False


def clear_cache() -> int:
    client = get_redis_client()
    if client is None:
        return 0

    try:
        keys = client.keys("llm_cache:*")
        if keys:
            return client.delete(*keys)
        return 0
    except Exception as e:
        print(f"⚠️ Cache clear error: {e}")
        return 0


def get_cache_stats() -> dict:
    client = get_redis_client()
    if client is None:
        return {"enabled": False, "keys": 0}

    try:
        keys = client.keys("llm_cache:*")
        return {
            "enabled": True,
            "keys": len(keys),
            "ttl_seconds": LLMConfig.LLM_CACHE_TTL
        }
    except Exception as e:
        return {"enabled": True, "error": str(e)}