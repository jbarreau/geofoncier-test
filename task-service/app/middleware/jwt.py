from geofoncier_shared.fastapi.jwt import CurrentUser, make_jwt_dependencies

from ..config import settings

get_current_user, require_permission = make_jwt_dependencies(
    lambda: settings.public_key_content
)

__all__ = ["CurrentUser", "get_current_user", "require_permission"]
