"""Admin access controls and the Swagger OAuth2 login contract."""

from backend.tests.conftest import DEMO_EMAIL, DEMO_PASSWORD


def test_swagger_oauth2_login(client):
    response = client.post(
        "/api/v1/auth/token",
        data={"username": DEMO_EMAIL, "password": DEMO_PASSWORD},
    )

    assert response.status_code == 200, response.text
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]


def test_openapi_exposes_admin_and_oauth2_password_flow(client):
    spec = client.get("/openapi.json").json()

    assert "/api/v1/admin/overview" in spec["paths"]
    assert "/api/v1/admin/users" in spec["paths"]
    assert "/api/v1/admin/leads" in spec["paths"]
    schemes = spec["components"]["securitySchemes"]
    oauth = next(value for value in schemes.values() if value["type"] == "oauth2")
    assert oauth["flows"]["password"]["tokenUrl"] == "/api/v1/auth/token"


def test_admin_api_requires_admin_role(client, demo_auth):
    headers = demo_auth["headers"]

    assert client.get("/api/v1/admin/overview").status_code == 401
    assert client.get("/api/v1/admin/overview", headers=headers).status_code == 403
    assert client.get("/api/v1/admin/users", headers=headers).status_code == 403
    assert client.get("/api/v1/admin/leads", headers=headers).status_code == 403
