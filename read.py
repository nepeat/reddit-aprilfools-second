import asyncio
import websockets
import aioredis

from api import get_ws_uri

class ReaderClient:
    def __init__(self):
        self.running = True
        self._redis = None
    
    @property
    def redis(self) -> aioredis.Redis:
        return self._redis

    async def main(self):
        self._redis = await aioredis.create_redis_pool('redis://localhost')
        
        try:
            await self.connect_ws()
        except KeyboardInterrupt:
            self.running = False

        self.redis.close()
        await self.redis.wait_closed()

    async def connect_ws(self):
        while self.running:
            try:
                async with websockets.connect(get_ws_uri()) as websocket:
                    async for message in websocket:
                        await self.on_message(message)
            except websockets.exceptions.ConnectionClosedError:
                print("Connection closed, reconnecting in 1 second.")
                await asyncio.sleep(1)

    async def on_message(self, message):
        await self.redis.rpush("reddit:second:socket", message)
        await self.redis.publish("reddit:second:socket", message)
        print(message)

if __name__ == "__main__":
    client = ReaderClient()
    asyncio.get_event_loop().run_until_complete(client.main())