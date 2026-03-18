import pytest

from geofoncier_shared.fastapi.config_mixin import PublicKeyMixin


class ConcreteSettings(PublicKeyMixin):
    """Minimal concrete class for testing the mixin standalone."""

    pass


class TestPublicKeyMixin:
    def test_returns_inline_key(self):
        s = ConcreteSettings()
        s.jwt_public_key = "inline-key"
        s.jwt_public_key_path = ""
        assert s.public_key_content == "inline-key"

    def test_inline_key_takes_precedence_over_path(self, tmp_path):
        key_file = tmp_path / "pub.pem"
        key_file.write_text("file-key")
        s = ConcreteSettings()
        s.jwt_public_key = "inline-key"
        s.jwt_public_key_path = str(key_file)
        assert s.public_key_content == "inline-key"

    def test_reads_from_file_when_no_inline_key(self, tmp_path):
        key_file = tmp_path / "pub.pem"
        key_file.write_text("file-key")
        s = ConcreteSettings()
        s.jwt_public_key = ""
        s.jwt_public_key_path = str(key_file)
        assert s.public_key_content == "file-key"

    def test_raises_when_neither_configured(self):
        s = ConcreteSettings()
        s.jwt_public_key = ""
        s.jwt_public_key_path = ""
        with pytest.raises(ValueError, match="JWT_PUBLIC_KEY"):
            _ = s.public_key_content

    def test_default_values(self):
        s = ConcreteSettings()
        assert s.jwt_public_key == ""
        assert s.jwt_public_key_path == ""
