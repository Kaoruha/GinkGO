"""#5738: deploy templates endpoint must not be swallowed by /{portfolio_id}."""

from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_deploy_templates_returns_200_with_list():
    from api import deployment

    app = FastAPI()
    app.include_router(deployment.router, prefix="/api/v1/deploy")
    client = TestClient(app)

    response = client.get("/api/v1/deploy/templates")

    assert response.status_code == 200
    body = response.json()
    assert body["data"]
    assert {item["mode"] for item in body["data"]} == {"paper", "live"}
