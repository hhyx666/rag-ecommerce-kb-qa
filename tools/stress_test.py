"""压力测试脚本:测量 RAG 知识库问答系统在不同并发用户数下的极限

测试四个层面(由轻到重):
  1. 用户登录     —— 密码加密(bcrypt)是 CPU 密集操作
  2. 会话列表查询 —— 数据库读取能力
  3. 知识库检索   —— 嵌入向量 + 重排序模型(CPU)—— 不含大模型
  4. 完整智能问答 —— 检索 + 大模型流式生成 —— 系统真正的瓶颈

用法:
  D:/venvs/langchain-project/Scripts/python.exe tools/stress_test.py
  参数: --quick 只跑小并发轮次(快速版)
"""
import asyncio
import json
import statistics
import sys
import time

import httpx

BASE = "http://127.0.0.1:8001"
TEST_USER = "stresstest"
TEST_PASS = "stresstest123"

QUICK = "--quick" in sys.argv
WORKER_TIMEOUT = 300  # 单个请求最长等待秒数,超时算失败(防止整个测试卡死)

from pathlib import Path

RESULT_FILE = Path("D:/langchain-data/stress-results.txt")


def log(text):
    """打印并立即写入结果文件(即使中途被打断,已有结果也不会丢)"""
    print(text, flush=True)
    try:
        RESULT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(RESULT_FILE, "a", encoding="utf-8") as f:
            f.write(text + "\n")
    except Exception:
        pass


def pct(values, p):
    """百分位数(如 P95 延迟)"""
    if not values:
        return 0.0
    values = sorted(values)
    idx = min(int(len(values) * p / 100), len(values) - 1)
    return values[idx]


class Stats:
    """收集一轮测试的结果"""

    def __init__(self, name, concurrency):
        self.name = name
        self.concurrency = concurrency
        self.latencies = []
        self.errors = []
        self.ttfts = []      # 首字延迟(仅问答测试有)
        self.char_counts = []

    @property
    def ok(self):
        return len(self.latencies)

    @property
    def success_rate(self):
        total = self.ok + len(self.errors)
        return self.ok / total * 100 if total else 0.0

    def report(self):
        if not self.latencies:
            return (f"  {self.name:<12} 并发{self.concurrency:>4} | "
                    f"全部失败({len(self.errors)}个错误)")
        line = (
            f"  {self.name:<12} 并发{self.concurrency:>4} | "
            f"成功 {self.ok:>3} | 成功率 {self.success_rate:5.1f}% | "
            f"平均 {statistics.mean(self.latencies):6.2f}s | "
            f"P95 {pct(self.latencies, 95):6.2f}s | "
            f"最慢 {max(self.latencies):6.2f}s"
        )
        if self.ttfts:
            line += f" | 首字均值 {statistics.mean(self.ttfts):5.2f}s"
        return line


# ============================================================
# 通用并发执行器
# ============================================================
async def run_concurrent(stats: Stats, worker):
    """同时发起 concurrency 个 worker 协程,收集成功/失败"""

    async def wrapped(i):
        t0 = time.perf_counter()
        try:
            # 超时保护:单个请求卡住超过 WORKER_TIMEOUT 秒就放弃,算作失败
            result = await asyncio.wait_for(worker(i), timeout=WORKER_TIMEOUT)
            stats.latencies.append(time.perf_counter() - t0)
            if isinstance(result, dict):
                if result.get("ttft") is not None:
                    stats.ttfts.append(result["ttft"])
                if result.get("chars"):
                    stats.char_counts.append(result["chars"])
        except asyncio.TimeoutError:
            stats.errors.append(f"超时(>{WORKER_TIMEOUT}s)")
        except Exception as e:
            stats.errors.append(f"{type(e).__name__}: {str(e)[:80]}")

    await asyncio.gather(*[wrapped(i) for i in range(stats.concurrency)])


# ============================================================
# 准备:注册测试用户 / 拿管理员令牌 / 建会话
# ============================================================
async def prepare(client: httpx.AsyncClient):
    # 测试用户(已存在就直接登录)
    r = await client.post(f"{BASE}/api/auth/register",
                          json={"username": TEST_USER, "password": TEST_PASS})
    if r.status_code == 400:
        r = await client.post(f"{BASE}/api/auth/login",
                              json={"username": TEST_USER, "password": TEST_PASS})
    assert r.status_code == 200, f"测试用户准备失败: {r.text}"
    user_token = r.json()["token"]
    user_h = {"Authorization": f"Bearer {user_token}"}

    # 管理员(检索测试用)
    r = await client.post(f"{BASE}/api/auth/login",
                          json={"username": "admin", "password": "123456"})
    assert r.status_code == 200, "管理员登录失败"
    admin_h = {"Authorization": f"Bearer {r.json()['token']}"}

    # 知识库
    r = await client.get(f"{BASE}/api/kb", headers=admin_h)
    kbs = r.json()
    assert kbs, "没有知识库,请先创建并上传文档"
    kb_id = kbs[0]["id"]

    return user_h, admin_h, kb_id


# ============================================================
# 场景 1:并发登录(bcrypt 密码校验,CPU 密集)
# ============================================================
async def test_login(client, concurrency):
    stats = Stats("登录", concurrency)

    async def worker(i):
        r = await client.post(f"{BASE}/api/auth/login",
                              json={"username": TEST_USER, "password": TEST_PASS})
        r.raise_for_status()

    await run_concurrent(stats, worker)
    return stats


