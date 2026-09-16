"""全局配置:从环境变量 / .env 文件读取"""
import os
from pathlib import Path

from dotenv import load_dotenv

# 项目根目录 = backend 的上一级
BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

# ===== 存储位置(用户要求:除硬性要求外一律放 D 盘)=====
# 模型文件:Ollama 大模型、HuggingFace 嵌入/重排模型
AI_MODELS_DIR = Path(os.getenv("AI_MODELS_DIR", "D:/AIModels"))
os.environ.setdefault("HF_HOME", str(AI_MODELS_DIR / "huggingface"))
os.environ.setdefault("HUGGINGFACE_HUB_CACHE", str(AI_MODELS_DIR / "huggingface" / "hub"))
os.environ.setdefault("TRANSFORMERS_CACHE", str(AI_MODELS_DIR / "huggingface" / "transformers"))

# 国内访问 HuggingFace 慢,统一走镜像下载模型
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

# 项目运行数据:数据库、向量库、上传文件
DATA_DIR = Path(os.getenv("DATA_DIR", "D:/langchain-data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR = DATA_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'app.db'}")
CHROMA_DIR = str(DATA_DIR / "chroma")

# JWT 安全配置
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "10080"))  # 7 天

# 预置管理员(第一次启动时自动创建)
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "123456")

# 大模型: local = 本地 Ollama(免费) / api = DeepSeek API(花钱)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "local")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:32b")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"

# 嵌入 / 重排模型(本地 HuggingFace 模型,下载到 D 盘)
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
RERANK_MODEL = os.getenv("RERANK_MODEL", "BAAI/bge-reranker-v2-m3")

# 检索参数
CANDIDATE_K = int(os.getenv("CANDIDATE_K", "20"))   # 粗排候选数量
RETRIEVE_TOP_K = int(os.getenv("RETRIEVE_TOP_K", "4"))  # 最终送给大模型的片段数
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))        # 切片字符数
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))   # 切片重叠字符数
# 相关度阈值:最高分低于这个值说明问题与知识库无关(闲聊/自我介绍),不塞资料直接回答
RELEVANCE_THRESHOLD = float(os.getenv("RELEVANCE_THRESHOLD", "0.35"))
