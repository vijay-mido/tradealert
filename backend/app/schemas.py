from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from decimal import Decimal
from app.models import AlertOperator

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    created_at: datetime
    
class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    
class SubscriptionCreate(BaseModel):
    ticker: str = Field(min_length=1, max_length=32)
    exchange: str = Field(default="NSE", min_length=1, max_length=32)
    display_name: str | None = Field(default=None, max_length=255)


class SubscriptionResponse(BaseModel):
    symbol_id: int
    ticker: str
    exchange: str
    display_name: str | None
    created_at: datetime
    
class AlertCreate(BaseModel):
    ticker: str = Field(min_length=1, max_length=32)
    exchange: str = Field(default="NSE", min_length=1, max_length=32)
    operator: AlertOperator
    target_price: Decimal = Field(gt=0)
    cooldown_seconds: int = Field(default=3600, ge=0, le=86400)


class AlertUpdate(BaseModel):
    operator: AlertOperator | None = None
    target_price: Decimal | None = Field(default=None, gt=0)
    is_active: bool | None = None
    cooldown_seconds: int | None = Field(default=None, ge=0, le=86400)


class AlertResponse(BaseModel):
    id: int
    symbol_id: int
    ticker: str
    exchange: str
    operator: AlertOperator
    target_price: Decimal
    is_active: bool
    cooldown_seconds: int
    created_at: datetime
    
class SimulatePriceRequest(BaseModel):
    ticker: str = Field(min_length=1, max_length=32)
    exchange: str = Field(default="NSE", min_length=1, max_length=32)
    price: Decimal = Field(gt=0)


class SimulatePriceResponse(BaseModel):
    ticker: str
    price: Decimal
    triggered_rule_ids: list[int]