"""文档切片:把长文档切成小片段(约 500 字一片,片与片重叠 50 字)"""
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ..config import CHUNK_OVERLAP, CHUNK_SIZE


def split_text(text: str) -> list[str]:
    """按段落/句子的自然边界切,尽量不把一句话劈成两半"""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", "。", "!", "?", "!", "?", ";", " "],
    )
    return [c.strip() for c in splitter.split_text(text) if c.strip()]
