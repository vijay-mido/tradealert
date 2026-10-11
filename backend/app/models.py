from __future__ import annotations

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class AlertOperator(str, PyEnum):
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"


class NotificationStatus(str, PyEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    SENT = "sent"
    FAILED = "failed"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    subscriptions: Mapped[list[UserSymbol]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    alert_rules: Mapped[list[AlertRule]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    notification_logs: Mapped[list[NotificationLog]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class Symbol(Base):
    __tablename__ = "symbols"
    __table_args__ = (
        UniqueConstraint("ticker", "exchange", name="uq_symbols_ticker_exchange"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    ticker: Mapped[str] = mapped_column(String(32))
    exchange: Mapped[str] = mapped_column(String(32))
    display_name: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    subscriptions: Mapped[list[UserSymbol]] = relationship(back_populates="symbol")
    alert_rules: Mapped[list[AlertRule]] = relationship(back_populates="symbol")
    price_snapshots: Mapped[list[PriceSnapshot]] = relationship(
        back_populates="symbol",
        cascade="all, delete-orphan",
    )


class UserSymbol(Base):
    """A user's subscription to one shared stock symbol."""

    __tablename__ = "user_symbols"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    symbol_id: Mapped[int] = mapped_column(
        ForeignKey("symbols.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    user: Mapped[User] = relationship(back_populates="subscriptions")
    symbol: Mapped[Symbol] = relationship(back_populates="subscriptions")


class AlertRule(Base):
    __tablename__ = "alert_rules"
    __table_args__ = (
        Index("ix_alert_rules_user_active", "user_id", "is_active"),
        Index("ix_alert_rules_symbol_active", "symbol_id", "is_active"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    symbol_id: Mapped[int] = mapped_column(
        ForeignKey("symbols.id", ondelete="CASCADE"),
        index=True,
    )
    operator: Mapped[AlertOperator] = mapped_column(
        Enum(AlertOperator, name="alert_operator")
    )
    target_price: Mapped[float] = mapped_column(Numeric(18, 4))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    cooldown_seconds: Mapped[int] = mapped_column(Integer, default=3600)

    # Used later by the monitor to make crossing detection deterministic.
    last_evaluated_price: Mapped[float | None] = mapped_column(Numeric(18, 4))
    last_evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_triggered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    user: Mapped[User] = relationship(back_populates="alert_rules")
    symbol: Mapped[Symbol] = relationship(back_populates="alert_rules")
    notification_logs: Mapped[list[NotificationLog]] = relationship(
        back_populates="rule",
        cascade="all, delete-orphan",
    )


class PriceSnapshot(Base):
    __tablename__ = "price_snapshots"
    __table_args__ = (
        Index("ix_price_snapshots_symbol_observed", "symbol_id", "observed_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    symbol_id: Mapped[int] = mapped_column(
        ForeignKey("symbols.id", ondelete="CASCADE"),
        index=True,
    )
    price: Mapped[float] = mapped_column(Numeric(18, 4))
    source: Mapped[str] = mapped_column(String(50), default="simulator")
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    symbol: Mapped[Symbol] = relationship(back_populates="price_snapshots")


class NotificationLog(Base):
    __tablename__ = "notification_logs"
    __table_args__ = (
        Index("ix_notification_logs_user_created", "user_id", "created_at"),
        Index("ix_notification_logs_status_created", "status", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    rule_id: Mapped[int] = mapped_column(
        ForeignKey("alert_rules.id", ondelete="CASCADE"),
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )

    # Unique key makes repeated queue delivery safe.
    event_key: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    status: Mapped[NotificationStatus] = mapped_column(
        Enum(NotificationStatus, name="notification_status"),
        default=NotificationStatus.PENDING,
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    rule: Mapped[AlertRule] = relationship(back_populates="notification_logs")
    user: Mapped[User] = relationship(back_populates="notification_logs")