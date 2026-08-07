from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models import User, Reward, CoinBalance, CoinTransaction, UserSettings, RewardType
from schemas import RewardCreate, RewardUpdate, RewardResponse
from security import get_current_user

router = APIRouter()


async def _get_reward_or_404(reward_id: int, user: User, db: AsyncSession) -> Reward:
    result = await db.execute(
        select(Reward).where(Reward.id == reward_id, Reward.user_id == user.id)
    )
    reward = result.scalar_one_or_none()
    if not reward:
        raise HTTPException(status_code=404, detail="Награда не найдена")
    return reward


@router.get("/", response_model=list[RewardResponse])
async def get_rewards(
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(Reward).where(Reward.user_id == current_user.id)
    if active_only:
        q = q.where(Reward.is_active == True)
    q = q.order_by(Reward.price)
    result = await db.execute(q)
    return result.scalars().all()


@router.post("/", response_model=RewardResponse, status_code=status.HTTP_201_CREATED)
async def create_reward(
    data: RewardCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    reward = Reward(
        user_id=current_user.id,
        **data.model_dump(),
        count_initial=data.count,
    )
    db.add(reward)
    await db.commit()
    await db.refresh(reward)
    return reward


@router.patch("/{reward_id}", response_model=RewardResponse)
async def update_reward(
    reward_id: int,
    data: RewardUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    reward = await _get_reward_or_404(reward_id, current_user, db)

    if data.name is not None:
        reward.name = data.name
    if data.price is not None:
        reward.price = data.price
    if data.description is not None:
        reward.description = data.description
    if data.count_add > 0 and reward.reward_type == RewardType.LIMITED:
        reward.count = (reward.count or 0) + data.count_add
        reward.count_initial = (reward.count_initial or 0) + data.count_add

    await db.commit()
    await db.refresh(reward)
    return reward


@router.delete("/{reward_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reward(
    reward_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    reward = await _get_reward_or_404(reward_id, current_user, db)
    await db.delete(reward)
    await db.commit()


@router.post("/{reward_id}/purchase", response_model=dict)
async def purchase_reward(
    reward_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    reward = await _get_reward_or_404(reward_id, current_user, db)

    if not reward.is_active:
        raise HTTPException(status_code=400, detail="Награда недоступна")
    if reward.reward_type == RewardType.LIMITED and (reward.count or 0) <= 0:
        raise HTTPException(status_code=400, detail="Товар закончился")

    bal_result = await db.execute(
        select(CoinBalance).where(CoinBalance.user_id == current_user.id)
    )
    balance = bal_result.scalar_one()

    if balance.balance < reward.price:
        raise HTTPException(status_code=400, detail="Недостаточно коинов")

    balance.balance -= reward.price

    if reward.reward_type == RewardType.LIMITED:
        reward.count -= 1

    db.add(CoinTransaction(
        user_id=current_user.id,
        amount=-reward.price,
        reason=f"Покупка: {reward.name}",
        reward_id=reward.id,
    ))

    await db.commit()
    return {"new_balance": balance.balance}