import requests
import os
import xml.etree.ElementTree as ET

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")
RSS_FEED_URL = os.getenv("RSS_FEED_URL")

KEYWORD = "retrocausality"
MEMORY_FILE = "last_tweet.txt"

def send_discord(message):
    requests.post(
        DISCORD_WEBHOOK,
        json={"content": message}
    )

def get_last_id():
    try:
        with open(MEMORY_FILE, "r") as f:
            return f.read().strip()
    except:
        return "0"

def save_last_id(tweet_id):
    with open(MEMORY_FILE, "w") as f:
        f.write(tweet_id)

def check_feed():
    last_id = get_last_id()

    r = requests.get(RSS_FEED_URL)
    root = ET.fromstring(r.text)

    items = root.findall(".//item")

    if not items:
        return

    newest_id = items[0].find("guid")

    if newest_id is None:
        return

    newest_id = newest_id.text

    # sprawdź tylko nowe wpisy
    for item in items:
        guid = item.find("guid")

        if guid is None:
            continue

        if guid.text == last_id:
            break

        title = item.find("title")
        description = item.find("description")
        link = item.find("link")

        text = ""

        if title is not None:
            text += title.text or ""

        if description is not None:
            text += " " + (description.text or "")

        if KEYWORD in text.lower():
            send_discord(
                "🚨 RETROCAUSALITY ALERT 🚨\n\n"
                + text
                + "\n\n"
                + (link.text if link is not None else "")
            )

    save_last_id(newest_id)

check_feed()
