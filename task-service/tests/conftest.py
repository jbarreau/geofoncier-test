import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


@pytest.fixture(scope="session")
def rsa_key_pair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    return {"private_key": private_pem, "public_key": public_pem}


@pytest.fixture(autouse=True)
def patch_settings(rsa_key_pair, monkeypatch):
    from app import config
    monkeypatch.setattr(config.settings, "jwt_public_key", rsa_key_pair["public_key"])
    monkeypatch.setattr(config.settings, "jwt_public_key_path", "")
