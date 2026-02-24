from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models import User, CoinBalance, CoinTransaction
from schemas import CoinBalanceResponse, CoinTransactionResponse
from security import get_current_user

router = APIRouter()


@router.get("/balance", response_model=CoinBalanceResponse)
async def get_balance(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(CoinBalance).where(CoinBalance.user_id == current_user.id)
    )
    return result.scalar_one()


@router.get("/transactions", response_model=list[CoinTransactionResponse])
async def get_transactions(
    limit: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(CoinTransaction)
        .where(CoinTransaction.user_id == current_user.id)
        .order_by(CoinTransaction.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


@router.patch("/balance/streak", response_model=CoinBalanceResponse)
async def update_streak(
    streak: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(CoinBalance).where(CoinBalance.user_id == current_user.id)
    )
    balance = result.scalar_one()
    balance.streak = streak
    await db.commit()
    await db.refresh(balance)
    return balance


@router.post("/transactions", response_model=CoinBalanceResponse)
async def add_transaction(
    amount: int,
    reason: str,
    task_id: str | None = None,
    plan_date: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Добавить транзакцию и обновить баланс."""
    result = await db.execute(
        select(CoinBalance).where(CoinBalance.user_id == current_user.id)
    )
    balance = result.scalar_one()

    # Проверяем уход в минус если штраф
    if amount < 0 and task_id is None:
        from models import UserSettings
        settings_result = await db.execute(
            select(UserSettings).where(UserSettings.user_id == current_user.id)
        )
        settings = settings_result.scalar_one()
        if not settings.allow_negative_balance:
            amount = max(-balance.balance, amount)  # не уходим глубже нуля

    balance.balance += amount
    db.add(CoinTransaction(
        user_id=current_user.id,
        amount=amount,
        reason=reason,
        task_id=task_id,
        plan_date=plan_date,
    ))
    await db.commit()
    await db.refresh(balance)
    return balance