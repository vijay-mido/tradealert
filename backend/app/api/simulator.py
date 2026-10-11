from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.workers.tasks import deliver_notification
from app.db import get_db
from app.dependencies import get_current_user
from app.models import (
    AlertOperator,
    AlertRule,
    NotificationLog,
    NotificationStatus,
    PriceSnapshot,
    Symbol,
    User,
)
from app.schemas import (
    SimulatePriceRequest,
    SimulatePriceResponse,
)

router = APIRouter(prefix="/debug", tags=["simulator"])


def has_crossed(
    operator: AlertOperator,
    previous_price,
    current_price,
    target_price,
) -> bool:
    if previous_price is None:
        return False

    if operator == AlertOperator.GT:
        return previous_price <= target_price < current_price
    if operator == AlertOperator.GTE:
        return previous_price < target_price <= current_price
    if operator == AlertOperator.LT:
        return previous_price >= target_price > current_price
    if operator == AlertOperator.LTE:
        return previous_price > target_price >= current_price

    return False


@router.post("/simulate-price", response_model=SimulatePriceResponse)
def simulate_price(
    payload: SimulatePriceRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    ticker = payload.ticker.strip().upper()
    exchange = payload.exchange.strip().upper()

    symbol = db.scalar(
        select(Symbol).where(
            Symbol.ticker == ticker,
            Symbol.exchange == exchange,
        )
    )
    if symbol is None:
        raise HTTPException(status_code=404, detail="Symbol not found")

    now = datetime.now(timezone.utc)

    db.add(
        PriceSnapshot(
            symbol_id=symbol.id,
            price=payload.price,
            source="simulator",
            observed_at=now,
        )
    )

    rules = db.scalars(
        select(AlertRule).where(
            AlertRule.symbol_id == symbol.id,
            AlertRule.is_active.is_(True),
        )
    ).all()

    triggered_rule_ids = []
    new_notifications = []
    for rule in rules:
        crossed = has_crossed(
            rule.operator,
            rule.last_evaluated_price,
            payload.price,
            rule.target_price,
        )

        cooldown_complete = (
            rule.last_triggered_at is None
            or now - rule.last_triggered_at
            >= timedelta(seconds=rule.cooldown_seconds)
        )

        if crossed and cooldown_complete:
            notification = NotificationLog(
                rule_id=rule.id,
                user_id=rule.user_id,
                event_key=f"rule-{rule.id}-{now.isoformat()}",
                status=NotificationStatus.PENDING,
            )

            db.add(notification)
            new_notifications.append(notification)
            triggered_rule_ids.append(rule.id)

        rule.last_evaluated_price = payload.price
        rule.last_evaluated_at = now

    db.commit()

    for notification in new_notifications:
        deliver_notification.delay(notification.id)

    return {
        "ticker": ticker,
        "price": payload.price,
        "triggered_rule_ids": triggered_rule_ids,
    }