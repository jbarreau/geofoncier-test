import uuid

import jwt
import pytest

from app.services.token_service import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    verify_refresh_token,
)


class TestCreateAccessToken:
    def test_returns_three_values(self) -> None:
        token, jti, exp = create_access_token(uuid.uuid4(), "u@e.com", [], [])
        assert isinstance(token, str)
        assert isinstance(jti, str)

    def test_payload_contains_expected_claims(self) -> None:
        user_id = uuid.uuid4()
        token, jti, _ = create_access_token(
            user_id, "user@example.com", ["admin"], ["users:read"]
        )
        payload = decode_access_token(token)
        assert payload["sub"] == str(user_id)
        assert payload["email"] == "user@example.com"
        assert payload["roles"] == ["admin"]
        assert payload["permissions"] == ["users:read"]
        assert payload["jti"] == jti

    def test_jti_is_unique_per_call(self) -> None:
        _, jti1, _ = create_access_token(uuid.uuid4(), "a@a.com", [], [])
        _, jti2, _ = create_access_token(uuid.uuid4(), "b@b.com", [], [])
        assert jti1 != jti2

    def test_empty_roles_and_permissions(self) -> None:
        token, _, _ = create_access_token(uuid.uuid4(), "u@e.com", [], [])
        payload = decode_access_token(token)
        assert payload["roles"] == []
        assert payload["permissions"] == []


class TestCreateRefreshToken:
    def test_returns_four_values(self) -> None:
        raw, token_hash, expires_at, db_id = create_refresh_token()
        assert isinstance(raw, str)
        assert isinstance(token_hash, str)
        assert isinstance(db_id, uuid.UUID)

    def test_raw_token_embeds_db_id(self) -> None:
        raw, _, _, db_id = create_refresh_token()
        assert raw.startswith(str(db_id) + ":")

    def test_hash_verifies_against_raw(self) -> None:
        raw, token_hash, _, _ = create_refresh_token()
        assert verify_refresh_token(raw, token_hash) is True

    def test_unique_db_id_per_call(self) -> None:
        _, _, _, db_id1 = create_refresh_token()
        _, _, _, db_id2 = create_refresh_token()
        assert db_id1 != db_id2


class TestVerifyRefreshToken:
    def test_correct_raw_returns_true(self) -> None:
        raw, token_hash, _, _ = create_refresh_token()
        assert verify_refresh_token(raw, token_hash) is True

    def test_wrong_raw_returns_false(self) -> None:
        _, token_hash, _, _ = create_refresh_token()
        assert verify_refresh_token("tampered:payload", token_hash) is False

    def test_empty_raw_returns_false(self) -> None:
        _, token_hash, _, _ = create_refresh_token()
        assert verify_refresh_token("", token_hash) is False


class TestDecodeAccessToken:
    def test_valid_token_returns_payload(self) -> None:
        user_id = uuid.uuid4()
        token, _, _ = create_access_token(user_id, "u@e.com", [], [])
        payload = decode_access_token(token)
        assert payload["sub"] == str(user_id)

    def test_garbage_raises_jwt_error(self) -> None:
        with pytest.raises(jwt.PyJWTError):
            decode_access_token("not.a.jwt")

    def test_tampered_signature_raises_jwt_error(self) -> None:
        token, _, _ = create_access_token(uuid.uuid4(), "u@e.com", [], [])
        tampered = token[:-6] + "XXXXXX"
        with pytest.raises(jwt.PyJWTError):
            decode_access_token(tampered)
