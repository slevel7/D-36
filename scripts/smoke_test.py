"""Against running local web/API. Never prints session credentials."""

import os

import httpx


def main():
    base = os.getenv("SMOKE_URL", "http://localhost:3000/api")
    password = os.environ["DEMO_PASSWORD"]
    with httpx.Client(base_url=base, timeout=20) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/auth/me").status_code == 401
        response = client.post(
            "/auth/login", json={"email": "employee@example.test", "password": password}
        )
        assert response.status_code == 200, response.status_code
        client.headers["x-csrf-token"] = response.json()["csrf"]
        assert client.get("/auth/me").json()["department"] == "DEMO Pension"
        assert client.get("/documents").status_code == 200
        assert client.get("/profile/preferences").status_code == 200
        assert client.post("/auth/logout").status_code == 200
        assert client.get("/auth/me").status_code == 401
    print("PASS: web proxy, health, login, scoped library, preferences, logout revocation")


if __name__ == "__main__":
    main()
