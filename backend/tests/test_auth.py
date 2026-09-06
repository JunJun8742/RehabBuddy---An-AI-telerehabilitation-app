from app.core.security import hash_password
from app.models import User


def register(client, email="new@x.dev", password="demo1234", name="New"):
    return client.post("/api/v1/auth/register", json={"email": email, "password": password, "display_name": name})


def test_register_creates_patient_and_returns_token(client):
    r = register(client)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == "new@x.dev"
    assert body["user"]["role"] == "patient"
    assert "password" not in body["user"] and "password_hash" not in body["user"]


def test_register_rejects_duplicate_email(client):
    register(client)
    r = register(client)
    assert r.status_code == 409


def test_register_rejects_short_password(client):
    r = register(client, password="short")
    assert r.status_code == 422


def test_login_returns_token_for_valid_credentials(client, db):
    db.add(User(email="doc@x.dev", password_hash=hash_password("demo1234"), role="doctor", display_name="Doc"))
    db.commit()
    r = client.post("/api/v1/auth/login", json={"email": "doc@x.dev", "password": "demo1234"})
    assert r.status_code == 200
    assert r.json()["user"]["role"] == "doctor"


def test_login_rejects_bad_password(client, db):
    db.add(User(email="doc2@x.dev", password_hash=hash_password("demo1234"), role="doctor", display_name="Doc"))
    db.commit()
    r = client.post("/api/v1/auth/login", json={"email": "doc2@x.dev", "password": "nope1234"})
    assert r.status_code == 401


def test_me_requires_token(client):
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_me_returns_current_user(client):
    token = register(client).json()["access_token"]
    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == "new@x.dev"
