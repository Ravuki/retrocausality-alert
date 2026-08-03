import requests
import os
import xml.etree.ElementTree as ET

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")
RSS_FEED_URL = os.getenv("RSS_FEED_URL")

KEYWORD = "retrocausality"

def send_discord(message):
    requests.post(
        DISCORD_WEBHOOK,
        json={"content": message}
    )

def check_feed():
    r = requests.get(RSS_FEED_URL)

    root = ET.fromstring(r.text)

    for item in root.findall(".//item"):
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
            return

check_feed()
