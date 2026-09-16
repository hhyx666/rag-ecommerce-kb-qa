"""批量上传全部模拟文档到知识库(重复文件自动跳过)

用法: D:/venvs/langchain-project/Scripts/python.exe tools/upload_all.py [文档目录]
默认目录: D:/langchain-data/size-docs
"""
import sys
import httpx
from pathlib import Path

BASE = "http://127.0.0.1:8001"
DOCS_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("D:/langchain-data/size-docs")
EXTS = {".md", ".txt", ".xlsx", ".docx", ".pdf"}


def main():
    client = httpx.Client(base_url=BASE, timeout=600)
    r = client.post("/api/auth/login", json={"username": "admin", "password": "123456"})
    assert r.status_code == 200, f"登录失败: {r.text}"
    token = r.json()["token"]
    H = {"Authorization": f"Bearer {token}"}

    r = client.get("/api/kb", headers=H)
    assert r.json(), "没有知识库,请先创建"
    kb_id = r.json()[0]["id"]
    print(f"目标知识库: id={kb_id}")

    ok = fail = 0
    for path in sorted(DOCS_DIR.iterdir()):
        if path.suffix.lower() not in EXTS:
            continue
        with open(path, "rb") as f:
            r = client.post(
                f"/api/kb/{kb_id}/upload", headers=H, files={"file": (path.name, f)}
            )
        if r.status_code == 200:
            d = r.json()
            print(f"  [OK] {path.name} (切片{d['chunk_count']}片)")
            ok += 1
        else:
            print(f"  [FAIL] {path.name}: {r.text[:120]}")
            fail += 1

    # 统计
    r = client.get(f"/api/kb/{kb_id}/documents", headers=H)
    docs = r.json()
    total_chunks = sum(d["chunk_count"] for d in docs)
    print(f"\n上传完成: 本次成功 {ok}, 失败 {fail}")
    print(f"知识库现状: {len(docs)} 份文档, {total_chunks} 个切片")


if __name__ == "__main__":
    main()
