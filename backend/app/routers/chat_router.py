"""问答接口:SSE 流式返回答案(打字机效果)"""
import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import get_current_user
from ..config import RELEVANCE_THRESHOLD
from ..database import get_db
from ..rag.pipeline import generate_stream, get_history_text
from ..rag.retriever import retrieve

router = APIRouter(prefix="/api/chat", tags=["问答"])


@router.post("")
async def chat(
    req: schemas.ChatRequest,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """发起一次问答,以 SSE 流式返回"""
    session = db.get(models.ChatSession, req.session_id)
    if session is None or session.user_id != user.id:
        raise HTTPException(404, "会话不存在")

    # 先取历史对话(不含本次提问),再保存本次提问
    history_text = get_history_text(db, session.id)
    db.add(models.Message(session_id=session.id, role="user", content=req.question))
    db.commit()

    # 检索知识库(目前系统只有一个默认知识库,取第一个)
    kb = db.query(models.KnowledgeBase).order_by(models.KnowledgeBase.id).first()
    contexts = retrieve(kb.id, req.question, db) if kb else []
    # 相关度过滤:最高分都低于阈值,说明是闲聊/自我介绍类问题,
    # 不塞资料让模型自由回答(比如"你是什么大模型")
    if contexts and contexts[0]["score"] < RELEVANCE_THRESHOLD:
        contexts = []
    # 注意:取不到片段时 contexts 为空,提示词里会让模型如实告知用户

    # 第一条问题作为会话标题
    if session.title == "新会话":
        session.title = req.question[:30]
        db.commit()

    async def event_stream():
        full: list[str] = []
        citations = None
        async for ev in generate_stream(req.question, contexts, history_text):
            if ev["type"] == "citations":
                citations = ev["data"]
                yield f"event: citations\ndata: {json.dumps(ev['data'], ensure_ascii=False)}\n\n"
            elif ev["type"] == "delta":
                full.append(ev["data"])
                yield f"event: delta\ndata: {json.dumps(ev['data'], ensure_ascii=False)}\n\n"
            elif ev["type"] == "error":
                full.append(ev["data"])
                yield f"event: error\ndata: {json.dumps(ev['data'], ensure_ascii=False)}\n\n"
            elif ev["type"] == "done":
                yield "event: done\ndata: {}\n\n"
        # 保存回答(含引用),下次登录也能看到
        db.add(
            models.Message(
                session_id=session.id,
                role="assistant",
                content="".join(full) or "回答生成失败,请重试",
                citations=citations,
            )
        )
        db.commit()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
