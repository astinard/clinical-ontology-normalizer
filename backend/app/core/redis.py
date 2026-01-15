"""Redis connection management."""

from redis import Redis

from app.core.config import settings

# Redis connection instance (lazy initialized)
_redis_client: Redis | None = None


def get_redis() -> Redis:
    """Get or create Redis connection.

    Returns a Redis client configured from settings.
    Connection is lazily created on first call.

    Returns:
        Redis client instance.
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = Redis.from_url(
            settings.redis_url,
            decode_responses=True,
        )
    return _redis_client


def close_redis() -> None:
    """Close Redis connection.

    Should be called during application shutdown.
    """
    global _redis_client
    if _redis_client is not None:
        _redis_client.close()
        _redis_client = None


def ping_redis() -> bool:
    """Check if Redis connection is healthy.

    Returns:
        True if Redis responds to ping, False otherwise.
    """
    try:
        return bool(get_redis().ping())
    except Exception:
        return False
