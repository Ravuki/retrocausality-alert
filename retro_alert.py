import os
import re
import requests
from datetime import datetime, timezone, timedelta


USERNAME = "HYPERMYSTx"
MEMORY_FILE = "last_tweet.txt"

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

    formats = [
        "%a %b %d %H:%M:%S %z %Y",
        "%Y-%m-%dT%H:%M:%S%z",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            pass

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

    if data.get("code") != 200:
        raise RuntimeError(
            f"FxTwitter API zwróciło code={data.get('code')}"
        )

    # WAŻNE:
    # FxTwitter API v2 zwraca tweety w polu "results".
    results = data.get("results")

    if not isinstance(results, list):
        raise RuntimeError(
            "FxTwitter API nie zwróciło listy 'results'."
        )

    tweets = []

    for tweet in results:
        if tweet.get("type") != "status":
            continue

        tweet_id = tweet.get("id")
        text = tweet.get("text") or ""
        created_at = tweet.get("created_at")
        url = tweet.get("url")

        if not tweet_id:
            continue

        try:
            tweet_id = int(tweet_id)
        except (ValueError, TypeError):
            continue

        if not url:
            url = f"https://x.com/{USERNAME}/status/{tweet_id}"

        tweets.append(
            {
                "id": tweet_id,
                "text": text,
                "created_at": created_at,
                "url": url,
            }
        )

    if not tweets:
        raise RuntimeError(
            "API odpowiedziało poprawnie, ale nie znaleziono tweetów."
        )

    # Najnowszy tweet pierwszy.
    tweets.sort(key=lambda x: x["id"], reverse=True)

    newest = tweets[0]

    print("=" * 60)
    print("NAJNOWSZY POBRANY TWEET:")
    print("ID:", newest["id"])
    print("Data:", newest["created_at"])
    print("Treść:", newest["text"])
    print("URL:", newest["url"])
    print("=" * 60)

    # ---------------------------------------------------------
    # SPRAWDZENIE ŚWIEŻOŚCI ŹRÓDŁA
    # ---------------------------------------------------------

    newest_date = parse_created_at(newest["created_at"])

    if newest_date is None:
        raise RuntimeError(
            "Nie udało się odczytać daty najnowszego tweeta. "
            "Nie aktualizuję pamięci."
        )

    now = datetime.now(timezone.utc)

    age = now - newest_date

    age_hours = age.total_seconds() / 3600

    print(f"Wiek najnowszego tweeta: {age_hours:.2f} godzin")

    if age > timedelta(hours=MAX_FEED_AGE_HOURS):
        raise RuntimeError(
            "ŹRÓDŁO JEST NIEAKTUALNE! "
            f"Najnowszy tweet ma {age_hours:.1f} godzin. "
            f"Limit: {MAX_FEED_AGE_HOURS} godzin. "
            "Pamięć NIE zostanie zmieniona."
        )

    print("ŚWIEŻOŚĆ FEEDU: OK")

    return tweets


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
        f"**HYPERMYSTx:**\n"
        f"{tweet['text']}\n\n"
        f"{tweet['url']}"
    )

    response = requests.post(
        DISCORD_WEBHOOK,
        json={
            "content": message
        },
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

    # Od najstarszego do najnowszego.
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
