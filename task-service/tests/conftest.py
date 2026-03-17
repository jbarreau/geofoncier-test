import pytest

pytest_plugins = ["geofoncier_shared.testing"]


@pytest.fixture(autouse=True)
def patch_jwt_env(rsa_key_pair, monkeypatch):
    monkeypatch.setenv("JWT_PUBLIC_KEY", rsa_key_pair["public_key"])
    monkeypatch.delenv("JWT_PUBLIC_KEY_PATH", raising=False)
