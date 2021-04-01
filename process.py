import csv
import redis
import progressbar
from collections import defaultdict
try:
    import orjson as json
except ImportError:
    print("orjson not installed")
    import json

r = redis.Redis()

rounds = {}
images = set()
winning_images = defaultdict(lambda: 0)

for raw_event in progressbar.progressbar(r.lrange("reddit:second:socket", 0, -1)):
    event = json.loads(raw_event)
    event_data = event["data"]

    current_round = event_data["current_round"]
    previous_round = event_data["previous_round"]

    # Get all images.
    for image in current_round.get("images", []):
        images.add(image["name"])
    
    # Parse only the first instance of a winning round.
    if previous_round and previous_round["id"] not in rounds:
        rounds[previous_round["id"]] = dict(
            votes=sum(image["votes"] for image in previous_round["images"]),
            images=previous_round["images"],
        )

        # Add winning images.
        winning_votes = sorted(x["votes"] for x in previous_round["images"])
        for image in previous_round["images"]:
            if image["votes"] == winning_votes[1]:
                winning_images[image["name"]] += 1

print(sorted(images))
print(sorted(winning_images.items(), key=lambda i: i[1]))

def rounds_csv():
    fields = [
        "round_id",
        "votes",
        "img0_votes",
        "img1_votes",
        "img2_votes",
        "img0_name",
        "img1_name",
        "img2_name",
    ]
    with open("output/rounds.csv", "w+") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()

        for round_id, meta in rounds.items():
            writer.writerow({
                "round_id": round_id,
                "votes": meta["votes"],
                "img0_votes": meta["images"][0]["votes"],
                "img1_votes": meta["images"][1]["votes"],
                "img2_votes": meta["images"][2]["votes"],
                "img0_name": meta["images"][0]["name"],
                "img1_name": meta["images"][1]["name"],
                "img2_name": meta["images"][2]["name"],
            })

# Run all processing commands.
rounds_csv()