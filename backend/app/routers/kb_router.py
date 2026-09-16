"""知识库管理接口(仅管理员可用)"""
import hashlib
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import require_admin
from ..config import UPLOAD_DIR
from ..database import get_db
from ..rag import loader, splitter
from ..rag.retriever import get_chroma_client, get_store, invalidate_cache, retrieve

router = APIRouter(prefix="/api/kb", tags=["知识库"])


@router.get("", response_model=list[schemas.KnowledgeBaseOut])
def list_kbs(user: models.User = Depends(require_admin), db: Session = Depends(get_db)):
    """知识库列表"""
    return db.query(models.KnowledgeBase).order_by(models.KnowledgeBase.id).all()


@router.post("", response_model=schemas.KnowledgeBaseOut)
def create_kb(
    data: schemas.KnowledgeBaseIn,
    user: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """创建知识库"""
    if db.query(models.KnowledgeBase).filter_by(name=data.name).first():
        raise HTTPException(400, "知识库名称已存在")
    kb = models.KnowledgeBase(name=data.name, description=data.description)
    db.add(kb)
    db.commit()
    db.refresh(kb)
    return kb


@router.delete("/{kb_id}")
def delete_kb(
    kb_id: int, user: models.User = Depends(require_admin), db: Session = Depends(get_db)
):
    """删除知识库(连带文档、切片、向量)"""
    kb = db.get(models.KnowledgeBase, kb_id)
    if kb is None:
        raise HTTPException(404, "知识库不存在")
    get_chroma_client().delete_collection(f"kb_{kb_id}")
    db.delete(kb)
    db.commit()
    invalidate_cache(kb_id)
    return {"message": "知识库已删除"}


@router.get("/{kb_id}/documents", response_model=list[schemas.DocumentOut])
def list_documents(
    kb_id: int, user: models.User = Depends(require_admin), db: Session = Depends(get_db)
):
    """知识库内的文档列表"""
    if db.get(models.KnowledgeBase, kb_id) is None:
        raise HTTPException(404, "知识库不存在")
    return (
        db.query(models.Document)
        .filter(models.Document.kb_id == kb_id)
        .order_by(models.Document.id.desc())
        .all()
    )


@router.post("/{kb_id}/upload", response_model=schemas.DocumentOut)
async def upload_document(
    kb_id: int,
    file: UploadFile = File(...),
    user: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """上传文档:解析 → 切片 → 向量化入库(一条龙)"""
    kb = db.get(models.KnowledgeBase, kb_id)
    if kb is None:
        raise HTTPException(404, "知识库不存在")
    if (
        file.filename is None
        or Path(file.filename).suffix.lower() not in loader.SUPPORTED_EXTS
    ):
        raise HTTPException(400, "只支持 PDF / Word / Excel / TXT / Markdown 文件")

    content = await file.read()
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(400, "文件太大(超过50MB)")
    file_hash = hashlib.sha256(content).hexdigest()

    # 内容相同的文件只处理一次(嵌入缓存:不重复花钱花时间算向量)
    dup = (
        db.query(models.Document)
        .filter(models.Document.kb_id == kb_id, models.Document.file_hash == file_hash)
        .first()
    )
    if dup:
        return dup

    doc = models.Document(kb_id=kb_id, filename=file.filename, file_hash=file_hash)
    db.add(doc)
    db.commit()
    db.refresh(doc)

    save_path = None
    try:
        save_path = UPLOAD_DIR / f"{doc.id}_{file.filename}"
        save_path.write_bytes(content)

        text = loader.extract_text(save_path)
        chunk_texts = splitter.split_text(text)
        if not chunk_texts:
            raise ValueError("文档里没有可提取的文字")

        # 切片存入数据库
        for i, t in enumerate(chunk_texts):
            db.add(models.Chunk(document_id=doc.id, chunk_index=i, content=t))
        db.flush()

        # 向量化存入 Chroma
        get_store(kb_id).add_texts(
            texts=chunk_texts,
            ids=[str(c.id) for c in doc.chunks],
            metadatas=[
                {
                    "chunk_id": c.id,
                    "document_id": doc.id,
                    "kb_id": kb_id,
                    "filename": doc.filename,
                }
                for c in doc.chunks
            ],
        )
        doc.status = "ready"
        doc.chunk_count = len(chunk_texts)
        db.commit()
        invalidate_cache(kb_id)
    except Exception as e:
        db.rollback()
        if save_path is not None:
            save_path.unlink(missing_ok=True)
        doc.status = "error"
        db.commit()
        raise HTTPException(500, f"文档处理失败:{e}")
    return doc


@router.delete("/{kb_id}/documents/{doc_id}")
def delete_document(
    kb_id: int,
    doc_id: int,
    user: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """删除文档(连带切片和向量)"""
    doc = db.get(models.Document, doc_id)
    if doc is None or doc.kb_id != kb_id:
        raise HTTPException(404, "文档不存在")
    get_store(kb_id).delete(ids=[str(c.id) for c in doc.chunks])
    db.delete(doc)
    db.commit()
    invalidate_cache(kb_id)
    return {"message": "文档已删除"}


@router.get("/documents/{doc_id}/chunks")
def get_chunks(
    doc_id: int, user: models.User = Depends(require_admin), db: Session = Depends(get_db)
):
    """预览文档切片结果(验证切片质量)"""
    if db.get(models.Document, doc_id) is None:
        raise HTTPException(404, "文档不存在")
    return [
        {"index": c.chunk_index, "content": c.content}
        for c in db.query(models.Chunk)
        .filter(models.Chunk.document_id == doc_id)
        .order_by(models.Chunk.chunk_index)
        .all()
    ]


@router.post("/{kb_id}/debug-search")
def debug_search(
    kb_id: int,
    req: schemas.DebugSearchIn,
    user: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """检索调试:返回命中的片段和得分,管理员验证检索效果用"""
    if db.get(models.KnowledgeBase, kb_id) is None:
        raise HTTPException(404, "知识库不存在")
    return retrieve(kb_id, req.query, db, top_k=10)
