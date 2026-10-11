import os

import httpx

token = os.environ["TELEGRAM_BOT_TOKEN"]

response = httpx.get(
    f"https://api.telegram.org/bot{token}/getUpdates",
    timeout=10,
)
response.raise_for_status()

for update in response.json()["result"]:
    chat = update.get("message", {}).get("chat", {})
    if chat:
        print(f"chat_id={chat['id']}, type={chat['type']}")