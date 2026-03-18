import base64

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services import login_user, logout_user, refresh_tokens, register_user
from geofoncier_shared.redis.redis_client import get_redis

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    return await register_user(db, body.email, body.password)


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> TokenResponse:
    return await login_user(db, redis, body.email, body.password)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> TokenResponse:
    return await refresh_tokens(db, redis, body.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    body: LogoutRequest,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> None:
    await logout_user(db, redis, body.access_token, body.refresh_token)


@router.get("/.well-known/jwks.json", include_in_schema=False)
async def jwks() -> dict:
    """Expose the RS256 public key in JWKS format for other services."""
    from cryptography.hazmat.primitives.serialization import load_pem_public_key

    from app.config import settings

    pub_key = load_pem_public_key(settings.public_key_content.encode())
    pub_numbers = pub_key.public_numbers()  # type: ignore[union-attr]

    def _int_to_base64url(n: int) -> str:
        length = (n.bit_length() + 7) // 8
        return base64.urlsafe_b64encode(n.to_bytes(length, "big")).rstrip(b"=").decode()

    return {
        "keys": [
            {
                "kty": "RSA",
                "use": "sig",
                "alg": "RS256",
                "n": _int_to_base64url(pub_numbers.n),
                "e": _int_to_base64url(pub_numbers.e),
                "kid": "auth-service-rs256",
            }
        ]
    }
