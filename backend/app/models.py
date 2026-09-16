"""数据表模型"""
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    """用户表"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(128), nullable=False)  # 加密后的密码,绝不存明文
    role = Column(String(20), default="user", nullable=False)  # admin / user
    created_at = Column(DateTime, default=datetime.now)

    sessions = relationship(
        "ChatSession", back_populates="user", cascade="all, delete-orphan"
    )


class ChatSession(Base):
    """会话表:每个用户可有多个会话(类似聊天软件的多个聊天窗口)"""
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    title = Column(String(100), default="新会话")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    user = relationship("User", back_populates="sessions")
    messages = relationship(
        "Message", back_populates="session", cascade="all, delete-orphan"
    )


class Message(Base):
    """消息表:保存每一次提问和回答(会话持久化的关键)"""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(
        Integer, ForeignKey("chat_sessions.id"), index=True, nullable=False
    )
    role = Column(String(20), nullable=False)  # user(提问) / assistant(回答)
    content = Column(Text, nullable=False)
    citations = Column(JSON, nullable=True)  # 回答引用的知识库片段(JSON 数组)
    created_at = Column(DateTime, default=datetime.now)

    session = relationship("ChatSession", back_populates="messages")


class KnowledgeBase(Base):
    """知识库表"""
    __tablename__ = "knowledge_bases"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(String(500), default="")
    created_at = Column(DateTime, default=datetime.now)

    documents = relationship(
        "Document", back_populates="kb", cascade="all, delete-orphan"
    )


class Document(Base):
    """文档表:知识库里上传的每个文件"""
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    kb_id = Column(Integer, ForeignKey("knowledge_bases.id"), index=True, nullable=False)
    filename = Column(String(255), nullable=False)
    file_hash = Column(String(64), nullable=False)  # 内容没变就不重复嵌入
    status = Column(String(20), default="processing")  # processing / ready / error
    chunk_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)

    kb = relationship("KnowledgeBase", back_populates="documents")
    chunks = relationship(
        "Chunk", back_populates="document", cascade="all, delete-orphan"
    )


class Chunk(Base):
    """切片表:文档切出的片段(向量存 Chroma,这里存原文方便展示)"""
    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), index=True, nullable=False)
    chunk_index = Column(Integer, nullable=False)  # 在文档中的序号
    content = Column(Text, nullable=False)

    document = relationship("Document", back_populates="chunks")
