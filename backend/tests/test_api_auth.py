from datetime import datetime

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.config.settings import settings
from app.core.security import create_token, get_current_user
from app.database.session import get_db
from app.entity.db_models import User


class _FakeQuery:
    def __init__(self, user):
        self.user = user

    def get(self, user_id):
        return self.user if self.user.id == user_id else None


class _FakeDatabase:
    def __init__(self, user):
        self.user = user

    def query(self, _model):
        return _FakeQuery(self.user)


def _test_user():
    return User(
        id=42,
        username="cookie-user",
        email="cookie@example.com",
        hashed_password="unused",
        is_active=True,
        is_superuser=False,
        created_at=datetime.now(),
    )


def _protected_client():
    user = _test_user()
    test_app = FastAPI()

    @test_app.get("/protected")
    async def protected(current_user=Depends(get_current_user)):
        return {"id": current_user.id}

    def override_db():
        yield _FakeDatabase(user)

    test_app.dependency_overrides[get_db] = override_db
    return TestClient(test_app), user


def test_cookie_authentication_is_supported():
    client, user = _protected_client()
    client.cookies.set(settings.AUTH_COOKIE_NAME, create_token({"sub": str(user.id)}))

    response = client.get("/protected")

    assert response.status_code == 200
    assert response.json() == {"id": user.id}


def test_bearer_authentication_is_still_supported():
    client, user = _protected_client()
    token = create_token({"sub": str(user.id)})

    response = client.get("/protected", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json() == {"id": user.id}


def test_missing_authentication_returns_401():
    client, _user = _protected_client()

    response = client.get("/protected")

    assert response.status_code == 401
