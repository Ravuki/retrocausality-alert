import requests
import os
import xml.etree.ElementTree as ET

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")
RSS_FEED_URL = os.getenv("RSS_FEED_URL")

KEYWORDS = {
    "retrocausality": "🚨 RETROCAUSALITY ALERT 🚨",
    "voidwalker": "🟣 VOIDWALKER ALERT 🟣",
    "void shadow": "🟣 VOID SHADOW FRAME ALERT 🟣",
}

MEMORY_FILE = "last_tweet.txt"


def send_discord(message):
    requests.post(
        DISCORD_WEBHOOK,
        json={"content": message},
        timeout=20
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

    try:
        r = requests.get(
            RSS_FEED_URL,
            timeout=20,
            headers={
                "User-Agent": "Mozilla/5.0 (Retrocausality Alert)"
            }
        )

        print("Feed URL:", RSS_FEED_URL)
        print("HTTP status:", r.status_code)
        print("Content-Type:", r.headers.get("Content-Type"))
        print("Final URL:", r.url)
        print("Response preview:", repr(r.text[:500]))

        r.raise_for_status()

    except requests.RequestException as e:
        print("Błąd podczas pobierania RSS:", e)
        return

    try:
        root = ET.fromstring(r.text)
    except ET.ParseError as e:
        print("Feed nie jest poprawnym XML-em!")
        print("Błąd XML:", e)
        print("Odpowiedź serwera:", repr(r.text[:1000]))
        return

    items = root.findall(".//item")

    if not items:
        print("Nie znaleziono żadnych <item> w feedzie.")
        return

    newest_id = items[0].find("guid")

    if newest_id is None or not newest_id.text:
        print("Najnowszy wpis nie ma GUID.")
        return

    newest_id = newest_id.text

    # Sprawdź tylko nowe wpisy
    for item in items:
        guid = item.find("guid")

        if guid is None or not guid.text:
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

        text_lower = text.lower()

        # Sprawdź wszystkie słowa kluczowe
        for keyword, alert_name in KEYWORDS.items():

            if keyword in text_lower:
                send_discord(
                    f"{alert_name}\n\n"
                    + f"🔎 Wykryto: `{keyword}`\n\n"
                    + text
                    + "\n\n"
                    + (link.text if link is not None else "")
                )

    save_last_id(newest_id)


check_feed()
