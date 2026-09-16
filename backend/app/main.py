"""程序入口:创建 FastAPI 应用,启动时自动建表 + 预置管理员"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import models
from .auth import hash_password
from .config import ADMIN_PASSWORD, ADMIN_USER
from .database import Base, SessionLocal, engine
from .routers import auth_router, chat_router, kb_router, session_router


def init_app():
    """建表 + 预置管理员账号(admin/123456)"""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        admin = (
            db.query(models.User).filter(models.User.username == ADMIN_USER).first()
        )
        if admin is None:
            db.add(
                models.User(
                    username=ADMIN_USER,
                    password_hash=hash_password(ADMIN_PASSWORD),
                    role="admin",
                )
            )
            db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_app()
    yield


app = FastAPI(
    title="RAG 电商知识库问答系统",
    description="毕设项目:基于 LangChain 的企业级知识库问答系统",
    version="1.0.0",
    lifespan=lifespan,
)

# 允许前端页面(开发时跑在别的端口)访问后端
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发期放开;答辩演示也是本机访问,无影响
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(session_router.router)
app.include_router(chat_router.router)
app.include_router(kb_router.router)


@app.get("/api/health")
def health():
    """健康检查:浏览器打开 /api/health 看到 ok 说明后端正常"""
    return {"status": "ok"}
