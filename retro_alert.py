import requests
from datetime import datetime

WEBHOOK_URL = "TUTAJ_PÓŹNIEJ"

def send_alert(text):
    requests.post(
        WEBHOOK_URL,
        json={"content": text}
    )

print("Bot działa:", datetime.now())
