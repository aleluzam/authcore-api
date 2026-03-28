import redis.asyncio as redis

from app.settings import settings

redis_client = redis.from_url(settings.redis_url)