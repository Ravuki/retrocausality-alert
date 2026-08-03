import requests
import os
from datetime import datetime

WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")

def send_alert(text):
    requests.post(
        WEBHOOK_URL,
        json={"content": text}
    )

print("Bot działa:", datetime.now())

send_alert("✅ GitHubowy bot Retrocausality działa!")
