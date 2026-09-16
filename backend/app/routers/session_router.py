"""会话接口:会话列表 / 新建 / 重命名 / 删除 / 历史消息"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db

router = APIRouter(prefix="/api/sessions", tags=["会话"])


def _get_owned(session_id: int, user: models.User, db: Session) -> models.ChatSession:
    """取出会话并校验归属(只能操作自己的会话)"""
    session = db.get(models.ChatSession, session_id)
    if session is None or session.user_id != user.id:
        raise HTTPException(404, "会话不存在")
    return session


@router.get("", response_model=list[schemas.ChatSessionOut])
def list_sessions(
    user: models.User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """当前用户的会话列表(最近更新的排前面)"""
    return (
        db.query(models.ChatSession)
        .filter(models.ChatSession.user_id == user.id)
        .order_by(models.ChatSession.updated_at.desc())
        .all()
    )


@router.post("", response_model=schemas.ChatSessionOut)
def create_session(
    user: models.User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """新建会话"""
    session = models.ChatSession(user_id=user.id)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.patch("/{session_id}", response_model=schemas.ChatSessionOut)
def rename_session(
    session_id: int,
    req: schemas.SessionRenameIn,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """重命名会话"""
    session = _get_owned(session_id, user, db)
    session.title = req.title
    db.commit()
    return session


@router.delete("/{session_id}")
def delete_session(
    session_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除会话(连带删除其中的消息)"""
    session = _get_owned(session_id, user, db)
    db.delete(session)
    db.commit()
    return {"message": "会话已删除"}


@router.get("/{session_id}/messages", response_model=list[schemas.MessageOut])
def get_messages(
    session_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """会话历史消息(时间正序)"""
    _get_owned(session_id, user, db)
    return (
        db.query(models.Message)
        .filter(models.Message.session_id == session_id)
        .order_by(models.Message.id)
        .all()
    )
