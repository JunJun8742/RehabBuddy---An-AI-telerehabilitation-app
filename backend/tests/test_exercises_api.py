from app.models import Exercise


def auth_headers(client):
    token = client.post(
        "/api/v1/auth/register",
        json={"email": "ex@x.dev", "password": "demo1234", "display_name": "Ex"},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_exercises_requires_auth(client):
    assert client.get("/api/v1/exercises").status_code == 401


def test_exercises_returns_catalog_with_definition(client, db):
    db.add(Exercise(id="squat", name="Bodyweight squat", description="d", camera_view="side"))
    db.commit()
    r = client.get("/api/v1/exercises", headers=auth_headers(client))
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body) == 1
    assert body[0]["id"] == "squat"
    assert body[0]["definition"]["detection"]["down_threshold"] == 100
    assert body[0]["definition"]["primary_angle"] == "knee"
