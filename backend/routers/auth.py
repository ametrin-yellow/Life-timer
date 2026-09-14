import hashlib
import hmac
import time

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests

from database import get_db
from config import settings as app_settings
from models import User, UserSettings, CoinBalance
from security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    decode_token, get_current_user,
)

router = APIRouter()


# ──────────────────────────────────────────────
#  Схемы
# ──────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: int
    email: str
    has_password: bool = False
    has_google: bool = False
    has_telegram: bool = False

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────
#  Эндпоинты
# ──────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Проверяем что email свободен
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email уже зарегистрирован")

    # Создаём пользователя + дефолтные настройки + нулевой баланс
    user = User(email=data.email, hashed_password=hash_password(data.password))
    db.add(user)
    await db.flush()  # получаем user.id до commit

    db.add(UserSettings(user_id=user.id))
    db.add(CoinBalance(user_id=user.id))
    await db.commit()

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    # OAuth2PasswordRequestForm использует поле username — у нас это email
    result = await db.execute(select(User).where(User.email == form.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
        )
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Аккаунт деактивирован")

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.get("/google-client-id")
async def google_client_id():
    return {"client_id": app_settings.google_client_id or None}


class GoogleAuthRequest(BaseModel):
    credential: str


@router.post("/google", response_model=TokenResponse)
async def google_auth(data: GoogleAuthRequest, db: AsyncSession = Depends(get_db)):
    if not app_settings.google_client_id:
        raise HTTPException(status_code=501, detail="Google OAuth не настроен")

    try:
        idinfo = google_id_token.verify_oauth2_token(
            data.credential,
            google_requests.Request(),
            app_settings.google_client_id,
        )
    except ValueError:
        raise HTTPException(status_code=401, detail="Невалидный Google токен")

    google_id = idinfo["sub"]
    email = idinfo.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Google аккаунт без email")

    result = await db.execute(select(User).where(User.google_id == google_id))
    user = result.scalar_one_or_none()

    if not user:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user:
            user.google_id = google_id
        else:
            user = User(email=email, google_id=google_id)
            db.add(user)
            await db.flush()
            db.add(UserSettings(user_id=user.id))
            db.add(CoinBalance(user_id=user.id))

        await db.commit()

    if not user.is_active:
        raise HTTPException(status_code=400, detail="Аккаунт деактивирован")

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.get("/telegram-bot")
async def telegram_bot():
    return {"bot_username": app_settings.telegram_bot_username or None}


class TelegramAuthRequest(BaseModel):
    id: int
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    photo_url: str | None = None
    auth_date: int
    hash: str


def _verify_telegram_auth(raw: dict, bot_token: str) -> bool:
    data = {k: v for k, v in raw.items() if k != "hash"}
    check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    computed = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()
    if computed != raw.get("hash"):
        return False
    if time.time() - int(raw["auth_date"]) > 86400:
        return False
    return True


@router.post("/telegram", response_model=TokenResponse)
async def telegram_auth(request: Request, db: AsyncSession = Depends(get_db)):
    if not app_settings.telegram_bot_token:
        raise HTTPException(status_code=501, detail="Telegram Login не настроен")

    raw = await request.json()
    if not _verify_telegram_auth(raw, app_settings.telegram_bot_token):
        raise HTTPException(status_code=401, detail="Невалидные данные Telegram")

    data = TelegramAuthRequest(**raw)

    tg_id = str(data.id)

    result = await db.execute(select(User).where(User.telegram_id == tg_id))
    user = result.scalar_one_or_none()

    if not user:
        tg_name = data.username or data.first_name or str(data.id)
        email = f"tg_{data.id}@telegram.local"
        user = User(email=email, telegram_id=tg_id)
        db.add(user)
        await db.flush()
        db.add(UserSettings(user_id=user.id))
        db.add(CoinBalance(user_id=user.id))
        await db.commit()

    if not user.is_active:
        raise HTTPException(status_code=400, detail="Аккаунт деактивирован")

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    user_id = decode_token(data.refresh_token, expected_type="refresh")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Пользователь не найден")

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),  # ротация refresh токена
    )


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.post("/change-password")
async def change_password(
    data: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.hashed_password:
        raise HTTPException(status_code=400, detail="Аккаунт использует Google вход. Установите пароль через настройки.")
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Неверный текущий пароль")

    current_user.hashed_password = hash_password(data.new_password)
    await db.commit()
    return {"ok": True}


@router.post("/link-telegram")
async def link_telegram(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not app_settings.telegram_bot_token:
        raise HTTPException(status_code=501, detail="Telegram Login не настроен")

    raw = await request.json()
    if not _verify_telegram_auth(raw, app_settings.telegram_bot_token):
        raise HTTPException(status_code=401, detail="Невалидные данные Telegram")

    tg_id = str(raw["id"])

    result = await db.execute(select(User).where(User.telegram_id == tg_id))
    existing = result.scalar_one_or_none()
    if existing and existing.id != current_user.id:
        raise HTTPException(status_code=400, detail="Этот Telegram аккаунт уже привязан к другому пользователю")

    current_user.telegram_id = tg_id
    await db.commit()
    return {"ok": True}


@router.post("/unlink-telegram")
async def unlink_telegram(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.telegram_id:
        raise HTTPException(status_code=400, detail="Telegram не привязан")
    if not current_user.hashed_password and not current_user.google_id:
        raise HTTPException(status_code=400, detail="Нельзя отвязать единственный способ входа")

    current_user.telegram_id = None
    await db.commit()
    return {"ok": True}


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        has_password=current_user.hashed_password is not None,
        has_google=current_user.google_id is not None,
        has_telegram=current_user.telegram_id is not None,
    )