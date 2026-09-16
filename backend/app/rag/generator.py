"""大模型生成:默认本地 Ollama(免费),可切 DeepSeek API"""
from langchain_ollama import ChatOllama

from ..config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
    LLM_PROVIDER,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
)

SYSTEM_PROMPT = """你是"电商知识库智能客服",基于通义千问 Qwen3 大模型开发,通过 LangChain RAG 框架接入电商商品知识库,回答时优先参考知识库资料。

回答要求:
1. 涉及商品参数、价格、售后政策等问题时,必须优先使用【知识库资料】中的信息作答,不要编造资料里没有的内容
2. 只有【知识库资料】里有编号资料时,才能在句末用 [1] [2] 这样的编号标注引用;资料为空时严禁编造引用编号
3. 用户问的是与商品无关的闲聊或自我介绍(比如"你是什么模型""你是谁""你能做什么"),直接友好回答即可,不需要引用资料
4. 用户问的商品信息在资料里没有时,直接说"知识库中没有找到相关内容",不要凭记忆编造商品信息
5. 用简体中文回答,条理清晰,商品参数类问题可以用列表形式"""


def _build_context_block(contexts: list[str]) -> str:
    """把检索到的片段编上号拼进提示词"""
    if not contexts:
        return (
            "【知识库资料】\n"
            "(本次问题未检索到相关资料。判断用户意图:若是闲聊或自我介绍,直接自由回答;"
            "若是询问商品或平台信息,请回答\"知识库中没有找到相关内容\","
            "不要凭记忆编造商品信息,也不要使用引用编号)"
        )
    numbered = "\n\n".join(f"[{i + 1}] {ctx}" for i, ctx in enumerate(contexts))
    return f"【知识库资料】\n{numbered}"


def get_llm():
    """根据配置创建大模型(local = Ollama,api = DeepSeek)"""
    if LLM_PROVIDER == "api":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=DEEPSEEK_MODEL,
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
            temperature=0.3,
            streaming=True,
        )
    return ChatOllama(
        model=OLLAMA_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=0.3,
    )


def build_messages(question: str, contexts: list[str], history_text: str) -> list:
    """拼装给大模型的消息:系统要求 + 知识库资料 + 历史对话 + 当前问题"""
    context_block = _build_context_block(contexts)
    return [
        ("system", SYSTEM_PROMPT),
        (
            "human",
            f"{context_block}\n\n【历史对话】\n{history_text}\n\n【用户当前问题】\n{question}",
        ),
    ]
