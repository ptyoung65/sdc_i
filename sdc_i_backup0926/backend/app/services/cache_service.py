"""
Redis Cache Service for AI responses
"""
import redis
import json
import hashlib
import os
from typing import Optional, Dict, Any
from datetime import timedelta

class CacheService:
    """Cache service for AI responses - supports both Redis and in-memory cache"""

    def __init__(self):
        self.redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        self.cache_enabled = True
        self.default_ttl = 3600  # 1 hour default TTL
        self.redis_client = None
        self.memory_cache = {}  # In-memory fallback cache
        self.use_memory_cache = False

        try:
            # Try without password first for basic testing
            self.redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
            # Test connection
            self.redis_client.ping()
            print("✅ [CACHE] Redis connection established successfully")
        except Exception as e:
            print(f"⚠️ [CACHE] Redis connection failed: {e} - falling back to memory cache")
            self.use_memory_cache = True
            print("✅ [CACHE] Memory cache enabled as fallback")

    def _generate_cache_key(self,
                          message: str,
                          provider: str,
                          search_mode: str = None,
                          use_rag: bool = False,
                          use_web_search: bool = False) -> str:
        """Generate a unique cache key based on query parameters"""
        # Normalize message for consistent caching
        normalized_message = message.strip().lower()

        # Create a hash of the essential request parameters only
        cache_data = {
            "message": normalized_message,
            "provider": provider.lower() if provider else "gemini",
            "use_rag": bool(use_rag),
            "use_web_search": bool(use_web_search)
        }

        # Only include search_mode if it's provided and not None
        if search_mode is not None:
            cache_data["search_mode"] = search_mode

        # Convert to JSON string and hash
        cache_string = json.dumps(cache_data, sort_keys=True)
        cache_hash = hashlib.md5(cache_string.encode()).hexdigest()

        print(f"🔑 [CACHE] Generated cache key for message: '{normalized_message[:30]}...' -> {cache_hash[:8]}...")
        return f"ai_response:{cache_hash}"

    def get_cached_response(self,
                          message: str,
                          provider: str,
                          search_mode: str = None,
                          use_rag: bool = False,
                          use_web_search: bool = False) -> Optional[Dict[str, Any]]:
        """Get cached AI response if available"""
        if not self.cache_enabled:
            return None

        try:
            cache_key = self._generate_cache_key(message, provider, search_mode, use_rag, use_web_search)

            if self.use_memory_cache:
                # Use in-memory cache
                if cache_key in self.memory_cache:
                    print(f"🎯 [CACHE] Memory cache hit for key: {cache_key[:20]}...")
                    return self.memory_cache[cache_key]
                else:
                    print(f"❌ [CACHE] Memory cache miss for key: {cache_key[:20]}...")
                    return None
            elif self.redis_client:
                # Use Redis cache
                cached_data = self.redis_client.get(cache_key)
                if cached_data:
                    print(f"🎯 [CACHE] Redis cache hit for key: {cache_key[:20]}...")
                    return json.loads(cached_data)
                else:
                    print(f"❌ [CACHE] Redis cache miss for key: {cache_key[:20]}...")
                    return None
            else:
                return None

        except Exception as e:
            print(f"⚠️ [CACHE] Error getting cached response: {e}")
            return None

    def set_cached_response(self,
                          message: str,
                          provider: str,
                          response_data: Dict[str, Any],
                          search_mode: str = None,
                          use_rag: bool = False,
                          use_web_search: bool = False,
                          ttl: int = None) -> bool:
        """Cache AI response"""
        if not self.cache_enabled:
            return False

        try:
            cache_key = self._generate_cache_key(message, provider, search_mode, use_rag, use_web_search)
            cache_ttl = ttl or self.default_ttl

            # Add cache metadata
            cache_data = {
                **response_data,
                "_cached_at": json.dumps({"timestamp": "now"}),
                "_cache_key": cache_key
            }

            if self.use_memory_cache:
                # Use in-memory cache (ignore TTL for simplicity)
                self.memory_cache[cache_key] = cache_data
                print(f"💾 [CACHE] Response cached in memory for key: {cache_key[:20]}...")
                return True
            elif self.redis_client:
                # Use Redis cache
                self.redis_client.setex(
                    cache_key,
                    cache_ttl,
                    json.dumps(cache_data)
                )
                print(f"💾 [CACHE] Response cached in Redis for key: {cache_key[:20]}... (TTL: {cache_ttl}s)")
                return True
            else:
                return False

        except Exception as e:
            print(f"⚠️ [CACHE] Error caching response: {e}")
            return False

    def invalidate_cache(self, pattern: str = None) -> int:
        """Invalidate cache entries by pattern"""
        if not self.cache_enabled or not self.redis_client:
            return 0

        try:
            if pattern:
                keys = self.redis_client.keys(pattern)
            else:
                keys = self.redis_client.keys("ai_response:*")

            if keys:
                deleted = self.redis_client.delete(*keys)
                print(f"🗑️ [CACHE] Invalidated {deleted} cache entries")
                return deleted

            return 0

        except Exception as e:
            print(f"⚠️ [CACHE] Error invalidating cache: {e}")
            return 0

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self.cache_enabled or not self.redis_client:
            return {"enabled": False, "error": "Redis not available"}

        try:
            info = self.redis_client.info()
            ai_keys = self.redis_client.keys("ai_response:*")

            return {
                "enabled": True,
                "redis_version": info.get("redis_version"),
                "used_memory": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "ai_response_cache_count": len(ai_keys),
                "total_keys": info.get("db0", {}).get("keys", 0) if "db0" in info else 0
            }

        except Exception as e:
            return {"enabled": False, "error": str(e)}

# Global cache service instance
cache_service = CacheService()

def get_cache_service() -> CacheService:
    """Get cache service instance"""
    return cache_service