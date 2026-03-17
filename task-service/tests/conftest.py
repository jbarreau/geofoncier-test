import pytest

pytest_plugins = ["geofoncier_shared.testing"]


@pytest.fixture(autouse=True)
def patch_settings(rsa_key_pair, monkeypatch):
    from app import config

    monkeypatch.setattr(config.settings, "jwt_public_key", rsa_key_pair["public_key"])
    monkeypatch.setattr(config.settings, "jwt_public_key_path", "")
