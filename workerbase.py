import aioredis

class WorkerBase:
    def __init__(self):
        self._redis = None
    
    @property
    def redis(self) -> aioredis.Redis:
        return self._redis
    
    async def main(self):
        self._redis = await aioredis.create_redis_pool('redis://localhost')
        
        try:
            await self.start()
        except KeyboardInterrupt:
            pass

        self.redis.close()
        await self.redis.wait_closed()