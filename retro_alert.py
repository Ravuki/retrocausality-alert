import json
import os
import re
import subprocess
import requests

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")
MEMORY_FILE = "last_tweet.txt"

KEYWORDS = {
    "retrocausality": [
        r"\bretrocausality\b",
    ],
    "voidwalker": [
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
            timeout=20,
        )

        if response.status_code not in (200, 204):
            print(
                "Discord webhook error:",
                response.status_code,
                response.text,
            )
            return False

        print("Discord alert sent successfully.")
        return True

    except requests.RequestException as e:
        print("Discord webhook error:", e)
        return False


def get_last_id():
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            value = f.read().strip()
            return value if value else "0"
    except FileNotFoundError:
        return "0"


def save_last_id(tweet_id):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        f.write(tweet_id)


def find_keywords(text):
    found = []

    for name, patterns in KEYWORDS.items():
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                found.append(name)
                break

    return found


def get_tweets():
    command = [
        "x",
        "timeline",
        "HYPERMYSTx",
        "--guest",
        "-n",
        "50",
        "-o",
        "jsonl",
    ]

    print("Uruchamiam:", " ".join(command))

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        print("x-cli przekroczył limit czasu.")
        return None

    if result.returncode != 0:
        print("x-cli zakończył się błędem.")
        print("Exit code:", result.returncode)
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
        return None

    if result.stderr:
        print("x-cli info:", result.stderr)

    tweets = []

    for line in result.stdout.splitlines():
        line = line.strip()

        if not line:
            continue

        try:
            tweet = json.loads(line)
            tweets.append(tweet)
        except json.JSONDecodeError:
            print("Nie udało się odczytać JSON:", line)

    return tweets


def check_feed():
    last_id = get_last_id()

    print("Ostatni zapamiętany ID:", last_id)

    tweets = get_tweets()

    if tweets is None:
        print("Nie aktualizuję pamięci — spróbujemy ponownie przy następnym uruchomieniu.")
        return

    if not tweets:
        print("x-cli nie zwrócił żadnych tweetów.")
        return

    print("Pobrano tweetów:", len(tweets))

    new_tweets = []

    for tweet in tweets:
        tweet_id = str(tweet.get("id", "")).strip()

        if not tweet_id:
            continue

        if tweet_id == last_id:
            break

        new_tweets.append(tweet)

    # Najpierw najstarsze, potem najnowsze.
    new_tweets.reverse()

    print("Nowych tweetów:", len(new_tweets))

    newest_id = str(tweets[0].get("id", "")).strip()

    if not newest_id:
        print("Nie znaleziono ID najnowszego tweeta.")
        return

    for tweet in new_tweets:
        tweet_id = str(tweet.get("id", "")).strip()
        text = str(tweet.get("text", "")).strip()
        url = str(tweet.get("url", "")).strip()

        print("----------------------------------------")
        print("Tweet ID:", tweet_id)
        print("Treść:", text)

        found_keywords = find_keywords(text)

        if not found_keywords:
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
                f"{url}"
            )

            send_discord(message)

    save_last_id(newest_id)

    print("Zapisano ostatni ID:", newest_id)


check_feed()
