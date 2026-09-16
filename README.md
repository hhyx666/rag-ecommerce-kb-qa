# RAG 电商知识库问答系统

基于 LangChain 的企业级 RAG(检索增强生成)知识库问答系统 · 毕业设计项目

## 快速开始

双击项目根目录的 **《一键启动.bat》**,自动启动大模型服务、后端、前端,并打开浏览器。

- 前端页面: http://localhost:5173
- 后端接口文档: http://localhost:8001/docs
- 管理员账号: admin / 123456
- 普通用户: 在登录页自行注册

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | Vue 3 + Element Plus + Vite + Pinia |
| 后端 | FastAPI + SQLAlchemy + SQLite |
| AI 框架 | LangChain 1.x |
| 大模型 | 本地 Ollama + Qwen3 32B(离线免费,可切 DeepSeek API) |
| 嵌入模型 | bge-m3(本地) |
| 重排模型 | bge-reranker-v2-m3(本地) |
| 向量数据库 | Chroma |
| 检索策略 | BM25 关键词 + 向量语义混合检索,RRF 融合 + 重排序 |
| 认证 | JWT + bcrypt |

## 核心功能

1. 浏览器知识库管理(仅管理员):上传 PDF/Word/Excel/TXT/Markdown,自动解析、切片、向量化
2. 知识库问答:回答引用知识库片段,展示引用来源和相关度
3. 多用户独立会话管理
4. 会话持久化:重新登录可找回历史对话
5. 注册 / 登录 / 修改密码
6. 管理员检索调试:查看检索命中片段和得分

## 目录结构

```
langchain项目/
├── 一键启动.bat           # 一键启动脚本
├── 方案计划.md            # 毕设方案文档
├── backend/               # 后端(FastAPI + LangChain)
│   └── app/
│       ├── main.py        # 入口
│       ├── config.py      # 配置(.env 可覆盖)
│       ├── models.py      # 数据表(用户/会话/消息/知识库/文档/切片)
│       ├── auth.py        # JWT + bcrypt
│       ├── routers/       # 接口:auth / sessions / chat / kb
│       └── rag/           # RAG 核心:loader / splitter / embeddings / retriever / generator / pipeline
├── frontend/              # 前端(Vue 3 + Element Plus)
│   └── src/
│       ├── views/         # Login / ChatView / AdminKbView / ProfileView
│       ├── router/        # 路由 + 登录/管理员守卫
│       └── stores/        # 登录状态
└── tools/                 # 工具脚本
    ├── generate_mock_data.py   # 生成 52 份模拟电商文档
    ├── upload_all.py           # 批量上传文档入库
    ├── test_api.py             # 接口冒烟测试
    └── test_chat.py            # RAG 问答链路测试
```

## 数据存储位置(D 盘)

- 模型文件: `D:\AIModels\(Ollama 大模型、HuggingFace 嵌入/重排模型)`
- 项目数据: `D:\langchain-data\(SQLite 数据库、Chroma 向量库、上传文档)`
- Python 环境: `D:\venvs\langchain-project`
