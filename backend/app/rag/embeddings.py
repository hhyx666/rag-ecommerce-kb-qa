"""嵌入模型:把文字转成向量(机器能比较"意思像不像"的数字指纹)

用本地 bge-m3 模型,免费、离线可用。跑在 CPU 上,
因为显卡主要留给大模型(qwen3:32b 占约 20G 显存)。
模型文件由 config.py 统一指定下载到 D 盘(D:/AIModels/huggingface)。
"""
from langchain_huggingface import HuggingFaceEmbeddings

from ..config import EMBEDDING_MODEL

_embedder = None


def get_embeddings() -> HuggingFaceEmbeddings:
    """全局只加载一次模型(加载一次要好几秒,不能每次请求都加载)"""
    global _embedder
    if _embedder is None:
        _embedder = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},  # bge-m3 官方推荐
        )
    return _embedder
