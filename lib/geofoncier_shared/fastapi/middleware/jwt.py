import os

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from geofoncier_shared.fastapi.schemas.auth import CurrentUser
from geofoncier_shared.redis.redis_client import get_redis


def _get_public_key() -> str:
    key = os.environ.get("JWT_PUBLIC_KEY", "")
    if key:
        return key
    path = os.environ.get("JWT_PUBLIC_KEY_PATH", "")
    if path:
        with open(path) as f:
            return f.read()
    raise ValueError(
        "No JWT public key configured (set JWT_PUBLIC_KEY or JWT_PUBLIC_KEY_PATH)"
    )


_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    redis=Depends(get_redis),
) -> CurrentUser:
    if credentials is None:
        raise HTTPException(
            status_code=401, detail="Missing or invalid Authorization header"
        )

    token = credentials.credentials
    try:
        payload = jwt.decode(token, _get_public_key(), algorithms=["RS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    jti = payload.get("jti")
    if jti and await redis.get(f"blacklist:{jti}"):
        raise HTTPException(status_code=401, detail="Token has been revoked")

    try:
        return CurrentUser(
            user_id=payload["sub"],
            roles=payload.get("roles", []),
            permissions=payload.get("permissions", []),
        )
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Invalid token payload") from exc


def require_permission(permission: str) -> Depends:
    """Dependency factory — use as a route dependency:

    @router.post("/api/tasks")
    async def create_task(user: CurrentUser = require_permission("tasks:create")):
        ...
    """

    async def _check(
        current_user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        if permission not in current_user.permissions:
            raise HTTPException(
                status_code=403,
                detail=f"Permission required: {permission}",
            )
        return current_user

    return Depends(_check)
