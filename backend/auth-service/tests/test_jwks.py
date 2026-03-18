class TestJwks:
    async def test_returns_valid_rsa_jwks(self, client):
        resp = await client.get("/api/auth/.well-known/jwks.json")

        assert resp.status_code == 200
        data = resp.json()
        assert "keys" in data
        assert len(data["keys"]) == 1
        key = data["keys"][0]
        assert key["kty"] == "RSA"
        assert key["alg"] == "RS256"
        assert key["use"] == "sig"
        assert key["kid"] == "auth-service-rs256"
        assert "n" in key and len(key["n"]) > 0
        assert "e" in key and len(key["e"]) > 0


class TestHealth:
    async def test_health_check(self, client):
        resp = await client.get("/health")

        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
