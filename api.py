import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "u/nepeat second-parser"
}

def get_ws_uri():
    embed_data = requests.get("https://second-api.reddit.com/embed?platform=desktop", headers=HEADERS).text
    embed_soup = BeautifulSoup(embed_data, 'html.parser')
    embed = embed_soup.find("afd2021-user-data")

    return embed["websocketurl"]
