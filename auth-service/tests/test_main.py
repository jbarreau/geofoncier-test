from httpx import AsyncClient


class TestHealth:
    async def test_returns_200(self, client: AsyncClient) -> None:
        resp = await client.get("/health")
        assert resp.status_code == 200

    async def test_returns_ok_status(self, client: AsyncClient) -> None:
        resp = await client.get("/health")
        assert resp.json() == {"status": "ok"}
