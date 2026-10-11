from fastapi import FastAPI, status, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.auth import router as auth_router
from app.db import engine, get_db
from app.dependencies import get_current_user
from app.models import User         
from app.schemas import UserResponse
from app.api.subscriptions import router as subscriptions_router
from app.api.alerts import router as alerts_router
from app.api.simulator import router as simulator_router

app = FastAPI(title="TradeAlert")
app.include_router(auth_router)
app.include_router(subscriptions_router)
app.include_router(alerts_router)
app.include_router(simulator_router)

@app.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return {
            "status": "ok",
            "database": "connected",
        }
    except SQLAlchemyError:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unavailable",
                "database": "disconnected",
            },
        )
@app.get("/me", response_model=UserResponse)
def read_current_user(
    current_user: User = Depends(get_current_user),
):
    return current_user