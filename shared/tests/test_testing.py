import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


@pytest.fixture(scope="module")
def key_pair(rsa_key_pair):
    return rsa_key_pair


class TestRsaKeyPairFixture:
    def test_returns_dict_with_expected_keys(self, rsa_key_pair):
        assert set(rsa_key_pair.keys()) == {"private_key", "public_key"}

    def test_private_key_is_valid_rsa_pem(self, rsa_key_pair):
        key = serialization.load_pem_private_key(
            rsa_key_pair["private_key"].encode(), password=None
        )
        assert isinstance(key, rsa.RSAPrivateKey)

    def test_public_key_is_valid_rsa_pem(self, rsa_key_pair):
        key = serialization.load_pem_public_key(rsa_key_pair["public_key"].encode())
        assert isinstance(key, rsa.RSAPublicKey)

    def test_key_size_is_2048(self, rsa_key_pair):
        key = serialization.load_pem_private_key(
            rsa_key_pair["private_key"].encode(), password=None
        )
        assert key.key_size == 2048

    def test_public_key_matches_private_key(self, rsa_key_pair):
        private_key = serialization.load_pem_private_key(
            rsa_key_pair["private_key"].encode(), password=None
        )
        derived_public_pem = (
            private_key.public_key()
            .public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            .decode()
        )
        assert derived_public_pem == rsa_key_pair["public_key"]
