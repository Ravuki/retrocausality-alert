import json
import os
import re
import subprocess
import sys
import requests

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")

MEMORY_FILE = "last_tweet.txt"
MAX_TWEETS = 100

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


def get_last_id():
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            value = f.read().strip()

        if value.isdigit():
            return int(value)

    except FileNotFoundError:
        return 0

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

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=60,
    )

    if result.returncode != 0:
        print("STDOUT:")
        print(result.stdout)

        print("STDERR:")
        print(result.stderr)

        raise RuntimeError(
            f"x-cli zakończył się kodem {result.returncode}"
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

        tweets.append({
            "id": int(tweet_id),
            "text": tweet.get("text") or "",
        })

    if not tweets:
        raise RuntimeError(
            "x-cli nie zwrócił żadnych poprawnych tweetów."
        )

    # Usuwamy duplikaty.
    unique = {}

    for tweet in tweets:
        unique[tweet["id"]] = tweet

    tweets = list(unique.values())

    # Największe ID = najnowszy tweet.
    tweets.sort(
        key=lambda tweet: tweet["id"],
        reverse=True,
    )

    print("Pobrano poprawnych tweetów:", len(tweets))

    newest = tweets[0]

    print("NAJNOWSZY POBRANY TWEET:")
    print("ID:", newest["id"])
    print("Treść:", newest["text"])
    print(
        "URL:",
        f"https://x.com/HYPERMYSTx/status/{newest['id']}",
    )

    return tweets


def find_matches(text):
    matches = []

    for keyword, patterns in KEYWORDS.items():
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                matches.append(keyword)
                break

    return matches


def send_discord(tweet, matches):
    if not DISCORD_WEBHOOK:
        raise RuntimeError(
            "Brak secreta DISCORD_WEBHOOK!"
        )

    tweet_id = tweet["id"]
    text = tweet["text"]

    labels = " / ".join(
        name.upper()
        for name in matches
    )

    message = (
        f"🚨 HYPERMYST ALERT — {labels} 🚨\n\n"
        f"{text}\n\n"
        f"https://x.com/HYPERMYSTx/status/{tweet_id}"
    )

    response = requests.post(
        DISCORD_WEBHOOK,
        json={"content": message},
        timeout=20,
    )

    response.raise_for_status()

    print("Discord: powiadomienie wysłane.")


def check():
    if not DISCORD_WEBHOOK:
        raise RuntimeError(
            "Brak secreta DISCORD_WEBHOOK!"
        )

    last_id = get_last_id()

    print("Ostatni zapamiętany ID:", last_id)

    tweets = get_tweets()

    new_tweets = [
        tweet
        for tweet in tweets
        if tweet["id"] > last_id
    ]

    # Od najstarszego nowego do najnowszego.
    new_tweets.sort(
        key=lambda tweet: tweet["id"]
    )

    print("Nowych tweetów:", len(new_tweets))

    for tweet in new_tweets:
        tweet_id = tweet["id"]
        text = tweet["text"]

        print("----------------------------------------")
        print("Tweet ID:", tweet_id)
        print("Treść:", text)

        matches = find_matches(text)

        if matches:
            print("!!! ZNALEZIONO !!!")
            print(
                "Dopasowania:",
                ", ".join(matches),
            )

            send_discord(tweet, matches)

        else:
            print("Brak dopasowania.")

    # Zapamiętujemy najnowszy pobrany tweet.
    newest_id = tweets[0]["id"]

    if newest_id > last_id:
        save_last_id(newest_id)

        print(
            "Zapisano ostatni ID:",
            newest_id,
        )
    else:
        print(
            "Zapisano ostatni ID:",
            last_id,
        )


if __name__ == "__main__":
    try:
        check()

    except Exception as e:
        print()
        print("!!! KRYTYCZNY BŁĄD !!!")
        print(str(e))
        sys.exit(1)
