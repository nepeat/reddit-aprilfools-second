import asyncio
import websockets
import aioredis
import json

from api import get_ws_uri

# https://stackoverflow.com/questions/287871/how-to-print-colored-text-to-the-terminal
class CLIColors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class DisplayClient:
    def __init__(self):
        self._redis = None
        self.vote_numbers = {}
    
    @property
    def redis(self) -> aioredis.Redis:
        return self._redis

    async def main(self):
        self._redis = await aioredis.create_redis_pool('redis://localhost')
        
        try:
            await self.connect_redis()
        except KeyboardInterrupt:
            pass

        self.redis.close()
        await self.redis.wait_closed()

    async def connect_redis(self):
        mpsc = aioredis.pubsub.Receiver()
        await self.redis.subscribe(mpsc.channel('reddit:second:socket'))
        async for _channel, msg in mpsc.iter():
            try:
                await self.on_message(msg)
            except KeyError as e:
                print(e)
                print(msg)

    def get_image(self, round: dict, image_id: int):
        for image in round["images"]:
            if image["id"] == image_id:
                return image

    def build_image_output(self, round_data: dict):
        output = []
        votes = sorted([
            max(self.vote_numbers.get(x["name"], 0), x["votes"]) for x in round_data["images"]
        ])

        for image in round_data["images"]:
            image_votes = self.vote_numbers.get(image["name"], 0)

            # Update image votes if it exists.
            new_votes = image.get("votes", self.vote_numbers.get(image["name"], None))
            if new_votes:
                self.vote_numbers[image["name"]] = new_votes
                image_votes = new_votes
        
            # Add to the output.
            if image_votes == 0:
                color = ""
            elif image_votes == votes[1]:
                color = CLIColors.OKGREEN
            else:
                color = CLIColors.FAIL

            output.append(f"{color}{image['name']} [{image_votes}]{CLIColors.ENDC}")

        return ", ".join(output)

    def print_round(self, round: dict, winner: bool = False):
        extra = ""

        if winner:
            output_str = "Round {{round}}: {{votes}} votes, {{img_count}} images ({{image_list}}), winner is '{winner_name}'".format(
                winner_name=self.get_image(round, round["winnerImageId"])["name"]
            )
            votes = sum(image["votes"] for image in round["images"])
        else:
            output_str = "Round {round}: {votes} votes, {img_count} images ({image_list}), {remaining} seconds remaining"
            votes = round["totalVotes"]

        print(output_str.format(
            round=round["id"],
            img_count=len(round["images"]),
            remaining=round.get("secondsLeft", 0.0),
            image_list=self.build_image_output(round),
            votes=votes
        ) + extra)

    async def on_message(self, message):
        message = json.loads(message)
        if message["message_type"] != "heartbeat":
            return

        current_round = message["data"]["current_round"]
        previous_round = message["data"]["previous_round"]

        if previous_round:
            self.vote_numbers.clear()
            self.print_round(previous_round, True)
        else:
            self.print_round(current_round, False)

if __name__ == "__main__":
    client = DisplayClient()
    asyncio.get_event_loop().run_until_complete(client.main())