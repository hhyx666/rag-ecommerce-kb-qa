"""文档解析:把上传的 PDF / Word / Excel / TXT / Markdown 转成纯文本"""
from pathlib import Path

import pandas as pd

SUPPORTED_EXTS = {".pdf", ".docx", ".xlsx", ".txt", ".md"}


def extract_text(file_path: Path) -> str:
    """根据文件后缀选择对应的解析器,返回全文文本"""
    ext = file_path.suffix.lower()
    if ext == ".pdf":
        import fitz  # pymupdf

        doc = fitz.open(file_path)
        parts = [page.get_text() for page in doc]
        doc.close()
        return "\n".join(parts)
    if ext == ".docx":
        from docx import Document

        doc = Document(str(file_path))
        return "\n".join(p.text for p in doc.paragraphs)
    if ext == ".xlsx":
        # 表格转文本:每行拼成 "列名: 值" 的形式,方便后续检索
        sheets = pd.read_excel(file_path, sheet_name=None)
        parts = []
        for name, df in sheets.items():
            parts.append(f"# 工作表: {name}")
            for _, row in df.iterrows():
                cells = [
                    f"{col}: {row[col]}" for col in df.columns if pd.notna(row[col])
                ]
                parts.append(", ".join(cells))
        return "\n".join(parts)
    if ext in {".txt", ".md"}:
        # 中文文件可能是 GBK 编码,先按常见编码挨个试
        for enc in ("utf-8", "gbk"):
            try:
                return file_path.read_text(encoding=enc)
            except UnicodeDecodeError:
                continue
        return file_path.read_text(encoding="utf-8", errors="ignore")
    raise ValueError(f"不支持的文件类型: {ext}")
