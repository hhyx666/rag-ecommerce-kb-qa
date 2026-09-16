"""RAG 问答链路测试:登录 → 建会话 → 流式问答 → 打印引用和答案

用法: D:/venvs/langchain-project/Scripts/python.exe tools/test_chat.py
首次运行大模型要加载进显存,较慢,耐心等待。
"""
import json
import sys

import httpx

BASE = "http://127.0.0.1:8001"


def ask(client, headers, session_id, question):
    print(f"\n{'=' * 60}\n用户: {question}\n{'=' * 60}")
    full = []
    with client.stream(
        "POST",
        "/api/chat",
        json={"session_id": session_id, "question": question},
        headers=headers,
        timeout=600,
    ) as r:
        event = None
        for line in r.iter_lines():
            if line.startswith("event: "):
                event = line[len("event: "):]
            elif line.startswith("data: "):
                data = line[len("data: "):]
                if event == "citations":
                    print("\n--- 检索到的引用片段 ---")
                    for c in json.loads(data):
                        print(f"[{c['index']}] 来源: {c['source']} (得分{c['score']})")
                        print(f"    内容: {c['content'][:120]}...")
                elif event == "delta":
                    print(data, end="", flush=True)
                    full.append(data)
                elif event == "error":
                    print(f"\n[错误] {data}")
    print(f"\n\n--- 完整回答 {len(''.join(full))} 字 ---")


def main():
    client = httpx.Client(base_url=BASE, timeout=600)

    # 用普通用户测试
    r = client.post(
        "/api/auth/login", json={"username": "xiaoming", "password": "newpass123"}
    )
    if r.status_code != 200:
        r = client.post(
            "/api/auth/register",
            json={"username": "xiaoming", "password": "newpass123"},
        )
    token = r.json()["token"]
    H = {"Authorization": f"Bearer {token}"}

    # 新建会话
    r = client.post("/api/sessions", headers=H)
    session_id = r.json()["id"]
    print(f"会话已创建: id={session_id}")

    # 测试问题
    questions = [
        "星云X1 Pro手机多少钱?有什么亮点?",
        "空调安装收费吗?",
    ]
    for q in questions:
        ask(client, H, session_id, q)

    # 验证历史消息已持久化
    r = client.get(f"/api/sessions/{session_id}/messages", headers=H)
    msgs = r.json()
    print(f"\n会话历史共 {len(msgs)} 条消息(下次登录也能看到)")


if __name__ == "__main__":
    main()
