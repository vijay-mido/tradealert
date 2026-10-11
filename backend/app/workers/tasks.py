import os
from datetime import datetime, timezone
from html import escape

import httpx

from app.db import SessionLocal
from app.models import NotificationLog, NotificationStatus
from app.workers.celery_app import celery_app


def send_telegram_message(text: str) -> None:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]

    response = httpx.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        },
        timeout=10,
    )
    response.raise_for_status()

    if not response.json().get("ok"):
        raise RuntimeError("Telegram rejected the message")


@celery_app.task(name="notifications.deliver")
def deliver_notification(notification_log_id: int) -> dict:
    db = SessionLocal()

    try:
        notification = db.get(NotificationLog, notification_log_id)

        if notification is None:
            return {"status": "missing"}

        if notification.status == NotificationStatus.SENT:
            return {"status": "already_sent"}

        notification.status = NotificationStatus.PROCESSING
        notification.attempts += 1
        db.commit()

        rule = notification.rule
        symbol = rule.symbol

        operator_labels = {
            "gt": "Above",
            "gte": "At or above",
            "lt": "Below",
            "lte": "At or below",
        }

        condition = operator_labels[rule.operator.value]
        ticker = escape(symbol.ticker)
        target = f"{rule.target_price:,.2f}"

        send_telegram_message(
            f"<b>📈 TradeAlert</b>\n"
            f"<b>{ticker} crossed {condition.lower()} its target</b>\n\n"
            f"<pre>"
            f"Symbol     {ticker}\n"
            f"Condition  {condition} ₹{target}\n"
            f"Status     Triggered"
            f"</pre>\n\n"
            f"<i>Simulated price crossing detected.</i>"
        )

        notification.status = NotificationStatus.SENT
        notification.sent_at = datetime.now(timezone.utc)
        notification.error_message = None
        db.commit()

        return {"status": "sent"}

    except Exception as error:
        db.rollback()

        notification = db.get(NotificationLog, notification_log_id)
        if notification is not None:
            notification.status = NotificationStatus.FAILED
            notification.error_message = str(error)
            db.commit()

        raise

    finally:
        db.close()