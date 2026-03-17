import uuid
from collections.abc import Callable

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from geofoncier_shared.redis.redis_client import get_redis


class CurrentUser(BaseModel):
    user_id: uuid.UUID
    roles: list[str]
    permissions: list[str]


def make_jwt_dependencies(
    get_public_key: Callable[[], str],
) -> tuple:
    """Factory that returns ``(get_current_user, require_permission)`` bound to
    the given public-key getter.

    Usage::

        from geofoncier_shared.fastapi.jwt import make_jwt_dependencies
        from .config import settings

        get_current_user, require_permission = make_jwt_dependencies(
            lambda: settings.public_key_content
        )
    """
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
            payload = jwt.decode(
                token,
                get_public_key(),
                algorithms=["RS256"],
            )
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
            raise HTTPException(
                status_code=401, detail="Invalid token payload"
            ) from exc

    def require_permission(permission: str) -> Depends:
        """Dependency factory — use as a route dependency:

        @router.post("/tasks")
        async def create_task(user: CurrentUser = require_permission("task:create")):
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

    return get_current_user, require_permission
