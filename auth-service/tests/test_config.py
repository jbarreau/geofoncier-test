import pytest


class TestPrivateKeyContent:
    def test_inline_key_is_returned(self, rsa_key_pair) -> None:
        from app.config import Settings

        private_pem, _ = rsa_key_pair
        s = Settings(jwt_private_key=private_pem)
        assert s.private_key_content == private_pem

    def test_reads_from_file_when_path_configured(self, tmp_path, rsa_key_pair) -> None:
        from app.config import Settings

        private_pem, _ = rsa_key_pair
        key_file = tmp_path / "private.pem"
        key_file.write_text(private_pem)

        s = Settings(jwt_private_key="", jwt_private_key_path=str(key_file))
        assert s.private_key_content == private_pem

    def test_raises_when_not_configured(self) -> None:
        from app.config import Settings

        s = Settings(jwt_private_key="", jwt_private_key_path="")
        with pytest.raises(ValueError, match="JWT_PRIVATE_KEY"):
            _ = s.private_key_content


class TestPublicKeyContent:
    def test_inline_key_is_returned(self, rsa_key_pair) -> None:
        from app.config import Settings

        _, public_pem = rsa_key_pair
        s = Settings(jwt_public_key=public_pem)
        assert s.public_key_content == public_pem

    def test_reads_from_file_when_path_configured(self, tmp_path, rsa_key_pair) -> None:
        from app.config import Settings

        _, public_pem = rsa_key_pair
        key_file = tmp_path / "public.pem"
        key_file.write_text(public_pem)

        s = Settings(jwt_public_key="", jwt_public_key_path=str(key_file))
        assert s.public_key_content == public_pem

    def test_raises_when_not_configured(self) -> None:
        from app.config import Settings

        s = Settings(jwt_public_key="", jwt_public_key_path="")
        with pytest.raises(ValueError, match="JWT_PUBLIC_KEY"):
            _ = s.public_key_content
