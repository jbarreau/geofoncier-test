from fastapi import Depends, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt

from app.exceptions import InsufficientPermissionsError, InvalidTokenError
from app.services.token_service import decode_access_token

_bearer = HTTPBearer(auto_error=False)


def get_current_user_permissions(
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
) -> list[str]:
    if credentials is None:
        raise InvalidTokenError()
    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.PyJWTError:
        raise InvalidTokenError()
    return payload.get("permissions", [])


def require_permission(permission: str):
    def _check(
        permissions: list[str] = Depends(get_current_user_permissions),
    ) -> list[str]:
        if permission not in permissions:
            raise InsufficientPermissionsError()
        return permissions

    return _check
