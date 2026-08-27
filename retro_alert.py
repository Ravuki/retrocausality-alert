import os
import re
import requests
from datetime import datetime, timezone, timedelta


USERNAME = "HYPERMYSTx"
MEMORY_FILE = "last_tweet.txt"

# Publiczny FxTwitter API v2
API_URL = f"https://api.fxtwitter.com/2/profile/{USERNAME}/statuses"

DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK")

MAX_FEED_AGE_HOURS = 24

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


def load_last_id():
    if not os.path.exists(MEMORY_FILE):
        return 0

    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return int(f.read().strip())
    except (ValueError, OSError):
        return 0


def save_last_id(tweet_id):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        f.write(str(tweet_id))


def parse_created_at(value):
    if not value:
        return None

    try:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
    except ValueError:
        return None


def fetch_tweets():
    print(f"Pobieram: {API_URL}")

    response = requests.get(
        API_URL,
        timeout=30,
        headers={
            "User-Agent": "RetrocausalityChecker/1.0",
            "Accept": "application/json",
        },
    )

    print("HTTP status:", response.status_code)

    response.raise_for_status()

    data = response.json()

    print("Odpowiedź API otrzymana.")

    if data.get("code") not in (None, 200):
        raise RuntimeError(
            f"FxTwitter API zwróciło code={data.get('code')}"
        )

    # FxTwitter API v2 zwraca listy w polu "tweets"/"statuses"
    tweets = data.get("tweets")

    if tweets is None:
        tweets = data.get("statuses")

    if not isinstance(tweets, list):
        raise RuntimeError(
            "Nie znaleziono listy tweetów w odpowiedzi FxTwitter."
        )

    parsed = []

    for tweet in tweets:
        tweet_id = tweet.get("id")

        if not tweet_id:
            continue

        try:
            tweet_id = int(tweet_id)
        except (ValueError, TypeError):
            continue

        text = tweet.get("text") or ""

        created_at = tweet.get("created_at")

        parsed.append(
            {
                "id": tweet_id,
                "text": text,
                "created_at": created_at,
                "url": tweet.get(
                    "url",
                    f"https://x.com/{USERNAME}/status/{tweet_id}",
                ),
            }
        )

    if not parsed:
        raise RuntimeError(
            "API odpowiedziało poprawnie, ale nie znaleziono tweetów."
        )

    # ID tweetów X jest chronologiczne.
    parsed.sort(key=lambda x: x["id"], reverse=True)

    newest = parsed[0]

    print(f"Pobrano tweetów: {len(parsed)}")
    print("=" * 60)
    print("NAJNOWSZY POBRANY TWEET:")
    print("ID:", newest["id"])
    print("Data:", newest["created_at"])
    print("Treść:", newest["text"])
    print("URL:", newest["url"])
    print("=" * 60)

    # --------------------------------------------------------
    # KRYTYCZNE ZABEZPIECZENIE PRZED STARYM FEEDem
    # --------------------------------------------------------

    newest_date = parse_created_at(newest["created_at"])

    if newest_date is None:
        raise RuntimeError(
            "Nie udało się odczytać daty najnowszego tweeta. "
            "Nie będę ryzykował aktualizacji pamięci."
        )

    now = datetime.now(timezone.utc)

    age = now - newest_date

    print(
        f"Wiek najnowszego tweeta: "
        f"{age.total_seconds() / 3600:.2f} godzin"
    )

    if age > timedelta(hours=MAX_FEED_AGE_HOURS):
        raise RuntimeError(
            "ŹRÓDŁO JEST NIEAKTUALNE! "
            f"Najnowszy tweet ma {age.total_seconds() / 3600:.1f} godzin. "
            f"Limit: {MAX_FEED_AGE_HOURS} godzin. "
            "Pamięć NIE zostanie zmieniona."
        )

    print("ŚWIEŻOŚĆ FEEDU: OK")

    return parsed


def find_matches(text):
    matches = []

    for name, patterns in KEYWORDS.items():
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                matches.append(name)
                break

    return matches


def send_discord(tweet, matches):
    if not DISCORD_WEBHOOK:
        raise RuntimeError(
            "Brak DISCORD_WEBHOOK w GitHub Secrets."
        )

    message = (
        "🚨 **RETROCAUSALITY ALERT** 🚨\n\n"
        f"**Dopasowanie:** {', '.join(matches)}\n\n"
        f"**HYPERMYSTx:**\n{tweet['text']}\n\n"
        f"{tweet['url']}"
    )

    response = requests.post(
        DISCORD_WEBHOOK,
        json={"content": message},
        timeout=30,
    )

    print("Discord HTTP status:", response.status_code)

    response.raise_for_status()

    print("Discord: POWIADOMIENIE WYSŁANE.")


def main():
    last_id = load_last_id()

    print("Ostatni zapamiętany ID:", last_id)

    tweets = fetch_tweets()

    new_tweets = [
        tweet
        for tweet in tweets
        if tweet["id"] > last_id
    ]

    new_tweets.sort(key=lambda x: x["id"])

    print("Nowych tweetów:", len(new_tweets))

    newest_id = last_id

    for tweet in new_tweets:
        print("-" * 60)
        print("Tweet ID:", tweet["id"])
        print("Data:", tweet["created_at"])
        print("Treść:", tweet["text"])
        print("URL:", tweet["url"])

        matches = find_matches(tweet["text"])

        if matches:
            print("!!! ZNALEZIONO DOPASOWANIE !!!")
            print("Dopasowania:", ", ".join(matches))

            send_discord(tweet, matches)
        else:
            print("Brak dopasowania.")

        newest_id = max(newest_id, tweet["id"])

    if newest_id != last_id:
        save_last_id(newest_id)

    print("Zapisano ostatni ID:", newest_id)


if __name__ == "__main__":
    main()
