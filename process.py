import csv
import redis
import progressbar
from collections import defaultdict
from enum import Enum
try:
    import orjson
    import orjson as json
except ImportError:
    print("orjson not installed")
    orjson = None
    import json

r = redis.Redis()

rounds = defaultdict(lambda: {
    "images": {},
    "image_phase": {
        SecondPhase.FIRST_REVEAL: {},
        SecondPhase.SECOND_REVEAL: {},
        SecondPhase.RESULTS: {}
    },
    "total_votes": 0
})
images = set()
winning_images = defaultdict(lambda: 0)

class SecondPhase(Enum):
    FIRST_REVEAL = "first"
    SECOND_REVEAL = "second"
    RESULTS = "results"

def get_phase(remaining_time: float):
    if remaining_time > 20:
        return SecondPhase.FIRST_REVEAL
    elif remaining_time == -1:
        return SecondPhase.RESULTS

    return SecondPhase.SECOND_REVEAL

def process_event(event: dict):
    event_data = event["data"]

    current_round = event_data["current_round"]
    previous_round = event_data["previous_round"]

    # Get info for the current round, if possible.
    seconds_until_vote_reveal = current_round.get("secondsUntilVoteReveal", 0.0)
    seconds_left = current_round.get("secondsLeft", -1)
    current_phase = get_phase(seconds_left)

    # Get all images.
    for image in current_round.get("images", []):
        images.add(image["name"])

    # Do things for the current round.
    if current_round["status"] == "in_progress":
        round_id = current_round["id"]
        rounds[round_id]["total_votes"] = max(current_round["totalVotes"], rounds[round_id]["total_votes"])

        # Add data for the current image to the images array.
        current_images = current_round.get("images", [])
        if current_images[0]["votes"] > 0:
            if (
                not rounds[round_id]["image_phase"][current_phase] or
                current_images[0]["votes"] > rounds[round_id]["image_phase"][current_phase][0]["votes"]
            ):
            rounds[round_id]["image_phase"][current_phase] = current_images
    
    # Parse only the first instance of a winning round.
    if previous_round:
        round_id = previous_round["id"]
        if rounds[round_id]["image_phase"][SecondPhase.RESULTS]:
            return
        
        rounds[round_id]["total_votes"] = sum(image["votes"] for image in previous_round["images"])
        rounds[round_id]["images"] = previous_round["images"]
        rounds[round_id]["image_phase"][SecondPhase.RESULTS] = previous_round["images"]

        # Add winning images.
        winning_votes = sorted(x["votes"] for x in previous_round["images"])
        if winning_votes[0] == winning_votes[1]:
            print("bollocks")

        for image in previous_round["images"]:
            if image["votes"] == winning_votes[1]:
                winning_images[image["name"]] += 1

for key in r.keys("reddit:second:socket*"):
    print(key)
    for raw_event in progressbar.progressbar(r.lrange(key, 0, -1)):
    event = json.loads(raw_event)
    process_event(event)

print(sorted(images))
print(sorted(winning_images.items(), key=lambda i: i[1]))

def rounds_csv():
    fields = [
        "round_id",
        "phase",
        "votes",
        "img0_votes",
        "img1_votes",
        "img2_votes",
        "img0_name",
        "img1_name",
        "img2_name",
    ]

    phaseless_fields = fields.copy()
    phaseless_fields.remove("phase")

    # Create CSVs per round.
    for phase in SecondPhase:
        with open(f"output/round_{phase.name}.csv", "w+") as f:
            writer = csv.DictWriter(f, fieldnames=phaseless_fields)
            writer.writeheader()

            for round_id, meta in rounds.items():
                images = meta["image_phase"][phase]
                if not images:
                    continue
                writer.writerow({
                    "round_id": round_id,
                    "votes": meta["total_votes"],
                    "img0_votes": images[0]["votes"],
                    "img1_votes": images[1]["votes"],
                    "img2_votes": images[2]["votes"],
                    "img0_name": images[0]["name"],
                    "img1_name": images[1]["name"],
                    "img2_name": images[2]["name"],
                })


    # Create CSVs for all rounds..
    with open("output/all_rounds.csv", "w+") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()

        for round_id, meta in rounds.items():
            for phase_name, images in meta["image_phase"].items():
                if not images:
                    continue
                writer.writerow({
                    "round_id": round_id,
                    "phase": phase_name.name,
                    "votes": meta["total_votes"],
                    "img0_votes": images[0]["votes"],
                    "img1_votes": images[1]["votes"],
                    "img2_votes": images[2]["votes"],
                    "img0_name": images[0]["name"],
                    "img1_name": images[1]["name"],
                    "img2_name": images[2]["name"],
                })

# Run all processing commands.
rounds_csv()

for round_id, meta in rounds.items():
    for phase in SecondPhase:
        phase_data = meta["image_phase"][phase]
        if not phase_data:
            print(round_id, "missing phase", phase)
            # print(round_id, json.dumps(meta, option=orjson.OPT_NON_STR_KEYS).decode("utf8"))