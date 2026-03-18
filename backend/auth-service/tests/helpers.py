import uuid
from datetime import datetime, timezone

from app.schemas import TokenResponse, UserResponse


def make_user(email: str = "user@example.com") -> UserResponse:
    return UserResponse(
        id=uuid.uuid4(),
        email=email,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )


def make_tokens() -> TokenResponse:
    return TokenResponse(
        access_token="header.payload.sig",
        refresh_token=f"{uuid.uuid4()}:{uuid.uuid4()}",
    )
