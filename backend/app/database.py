"""数据库连接(SQLAlchemy)"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import DATABASE_URL

# SQLite 需要 check_same_thread=False 才能在 FastAPI 多线程下正常用
connect_args = (
    {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """所有数据表模型的基类"""
    pass


def get_db():
    """FastAPI 依赖:每个请求拿一个独立数据库会话,用完自动关闭"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
