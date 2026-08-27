import json
import os
import re
import subprocess
import sys
import requests

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")

MEMORY_FILE = "last_tweet.txt"

# Szukamy wszystkich tych nazw niezależnie od wielkości liter.
KEYWORDS = {
    "retrocausality": [
        r"\bretrocausality\b",
    ],
    "voidwalker": [
        r"\bvoid\s*walker\b",
        r"\bvoidwalker\b",
    ],
    "void shadow": [
        r"\bvoid\s*shadow\b",
        r"\bvoidshadow\b",
    ],
}

MAX_TWEETS = 100


def send_discord(message):
    if not DISCORD_WEBHOOK:
        raise RuntimeError("Brak secreta DISCORD_WEBHOOK!")

    response = requests.post(
        DISCORD_WEBHOOK,
        json={"content": message},
        timeout=20,
    )

    response.raise_for_status()

    print("Discord: powiadomienie wysłane.")


def get_last_id():
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            value = f.read().strip()

        if value.isdigit():
            return int(value)

    except FileNotFoundError:
        pass

    except Exception as e:
        raise RuntimeError(
            f"Nie można odczytać {MEMORY_FILE}: {e}"
        )

    return 0


def save_last_id(tweet_id):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        f.write(str(tweet_id))


def get_tweets():
    command = [
        "x",
        "timeline",
        "HYPERMYSTx",
        "--guest",
        "--no-cache",
        "-n",
        str(MAX_TWEETS),
        "-o",
        "jsonl",
    ]

    print("Uruchamiam:", " ".join(command))

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("x-cli przekroczył limit czasu 60 sekund.")

    if result.returncode != 0:
        print("STDOUT:")
        print(result.stdout)

        print("STDERR:")
        print(result.stderr)

        raise RuntimeError(
            f"x-cli zakończył się kodem {result.returncode}."
        )

    tweets = []

    for line in result.stdout.splitlines():
        line = line.strip()

        if not line:
            continue

        try:
            tweet = json.loads(line)
        except json.JSONDecodeError:
            continue

        tweet_id = tweet.get("id")

        if tweet_id is None:
            continue

        tweet_id = str(tweet_id)

        if not tweet_id.isdigit():
            continue

        text = tweet.get("text") or ""

        tweets.append(
            {
                "id": int(tweet_id),
                "text": text,
            }
        )

    if not tweets:
        raise RuntimeError(
            "x-cli zakończył się poprawnie, ale nie zwrócił żadnych tweetów."
        )

    # Usuwamy ewentualne duplikaty.
    unique = {}

    for tweet in tweets:
        unique[tweet["id"]] = tweet

    tweets = list(unique.values())

    # WAŻNE:
    # Nie ufamy kolejności zwróconej przez x-cli.
    # Najnowszy tweet ma największe ID.
    tweets.sort(
        key=lambda tweet: tweet["id"],
        reverse=True,
    )

    print("Pobrano poprawnych tweetów:", len(tweets))

    print("NAJNOWSZY POBRANY TWEET:")
    newest = tweets[0]

    print("ID:", newest["id"])
    print("Treść:", newest["text"])
    print(
        "URL:",
        f"https://x.com/HYPERMYSTx/status/{newest['id']}",
    )

    return tweets


def find_matches(text):
    matches = []

    text_lower = text.lower()

    for keyword, patterns in KEYWORDS.items():
        for pattern in patterns:
            if re.search(pattern, text_lower):
                matches.append(keyword)
                break

    return matches


def check_feed():
    if not DISCORD_WEBHOOK:
        raise RuntimeError("Brak secreta DISCORD_WEBHOOK!")

    last_id = get_last_id()

    print("Ostatni zapamiętany ID:", last_id)

    tweets = get_tweets()

    # Wszystkie tweety nowsze od zapamiętanego ID.
    new_tweets = [
        tweet
        for tweet in tweets
        if tweet["id"] > last_id
    ]

    # Sortujemy od najstarszego do najnowszego,
    # żeby alerty przyszły w prawidłowej kolejności.
    new_tweets.sort(
        key=lambda tweet: tweet["id"]
    )

    print("Nowych tweetów:", len(new_tweets))

    if new_tweets:
        print("=" * 60)

        for tweet in new_tweets:
            tweet_id = tweet["id"]
            text = tweet["text"]

            print("Nowy tweet:", tweet_id)
            print("Treść:", text)

            matches = find_matches(text)

            if matches:
                print("!!! MATCH !!!")
                print("Dopasowane:", ", ".join(matches))

                labels = " / ".join(
                    name.upper()
                    for name in matches
                )

                message = (
                    f"🚨 HYPERMYST ALERT — {labels} 🚨\n\n"
                    f"{text}\n\n"
                    f"https://x.com/HYPERMYSTx/status/{tweet_id}"
                )

                send_discord(message)

            else:
                print("Brak interesującego słowa.")

            print("-" * 60)

    # Najnowszy tweet, który rzeczywiście pobraliśmy.
    newest_id = tweets[0]["id"]

    # Nie cofamy pamięci.
    if newest_id > last_id:
        save_last_id(newest_id)

        print(
            "Zapisano ostatni ID:",
            newest_id,
        )
    else:
        print(
            "Nie zmieniono pamięci. "
            "Najnowszy ID nie jest nowszy od zapisanego."
        )


if __name__ == "__main__":
    try:
        check_feed()

    except Exception as e:
        print()
        print("!!! KRYTYCZNY BŁĄD !!!")
        print(str(e))
        sys.exit(1)
