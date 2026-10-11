from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.dependencies import get_current_user
from app.models import Symbol, User, UserSymbol
from app.schemas import SubscriptionCreate, SubscriptionResponse

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.post(
    "",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
)
def follow_symbol(
    payload: SubscriptionCreate,
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
        symbol = Symbol(
            ticker=ticker,
            exchange=exchange,
            display_name=payload.display_name,
        )
        db.add(symbol)
        db.flush()

    existing_subscription = db.scalar(
        select(UserSymbol).where(
            UserSymbol.user_id == current_user.id,
            UserSymbol.symbol_id == symbol.id,
        )
    )

    if existing_subscription:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already follow this symbol",
        )

    subscription = UserSymbol(
        user_id=current_user.id,
        symbol_id=symbol.id,
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)

    return SubscriptionResponse(
        symbol_id=symbol.id,
        ticker=symbol.ticker,
        exchange=symbol.exchange,
        display_name=symbol.display_name,
        created_at=subscription.created_at,
    )


@router.get("", response_model=list[SubscriptionResponse])
def list_subscriptions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    subscriptions = db.scalars(
        select(UserSymbol)
        .where(UserSymbol.user_id == current_user.id)
        .options(selectinload(UserSymbol.symbol))
        .order_by(UserSymbol.created_at.desc())
    ).all()

    return [
        SubscriptionResponse(
            symbol_id=item.symbol.id,
            ticker=item.symbol.ticker,
            exchange=item.symbol.exchange,
            display_name=item.symbol.display_name,
            created_at=item.created_at,
        )
        for item in subscriptions
    ]


@router.delete(
    "/{symbol_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def unfollow_symbol(
    symbol_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    subscription = db.get(
        UserSymbol,
        {
            "user_id": current_user.id,
            "symbol_id": symbol_id,
        },
    )

    if subscription is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        )

    db.delete(subscription)
    db.commit()