from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.dependencies import get_current_user
from app.models import AlertRule, Symbol, User, UserSymbol
from app.schemas import AlertCreate, AlertResponse, AlertUpdate

router = APIRouter(prefix="/alerts", tags=["alerts"])


def alert_response(alert: AlertRule) -> AlertResponse:
    return AlertResponse(
        id=alert.id,
        symbol_id=alert.symbol.id,
        ticker=alert.symbol.ticker,
        exchange=alert.symbol.exchange,
        operator=alert.operator,
        target_price=alert.target_price,
        is_active=alert.is_active,
        cooldown_seconds=alert.cooldown_seconds,
        created_at=alert.created_at,
    )


@router.post(
    "",
    response_model=AlertResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_alert(
    payload: AlertCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Symbol not found. Follow it before creating an alert.",
        )

    subscription = db.get(
        UserSymbol,
        {"user_id": current_user.id, "symbol_id": symbol.id},
    )
    if subscription is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Follow this symbol before creating an alert.",
        )

    alert = AlertRule(
        user_id=current_user.id,
        symbol_id=symbol.id,
        operator=payload.operator,
        target_price=payload.target_price,
        cooldown_seconds=payload.cooldown_seconds,
    )

    db.add(alert)
    db.commit()
    db.refresh(alert)

    alert = db.scalar(
        select(AlertRule)
        .where(AlertRule.id == alert.id)
        .options(selectinload(AlertRule.symbol))
    )
    return alert_response(alert)


@router.get("", response_model=list[AlertResponse])
def list_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    alerts = db.scalars(
        select(AlertRule)
        .where(AlertRule.user_id == current_user.id)
        .options(selectinload(AlertRule.symbol))
        .order_by(AlertRule.created_at.desc())
    ).all()

    return [alert_response(alert) for alert in alerts]


@router.patch("/{alert_id}", response_model=AlertResponse)
def update_alert(
    alert_id: int,
    payload: AlertUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    alert = db.scalar(
        select(AlertRule)
        .where(
            AlertRule.id == alert_id,
            AlertRule.user_id == current_user.id,
        )
        .options(selectinload(AlertRule.symbol))
    )

    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(alert, field, value)

    db.commit()
    db.refresh(alert)
    return alert_response(alert)


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    alert = db.scalar(
        select(AlertRule).where(
            AlertRule.id == alert_id,
            AlertRule.user_id == current_user.id,
        )
    )

    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")

    db.delete(alert)
    db.commit()