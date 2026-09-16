"""用户接口:注册 / 登录 / 修改密码"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import create_token, get_current_user, hash_password, verify_password
from ..database import get_db

router = APIRouter(prefix="/api/auth", tags=["用户"])


@router.post("/register", response_model=schemas.TokenOut)
def register(data: schemas.RegisterIn, db: Session = Depends(get_db)):
    """注册新账号,注册成功直接返回登录令牌"""
    if db.query(models.User).filter(models.User.username == data.username).first():
        raise HTTPException(400, "用户名已存在")
    user = models.User(
        username=data.username,
        password_hash=hash_password(data.password),
        role="user",  # 注册的账号一律是普通用户,管理员只能预置
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return schemas.TokenOut(token=create_token(user.id, user.role), user=user)


@router.post("/login", response_model=schemas.TokenOut)
def login(data: schemas.LoginIn, db: Session = Depends(get_db)):
    """登录:校验用户名密码,成功返回令牌"""
    user = db.query(models.User).filter(models.User.username == data.username).first()
    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "用户名或密码错误")
    return schemas.TokenOut(token=create_token(user.id, user.role), user=user)


@router.get("/me", response_model=schemas.UserOut)
def me(user: models.User = Depends(get_current_user)):
    """查询当前登录用户信息"""
    return user


@router.post("/change-password")
def change_password(
    data: schemas.PasswordChangeIn,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """修改密码:必须先验证旧密码"""
    if not verify_password(data.old_password, user.password_hash):
        raise HTTPException(400, "原密码错误")
    user.password_hash = hash_password(data.new_password)
    db.commit()
    return {"message": "密码修改成功"}
