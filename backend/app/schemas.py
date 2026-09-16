"""接口的请求/响应格式定义(Pydantic 自动校验输入)"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# ---------- 用户 ----------
class RegisterIn(BaseModel):
    username: str = Field(min_length=2, max_length=50)
    password: str = Field(min_length=6, max_length=50)


class LoginIn(BaseModel):
    username: str
    password: str


class PasswordChangeIn(BaseModel):
    old_password: str
    new_password: str = Field(min_length=6, max_length=50)


class UserOut(BaseModel):
    id: int
    username: str
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


class TokenOut(BaseModel):
    token: str
    user: UserOut


# ---------- 知识库 ----------
class KnowledgeBaseIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = ""


class KnowledgeBaseOut(BaseModel):
    id: int
    name: str
    description: str
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentOut(BaseModel):
    id: int
    filename: str
    status: str
    chunk_count: int
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- 会话 ----------
class SessionRenameIn(BaseModel):
    title: str = Field(min_length=1, max_length=100)


class ChatSessionOut(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    citations: Optional[list] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- 问答 ----------
class ChatRequest(BaseModel):
    session_id: int
    question: str = Field(min_length=1, max_length=2000)


class Citation(BaseModel):
    """引用片段:回答中 [1][2] 编号对应的知识库原文"""
    index: int
    content: str
    source: str  # 文档名
    score: float  # 相关度得分


class DebugSearchIn(BaseModel):
    query: str = Field(min_length=1)
