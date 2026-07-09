from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.core.security import get_current_user
from app.database.session import get_db
from app.entity.schemas import UserLogin, UserRegister, UserResponse, TokenResponse
from app.services.user_service import user_service

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(request: UserRegister, db: Session = Depends(get_db)):
    """
    用户注册
      - **username**: 用户名（3-50 字符）
      - **email**: 邮箱
      - **password**: 密码（至少 6 位）
    """
    try:
        user = user_service.register(
            db=db,
            username=request.username,
            email=request.email,
            password=request.password,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return user


@router.post("/login", response_model=TokenResponse)
async def login(request: UserLogin, db: Session = Depends(get_db)):
    """
    用户登录
        - 设置 HttpOnly cookie 存储 JWT token
        - 同时返回 access_token 用于兼容
    """
    try:
        user = user_service.login(
            db=db,
            username=request.username,
            password=request.password,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = user_service.create_access_token_for_user(user)
    roles = user_service.get_user_roles(db, user)

    response_data = {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "avatar": user.avatar,
            "roles": roles,
        },
    }

    response = JSONResponse(content=response_data)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=30 * 60,
        path="/",
    )
    return response


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user=Depends(get_current_user),
    db=Depends(get_db),
):
    """获取当前登录用户信息（需要 Token 认证）"""
    roles = user_service.get_user_roles(db, current_user)
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "phone": current_user.phone,
        "avatar": current_user.avatar,
        "is_active": current_user.is_active,
        "is_superuser": current_user.is_superuser,
        "roles": roles,
        "last_login_at": current_user.last_login_at,
        "created_at": current_user.created_at,
    }


@router.post("/logout")
async def logout():
    """登出 - 清除 HttpOnly cookie"""
    response = JSONResponse(content={"message": "已登出"})
    response.delete_cookie(key="access_token", path="/")
    return response