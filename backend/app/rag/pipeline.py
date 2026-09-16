"""RAG 问答完整链路:检索 → 拼提示词 → 流式生成"""
from typing import AsyncIterator

from sqlalchemy.orm import Session

from .. import models
from .generator import build_messages, get_llm

MAX_HISTORY = 6  # 带最近 6 条对话,让模型记得上下文


def get_history_text(db: Session, session_id: int) -> str:
    """取会话最近几条消息,拼成对话文本"""
    msgs = (
        db.query(models.Message)
        .filter(models.Message.session_id == session_id)
        .order_by(models.Message.id.desc())
        .limit(MAX_HISTORY)
        .all()
    )
    lines = [
        f"{'用户' if m.role == 'user' else '客服'}: {m.content}"
        for m in reversed(msgs)
    ]
    return "\n".join(lines)


async def generate_stream(
    question: str, contexts: list[dict], history_text: str
) -> AsyncIterator[dict]:
    """流式生成答案。

    依次发出事件:
    - {"type": "citations", "data": [...]}   引用片段(前端先展示)
    - {"type": "delta", "data": "文字"}      答案增量(打字机效果)
    - {"type": "error", "data": "错误信息"}  生成出错时
    - {"type": "done", "data": "全文"}       结束(全文用于存库)
    """
    citations = [
        {
            "index": i + 1,
            "content": c["content"],
            "source": c["source"],
            "score": c["score"],
        }
        for i, c in enumerate(contexts)
    ]
    yield {"type": "citations", "data": citations}

    messages = build_messages(question, [c["content"] for c in contexts], history_text)
    full: list[str] = []
    try:
        async for chunk in get_llm().astream(messages):
            text = chunk.content
            if text:
                full.append(text)
                yield {"type": "delta", "data": text}
    except Exception as e:
        yield {"type": "error", "data": f"大模型调用失败:{e}"}
    yield {"type": "done", "data": "".join(full)}