# ============================================================
# 场景 2:并发查询会话列表(数据库读取)
# ============================================================
async def test_session_list(client, user_h, concurrency):
    stats = Stats("会话查询", concurrency)

    async def worker(i):
        r = await client.get(f"{BASE}/api/sessions", headers=user_h)
        r.raise_for_status()

    await run_concurrent(stats, worker)
    return stats


# ============================================================
# 场景 3:并发检索(嵌入+重排,不含大模型)
# ============================================================
async def test_retrieval(client, admin_h, kb_id, concurrency):
    stats = Stats("知识库检索", concurrency)
    questions = ["身高175体重70穿什么码", "脚长26厘米买多大鞋", "羽绒服怎么选码",
                 "牛仔裤腰围怎么换算", "衬衫领围怎么量"]

    async def worker(i):
        r = await client.post(f"{BASE}/api/kb/{kb_id}/debug-search",
                              json={"query": questions[i % len(questions)]},
                              headers=admin_h, timeout=120)
        r.raise_for_status()

    await run_concurrent(stats, worker)
    return stats


# ============================================================
# 场景 4:并发完整问答(检索 + 大模型生成)—— 系统真正瓶颈
# ============================================================
async def test_chat(client, user_h, concurrency, session_ids):
    stats = Stats("完整问答", concurrency)

    async def worker(i):
        t0 = time.perf_counter()
        ttft = None
        text = ""
        async with client.stream(
            "POST", f"{BASE}/api/chat",
            json={"session_id": session_ids[i], "question": "身高175体重70穿什么码?一句话回答"},
            headers=user_h, timeout=600,
        ) as r:
            r.raise_for_status()
            event = None
            async for line in r.aiter_lines():
                if line.startswith("event: "):
                    event = line[7:].strip()
                elif line.startswith("data: "):
                    if event == "delta":
                        if ttft is None:
                            ttft = time.perf_counter() - t0
                        try:
                            text += json.loads(line[6:])
                        except Exception:
                            pass
        return {"ttft": ttft, "chars": len(text)}

    await run_concurrent(stats, worker)
    return stats


# ============================================================
# 主流程
# ============================================================
async def main():
    log("\n" + "=" * 78)
    log(f"  RAG 知识库问答系统 · 并发压力测试   {time.strftime('%Y-%m-%d %H:%M:%S')}")
    log("=" * 78)

    # 先确认后端活着
    async with httpx.AsyncClient(timeout=30) as c:
        try:
            r = await c.get(f"{BASE}/api/health")
            assert r.status_code == 200
        except Exception:
            print("  [错误] 后端没在运行!请先启动后端(端口8001)")
            return

    async with httpx.AsyncClient(timeout=600) as client:
        user_h, admin_h, kb_id = await prepare(client)
        print(f"  准备就绪: 测试用户 {TEST_USER} | 知识库 id={kb_id}\n")

        # 给问答测试准备独立会话(每个并发请求一个会话,避免相互干扰)
        session_ids = []
        for _ in range(16):
            r = await client.post(f"{BASE}/api/sessions", headers=user_h)
            session_ids.append(r.json()["id"])

        all_stats = []
        levels = [1, 5, 20] if QUICK else [1, 5, 20, 50, 100]

        # ---------- 场景 1:登录 ----------
        print("【1/4】并发登录(密码校验,CPU 密集)")
        for n in levels:
            s = await test_login(client, n)
            log(s.report())
            all_stats.append(s)

        # ---------- 场景 2:会话查询 ----------
        log("\n【2/4】并发会话列表查询(数据库读取)")
        for n in levels:
            s = await test_session_list(client, user_h, n)
            log(s.report())
            all_stats.append(s)

        # ---------- 场景 3:知识库检索 ----------
        log("\n【3/4】并发知识库检索(嵌入 + 重排,不含大模型)")
        for n in [1, 2, 4] if QUICK else [1, 2, 4, 8]:
            s = await test_retrieval(client, admin_h, kb_id, n)
            log(s.report())
            all_stats.append(s)

        # ---------- 场景 4:完整问答 ----------
        log("\n【4/4】并发完整智能问答(检索 + 大模型生成,系统真正瓶颈)")
        print("      (每个回答约需 15~40 秒,请耐心等待...)\n")
        chat_levels = [1, 2] if QUICK else [1, 2, 4, 6, 8]
        for n in chat_levels:
            s = await test_chat(client, user_h, n, session_ids)
            log(s.report())
            all_stats.append(s)

    # ---------- 汇总 ----------
    log("\n" + "=" * 78)
    log("  测试结论")
    log("=" * 78)

    # 找各场景的可靠并发上限(成功率95%以上且P95<30秒)
    def find_limit(name, threshold=30.0):
        best = 0
        for s in all_stats:
            if s.name == name and s.success_rate >= 95 and pct(s.latencies, 95) <= threshold:
                best = max(best, s.concurrency)
        return best

    log(f"  登录接口:      稳定支持 {find_limit('登录')} 人同时登录")
    log(f"  会话查询:      稳定支持 {find_limit('会话查询')} 人同时使用")
    log(f"  知识库检索:    稳定支持 {find_limit('知识库检索')} 人同时检索")
    log(f"  完整智能问答:  稳定支持 {find_limit('完整问答', 120.0)} 人同时问答")
    log("")
    log("  说明: 完整问答的瓶颈是大模型生成速度(本地单卡推理),")
    log("        并发请求会排队,人数越多每个用户等待越久。")


if __name__ == "__main__":
    asyncio.run(main())
