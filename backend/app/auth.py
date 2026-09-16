"""用户认证:JWT 令牌 + bcrypt 密码加密"""
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from . import models
from .config import JWT_ALGORITHM, JWT_EXPIRE_MINUTES, SECRET_KEY
from .database import get_db

# 前端在请求头里带 Authorization: Bearer <token>
bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    """密码单向加密,数据库里只存密文,泄露了也看不出原密码"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """校验密码是否正确"""
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_token(user_id: int, role: str) -> str:
    """生成登录令牌(有效期默认 7 天)"""
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """解析令牌;无效或过期会抛异常"""
    return jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    """FastAPI 依赖:从请求头解析当前登录用户,未登录返回 401"""
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "未登录")
    try:
        payload = decode_token(credentials.credentials)
        user_id = int(payload["sub"])
    except Exception:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "登录已过期,请重新登录")
    user = db.get(models.User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "用户不存在")
    return user


def require_admin(user: models.User = Depends(get_current_user)) -> models.User:
    """FastAPI 依赖:只有 admin 能通过,知识库管理接口用它"""
    if user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "只有管理员可以操作")
    return user
