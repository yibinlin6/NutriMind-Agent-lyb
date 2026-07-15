"""NutriMind 营养智能体对话 API。"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import get_current_user
from app.entity.db_models import User
from app.entity.schemas import ChatRequest, ChatResponse
from app.services.agent_graph import run_agent

router = APIRouter(prefix="/api/chat", tags=["AI 对话"])


@router.post("/message", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
) -> ChatResponse:
    """发送消息，可同时携带 YOLO 食物检测结果并延续多轮会话。"""
    message = request.message.strip()
    if not message and not request.detections:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="消息和检测结果不能同时为空",
        )

    session_id = request.session_id or str(uuid.uuid4())
    # MemorySaver 以 thread_id 隔离历史；加入 user_id 防止不同用户复用
    # 相同 session_id 时串话。
    thread_id = f"user:{current_user.id}:{session_id}"
    result = await run_agent(
        session_id=thread_id,
        user_message=message,
        detections=[item.model_dump() for item in request.detections] or None,
        user_id=current_user.id,
    )

    return ChatResponse(
        session_id=session_id,
        response=result["response"],
        tool_calls=result.get("tool_calls", []),
        analysis_result=result.get("analysis_result"),
    )
