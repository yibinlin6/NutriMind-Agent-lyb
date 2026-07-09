from datetime import datetime
from sqlalchemy.orm import Session
from app.entity.db_models import User, UserRole, Role
from app.core.security import hash_password, verify_password, create_token
class UserService:
    def register(self, db: Session, username: str, email: str, password: str) -> User:
        """⽤户注册"""
        # 检查⽤户名是否已存在
        existing_user = db.query(User).filter(User.username == username).first()
        if existing_user:
            raise ValueError("⽤户名已存在")
        
        # 检查邮箱是否已存在
        existing_email = db.query(User).filter(User.email == email).first()
        if existing_email:
            raise ValueError("邮箱已被注册")
        
        # 创建⽤户
        user = User(
            username=username,
            email=email,
            hashed_password=hash_password(password),
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        return user
    
    def login(self, db: Session, username: str, password: str) -> User:
        """⽤户登录"""
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise ValueError("⽤户名或密码错误")
         
        if not verify_password(password, user.hashed_password):
            raise ValueError("⽤户名或密码错误")
        
        if not user.is_active:
            raise ValueError("账户已被禁⽤")
        
        # 更新最后登录时间
        user.last_login_at = datetime.now()
        db.commit()
        
        return user
    
    def create_access_token_for_user(self, user: User) -> str:
        """为⽤户创建 JWT Token"""
        return create_token({"sub": str(user.id)})
    
    def get_user_roles(self, db: Session, user: User) -> list:
        """获取⽤户⻆⾊列表"""
        user_roles = db.query(UserRole).filter(UserRole.user_id == user.id).all()
        roles = []
        for ur in user_roles:
            role = db.query(Role).get(ur.role_id)
            if role:
                roles.append(role.name)
        return roles
# 全局单例
user_service = UserService()