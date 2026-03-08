import hmac
import hashlib
from urllib.parse import parse_qsl
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.config import settings
from app.core.security import create_access_token
from app.schemas.auth import AuthRequest, AuthResponse
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


def _verify_telegram_init_data(init_data: str, bot_token: str) -> dict:
    # Telegram WebApp validation:
    # 1) parse querystring
    # 2) extract hash
    # 3) build data_check_string from sorted key=value pairs without hash
    # 4) secret_key = HMAC_SHA256("WebAppData", bot_token)
    # 5) computed_hash = HMAC_SHA256(secret_key, data_check_string)
    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise ValueError("hash missing")

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        raise ValueError("hash mismatch")

    return pairs


@router.post("/telegram", response_model=AuthResponse)
async def auth_telegram(payload: AuthRequest, db: AsyncSession = Depends(get_db)):
    if settings.TELEGRAM_AUTH_DEV_BYPASS:
        # DEV: создаём/находим пользователя с telegram_id=1
        telegram_id = 1
        name = "DEV"
    else:
        try:
            data = _verify_telegram_init_data(payload.initData, settings.BOT_TOKEN)
        except Exception as e:
            raise HTTPException(status_code=401, detail=f"Telegram initData invalid: {e}")

        # user is JSON inside "user"
        # We avoid JSON parsing in stage 1: extract telegram_id roughly from payload "user" string.
        # На этапе 2 сделаем нормальный json decode.
        user_raw = data.get("user")
        if not user_raw:
            raise HTTPException(status_code=401, detail="user missing in initData")

        # Очень простой парсер: ищем '"id":123'
        import re
        m_id = re.search(r'"id"\s*:\s*(\d+)', user_raw)
        m_name = re.search(r'"first_name"\s*:\s*"([^"]+)"', user_raw)
        if not m_id:
            raise HTTPException(status_code=401, detail="Cannot parse telegram user id")

        telegram_id = int(m_id.group(1))
        name = m_name.group(1) if m_name else "User"

    user = await db.scalar(select(User).where(User.telegram_id == telegram_id))
    if not user:
        user = User(telegram_id=telegram_id, name=name)
        db.add(user)
        await db.commit()
        await db.refresh(user)

    token = create_access_token(str(user.id))
    return AuthResponse(token=token)