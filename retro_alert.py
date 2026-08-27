import os
import re
import html
import requests
from bs4 import BeautifulSoup


# ============================================================
# KONFIGURACJA
# ============================================================

PROFILE_URL = "https://twstalker.com/HYPERMYSTx"
USERNAME = "HYPERMYSTx"
MEMORY_FILE = "last_tweet.txt"

DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK")

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


# ============================================================
# PAMIĘĆ
# ============================================================

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


# ============================================================
# POBIERANIE TWEETÓW
# ============================================================

def fetch_tweets():
    print(f"Pobieram: {PROFILE_URL}")

    response = requests.get(
        PROFILE_URL,
        timeout=30,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/139.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        },
    )

    print("HTTP status:", response.status_code)
    print("Final URL:", response.url)

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    tweets = []
    seen_ids = set()

    # Szukamy wszystkich linków prowadzących do konkretnych tweetów.
    for link in soup.find_all("a", href=True):
        href = html.unescape(link["href"])

        match = re.search(
            rf"/{re.escape(USERNAME)}/status/(\d+)",
            href,
            re.IGNORECASE,
        )

        if not match:
            continue

        tweet_id = int(match.group(1))

        if tweet_id in seen_ids:
            continue

        seen_ids.add(tweet_id)

        # Próbujemy znaleźć kontener zawierający tekst danego tweeta.
        container = link

        for _ in range(8):
            if container.parent is None:
                break

            container = container.parent
            text = container.get_text(" ", strip=True)

            if USERNAME in text and len(text) > 30:
                break

        full_text = container.get_text(" ", strip=True)

        # Usuwamy typowe śmieci z interfejsu TwStalker.
        full_text = re.sub(
            r"\bView Details\b",
            "",
            full_text,
            flags=re.IGNORECASE,
        )

        full_text = re.sub(
            r"\bPrevious\b|\bNext\b|\bkeyboard_arrow_left\b|\bkeyboard_arrow_right\b",
            "",
            full_text,
            flags=re.IGNORECASE,
        )

        full_text = re.sub(r"\s+", " ", full_text).strip()

        # Jeżeli kontener jest zbyt ogólny, próbujemy wyciągnąć tekst
        # z elementów zawierających bezpośrednio treść.
        if USERNAME in full_text:
            marker = f"{USERNAME}"
            pos = full_text.find(marker)

            if pos >= 0:
                candidate = full_text[pos + len(marker):].strip()

                # Usuń ewentualny nagłówek / liczbę followersów itp.
                candidate = re.sub(
                    r"^\s*\d+\s*Followers.*?\d+\s*Following\s*",
                    "",
                    candidate,
                    flags=re.IGNORECASE,
                )

                if len(candidate) > 10:
                    full_text = candidate

        # Ostateczne czyszczenie.
        full_text = html.unescape(full_text)

        tweets.append(
            {
                "id": tweet_id,
                "text": full_text,
                "url": f"https://x.com/{USERNAME}/status/{tweet_id}",
            }
        )

    if not tweets:
        raise RuntimeError(
            "Nie znaleziono żadnych tweetów HYPERMYST na TwStalker."
        )

    # Najwyższe ID traktujemy jako najnowszy znaleziony tweet.
    tweets.sort(key=lambda x: x["id"])

    print(f"Znalezionych tweetów: {len(tweets)}")
    print("=" * 50)

    newest = tweets[-1]

    print("NAJNOWSZY ZNALEZIONY TWEET:")
    print("ID:", newest["id"])
    print("Treść:", newest["text"])
    print("URL:", newest["url"])
    print("=" * 50)

    return tweets


# ============================================================
# KEYWORDY
# ============================================================

def find_matches(text):
    matches = []

    for name, patterns in KEYWORDS.items():
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                matches.append(name)
                break

    return matches


# ============================================================
# DISCORD
# ============================================================

def send_discord(tweet, matches):
    if not DISCORD_WEBHOOK:
        raise RuntimeError(
            "Brak DISCORD_WEBHOOK w GitHub Secrets."
        )

    content = (
        "🚨 **RETROCAUSALITY ALERT** 🚨\n\n"
        f"**Dopasowanie:** {', '.join(matches)}\n"
        f"**HYPERMYST:** {tweet['text']}\n\n"
        f"{tweet['url']}"
    )

    response = requests.post(
        DISCORD_WEBHOOK,
        json={"content": content},
        timeout=30,
    )

    print("Discord HTTP status:", response.status_code)

    response.raise_for_status()

    print("Discord: powiadomienie wysłane.")


# ============================================================
# GŁÓWNY PROGRAM
# ============================================================

def main():
    last_id = load_last_id()

    print("Ostatni zapamiętany ID:", last_id)

    tweets = fetch_tweets()

    # Tylko tweety faktycznie nowsze od zapamiętanego.
    new_tweets = [
        tweet
        for tweet in tweets
        if tweet["id"] > last_id
    ]

    print("Nowych tweetów:", len(new_tweets))

    # Przetwarzamy chronologicznie.
    new_tweets.sort(key=lambda x: x["id"])

    newest_id = last_id

    for tweet in new_tweets:
        print("-" * 40)
        print("Tweet ID:", tweet["id"])
        print("Treść:", tweet["text"])
        print("URL:", tweet["url"])

        matches = find_matches(tweet["text"])

        if matches:
            print("!!! ZNALEZIONO !!!")
            print("Dopasowania:", ", ".join(matches))

            send_discord(tweet, matches)
        else:
            print("Brak dopasowania.")

        newest_id = max(newest_id, tweet["id"])

    # WAŻNE:
    # Pamięć aktualizujemy dopiero po pomyślnym przetworzeniu
    # wszystkich nowych tweetów.
    if newest_id != last_id:
        save_last_id(newest_id)

    print("Zapisano ostatni ID:", newest_id)


if __name__ == "__main__":
    main()
