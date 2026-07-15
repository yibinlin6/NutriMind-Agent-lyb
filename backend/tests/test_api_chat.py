from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.core.security import get_current_user
from app.entity.db_models import User
from main import app


def _mock_user():
    return User(id=7, username="agent-user", email="agent@example.com", is_active=True)


def test_chat_message_passes_detection_context():
    app.dependency_overrides[get_current_user] = _mock_user
    agent_result = {
        "response": "这餐约含 250 kcal。",
        "tool_calls": [{"name": "query_food_calories", "args": {"food_name": "apple"}}],
        "analysis_result": None,
    }
    try:
        with patch("app.api.chat.run_agent", new=AsyncMock(return_value=agent_result)) as mocked:
            response = TestClient(app).post(
                "/api/chat/message",
                json={
                    "session_id": "meal-001",
                    "message": "分析一下",
                    "detections": [{
                        "class_name": "apple",
                        "class_name_cn": "苹果",
                        "confidence": 0.95,
                        "bbox": [10, 20, 200, 300],
                    }],
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["session_id"] == "meal-001"
    assert response.json()["tool_calls"][0]["name"] == "query_food_calories"
    assert mocked.await_args.kwargs["session_id"] == "user:7:meal-001"
    assert mocked.await_args.kwargs["detections"][0]["class_name"] == "apple"


def test_chat_rejects_empty_request():
    app.dependency_overrides[get_current_user] = _mock_user
    try:
        response = TestClient(app).post("/api/chat/message", json={})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


def test_chat_generates_session_id():
    app.dependency_overrides[get_current_user] = _mock_user
    try:
        with patch(
            "app.api.chat.run_agent",
            new=AsyncMock(return_value={"response": "你好", "tool_calls": [], "analysis_result": None}),
        ):
            response = TestClient(app).post(
                "/api/chat/message",
                json={"message": "你好"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["session_id"]
