"""后端接口冒烟测试:登录 → 建库 → 上传多格式文档 → 文档列表

用法: D:/venvs/langchain-project/Scripts/python.exe tools/test_api.py
"""
import json
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8001"
DOCS_DIR = Path("D:/langchain-data/mock-docs")


def p(name, obj):
    text = json.dumps(obj, ensure_ascii=False, indent=2)
    print(f"\n=== {name} ===\n{text[:400]}")


def main():
    client = httpx.Client(base_url=BASE, timeout=600)

    # 1. admin 登录
    r = client.post("/api/auth/login", json={"username": "admin", "password": "123456"})
    assert r.status_code == 200, f"admin登录失败: {r.text}"
    admin_token = r.json()["token"]
    p("admin 登录", r.json()["user"])
    H = {"Authorization": f"Bearer {admin_token}"}

    # 2. 创建知识库(已存在就复用)
    r = client.get("/api/kb", headers=H)
    kbs = r.json()
    if not kbs:
        r = client.post(
            "/api/kb",
            json={"name": "电商商品知识库", "description": "模拟电商商品资料,用于毕设演示"},
            headers=H,
        )
        print("创建知识库:", r.status_code, r.text[:100])
        kb_id = r.json()["id"]
    else:
        kb_id = kbs[0]["id"]
        print(f"知识库已存在,复用 id={kb_id},现有文档 {len(kbs[0].get('documents', []))} 个")

    # 3. 上传 4 种格式各一份,验证解析器
    test_files = [
        "星云 X1 Pro-详情.md",
        "手机参数对比表.xlsx",
        "凉夏空调安装与保养手册.pdf",
        "声动Buds Pro 2使用指南.docx",
    ]
    for fname in test_files:
        path = DOCS_DIR / fname
        with open(path, "rb") as f:
            r = client.post(f"/api/kb/{kb_id}/upload", headers=H, files={"file": (fname, f)})
        if r.status_code == 200:
            d = r.json()
            print(f"上传 {fname}: 状态={d['status']}, 切片数={d['chunk_count']}")
        else:
            print(f"上传 {fname}: 失败 {r.status_code} {r.text[:200]}")

    # 4. 文档列表
    r = client.get(f"/api/kb/{kb_id}/documents", headers=H)
    p("文档列表", r.json()[:5])

    # 5. 看第一个文档的切片预览(验证切片质量)
    r = client.get(f"/api/kb/{kb_id}/documents", headers=H)
    docs = r.json()
    if docs:
        r = client.get(f"/api/kb/documents/{docs[0]['id']}/chunks", headers=H)
        chunks = r.json()
        p(f"切片预览(文档: {docs[0]['filename']}, 共{len(chunks)}片)", chunks[0])


if __name__ == "__main__":
    main()
