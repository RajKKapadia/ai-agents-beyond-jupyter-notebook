"""Redis client module for managing async Redis connections."""
import redis.asyncio as redis
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class RedisClient:
    """Singleton Redis client with connection pooling."""
    
    _instance: Optional["RedisClient"] = None
    _client: Optional[redis.Redis] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize Redis client (only once due to singleton pattern)."""
        if self._client is None:
            # Will be initialized on first connect
            pass
    
    async def connect(self, redis_url: str = "redis://localhost:6379") -> None:
        """
        Connect to Redis server.
        
        Args:
            redis_url: Redis connection URL (default: redis://localhost:6379)
        """
        try:
            self._client = await redis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=10,
            )
            # Test connection
            await self._client.ping()
            logger.info(f"✅ Connected to Redis at {redis_url}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Redis: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info("🔌 Disconnected from Redis")
    
    async def get(self, key: str) -> Optional[str]:
        """
        Get value from Redis.
        
        Args:
            key: Redis key
            
        Returns:
            Value as string or None if not found
        """
        if not self._client:
            raise RuntimeError("Redis client not connected. Call connect() first.")
        
        try:
            return await self._client.get(key)
        except Exception as e:
            logger.error(f"Error getting key {key}: {e}")
            return None
    
    async def set(
        self, 
        key: str, 
        value: str, 
        ex: Optional[int] = None
    ) -> bool:
        """
        Set value in Redis with optional expiration.
        
        Args:
            key: Redis key
            value: Value to store
            ex: Expiration time in seconds (optional)
            
        Returns:
            True if successful, False otherwise
        """
        if not self._client:
            raise RuntimeError("Redis client not connected. Call connect() first.")
        
        try:
            await self._client.set(key, value, ex=ex)
            return True
        except Exception as e:
            logger.error(f"Error setting key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """
        Delete key from Redis.
        
        Args:
            key: Redis key to delete
            
        Returns:
            True if key was deleted, False otherwise
        """
        if not self._client:
            raise RuntimeError("Redis client not connected. Call connect() first.")
        
        try:
            result = await self._client.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"Error deleting key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """
        Check if key exists in Redis.
        
        Args:
            key: Redis key
            
        Returns:
            True if key exists, False otherwise
        """
        if not self._client:
            raise RuntimeError("Redis client not connected. Call connect() first.")
        
        try:
            result = await self._client.exists(key)
            return result > 0
        except Exception as e:
            logger.error(f"Error checking key {key}: {e}")
            return False
    
    @property
    def is_connected(self) -> bool:
        """Check if Redis client is connected."""
        return self._client is not None


# Global Redis client instance
redis_client = RedisClient()
