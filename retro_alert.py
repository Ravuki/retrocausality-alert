import requests
import os

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")
X_BEARER_TOKEN = os.getenv("X_BEARER_TOKEN")

USERNAME = "HYPERMYSTx"
KEYWORD = "retrocausality"

def send_discord(message):
    requests.post(
        DISCORD_WEBHOOK,
        json={"content": message}
    )

def get_user_id():
    url = f"https://api.x.com/2/users/by/username/{USERNAME}"
    headers = {
        "Authorization": f"Bearer {X_BEARER_TOKEN}"
    }

    r = requests.get(url, headers=headers)

    print("X response:", r.text)

    data = r.json()

    if "data" not in data:
        raise Exception("X API error: " + r.text)

    return data["data"]["id"]
def check_tweets():
    user_id = get_user_id()

    url = f"https://api.x.com/2/users/{user_id}/tweets"

    headers = {
        "Authorization": f"Bearer {X_BEARER_TOKEN}"
    }

    params = {
        "max_results": 5,
        "tweet.fields": "created_at"
    }

    r = requests.get(url, headers=headers, params=params)

    tweets = r.json().get("data", [])

    for tweet in tweets:
        text = tweet["text"].lower()

        if KEYWORD in text:
            send_discord(
                "🚨 RETROCAUSALITY ALERT 🚨\n\n" + tweet["text"]
            )
            break

check_tweets()
