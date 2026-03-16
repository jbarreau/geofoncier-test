from app.services.password_service import hash_password, verify_password


class TestHashPassword:
    def test_returns_bcrypt_hash(self) -> None:
        result = hash_password("secret")
        assert result.startswith("$2b$")

    def test_does_not_return_plain_text(self) -> None:
        assert hash_password("secret") != "secret"

    def test_same_plain_produces_different_hashes(self) -> None:
        assert hash_password("secret") != hash_password("secret")


class TestVerifyPassword:
    def test_correct_password_returns_true(self) -> None:
        hashed = hash_password("secret")
        assert verify_password("secret", hashed) is True

    def test_wrong_password_returns_false(self) -> None:
        hashed = hash_password("secret")
        assert verify_password("wrong", hashed) is False

    def test_empty_password_returns_false(self) -> None:
        hashed = hash_password("secret")
        assert verify_password("", hashed) is False
