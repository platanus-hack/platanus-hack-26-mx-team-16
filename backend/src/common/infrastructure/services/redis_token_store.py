from dataclasses import dataclass

from redis.asyncio import Redis

from src.common.domain.services.token_store import TokenStore


@dataclass
class RedisTokenStore(TokenStore):
    redis_client: Redis

    async def store_token(self, sub: str, jti: str, ttl: int, namespace: str):
        await self.redis_client.setex(f"{namespace}_RT:{sub}", ttl, jti)

    async def get_token_jti(self, sub: str, namespace: str) -> str | None:
        return await self.redis_client.get(f"{namespace}_RT:{sub}")

    async def blacklist_token_jti(self, jti: str, ttl: int, namespace: str):
        if ttl <= 0:
            return
        await self.redis_client.setex(f"{namespace}_BL:{jti}", ttl, 1)

    async def blacklist_token_sub(self, sub: str, ttl: int, namespace: str):
        token_jti = await self.get_token_jti(sub, namespace)
        if not token_jti:
            return
        await self.blacklist_token_jti(token_jti, ttl=ttl, namespace=namespace)

    async def is_blacklisted(self, jti: str, namespace: str) -> bool:
        return await self.redis_client.exists(f"{namespace}_BL:{jti}") == 1

    async def clean(self, jti: str, sub: str, namespace: str) -> bool:
        await self.redis_client.delete(f"{namespace}_RT:{sub}")
        await self.redis_client.delete(f"{namespace}_BL:{jti}")
        return await self.redis_client.delete(f"{namespace}_BL:{jti}")
