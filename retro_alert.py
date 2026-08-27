import requests
import os
import xml.etree.ElementTree as ET
import re

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")
RSS_FEED_URL = os.getenv("RSS_FEED_URL")

MEMORY_FILE = "last_tweet.txt"

KEYWORDS = {
    "retrocausality": [
        r"\bretrocausality\b",
    ],

    "voidwalker": [
        r"\bvoidwalker\b",
        r"\bvoid\s*walker\b",
    ],

    "void shadow": [
        r"\bvoid\s*shadow\b",
        r"\bvoidshadow\b",
    ],
}


def send_discord(message):
    try:
        response = requests.post(
            DISCORD_WEBHOOK,
            json={"content": message},
            timeout=20
        )

        if response.status_code not in (200, 204):
            print(
                "Discord webhook error:",
                response.status_code,
                response.text
            )
            return False

        print("Discord alert sent successfully.")
        return True

    except requests.RequestException as e:
        print("Błąd Discord webhook:", e)
        return False


def get_last_id():
    try:
        with open(MEMORY_FILE, "r") as f:
            value = f.read().strip()

            if value:
                return value

    except FileNotFoundError:
        pass

    return "0"


def save_last_id(tweet_id):
    with open(MEMORY_FILE, "w") as f:
        f.write(tweet_id)


def find_keywords(text):
    """
    Zwraca listę wykrytych kategorii.
    Wielkość liter nie ma znaczenia.
    """

    found = []

    for name, patterns in KEYWORDS.items():
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                found.append(name)
                break

    return found


def check_feed():
    last_id = get_last_id()

    print("Ostatni zapamiętany ID:", last_id)

    try:
        r = requests.get(
            RSS_FEED_URL,
            timeout=20,
            headers={
                "User-Agent": "Mozilla/5.0 (HyperMyst Alert Bot)"
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

        # NIE aktualizujemy last_tweet.txt.
        # Przy kolejnym uruchomieniu spróbujemy ponownie.
        return

    try:
        root = ET.fromstring(r.text)

    except ET.ParseError as e:
        print("Feed nie jest poprawnym XML-em!")
        print("Błąd XML:", e)
        print("Odpowiedź serwera:", repr(r.text[:1000]))

        # NIE aktualizujemy last_tweet.txt.
        return

    items = root.findall(".//item")

    if not items:
        print("Nie znaleziono żadnych <item> w feedzie.")
        return

    newest_id_element = items[0].find("guid")

    if newest_id_element is None or not newest_id_element.text:
        print("Najnowszy wpis nie ma GUID.")
        return

    newest_id = newest_id_element.text.strip()

    print("Najnowszy ID:", newest_id)

    new_items = []

    # Zbieramy wszystkie wpisy nowsze od ostatnio zapamiętanego.
    for item in items:
        guid = item.find("guid")

        if guid is None or not guid.text:
            continue

        guid_text = guid.text.strip()

        if guid_text == last_id:
            break

        new_items.append(item)

    print("Nowych wpisów:", len(new_items))

    # Przetwarzamy od najstarszego do najnowszego.
    new_items.reverse()

    for item in new_items:

        guid = item.find("guid")
        title = item.find("title")
        description = item.find("description")
        link = item.find("link")

        tweet_id = guid.text.strip() if guid is not None and guid.text else ""

        title_text = title.text.strip() if title is not None and title.text else ""
        description_text = (
            description.text.strip()
            if description is not None and description.text
            else ""
        )

        link_text = link.text.strip() if link is not None and link.text else ""

        text = f"{title_text} {description_text}".strip()

        print("----------------------------------------")
        print("Tweet ID:", tweet_id)
        print("Treść:", text)

        found_keywords = find_keywords(text)

        if not found_keywords:
            print("Brak interesujących słów.")
            continue

        print("WYKRYTO:", ", ".join(found_keywords))

        for keyword in found_keywords:

            if keyword == "retrocausality":
                alert_title = "🚨 RETROCAUSALITY ALERT 🚨"

            elif keyword == "voidwalker":
                alert_title = "🟣 VOIDWALKER ALERT 🟣"

            elif keyword == "void shadow":
                alert_title = "🟣 VOID SHADOW FRAME ALERT 🟣"

            else:
                alert_title = "🚨 HYPERMYST ALERT 🚨"

            message = (
                f"{alert_title}\n\n"
                f"🔎 Wykryto: `{keyword}`\n\n"
                f"{text}\n\n"
                f"{link_text}"
            )

            send_discord(message)

    # Aktualizujemy pamięć dopiero po poprawnym przetworzeniu feedu.
    save_last_id(newest_id)

    print("Zapisano ostatni ID:", newest_id)


check_feed()
