from langchain.chat_models import init_chat_model
from dotenv import load_dotenv
import os

# 加载 .env 文件中的环境变量
load_dotenv()

# 通用配置
API_KEY = os.getenv("SILICONFLOW_API_KEY")
if not API_KEY:
    raise ValueError("未找到 SILICONFLOW_API_KEY 环境变量，请检查 .env 文件")
BASE_URL = "https://api.siliconflow.cn/v1"


def get_model():
    """获取主模型（DeepSeek-V3.2）"""
    model = init_chat_model(
        "deepseek-ai/DeepSeek-V3.2",
        model_provider="openai",
        api_key=API_KEY,
        base_url=BASE_URL,
        temperature=0.7,
        timeout=300,
        max_tokens=2048
    )
    return model


def get_routing_model():
    """获取路由模型（Qwen3-32B，用于 Manager 路由决策）"""
    model = init_chat_model(
        "Qwen/Qwen3-32B",
        model_provider="openai",
        api_key=API_KEY,
        base_url=BASE_URL,
        temperature=0.3,  # 路由决策需要更确定性的输出
        timeout=60,
        max_tokens=2048
    )
    return model


def get_middleware_model():
    """获取中间件模型（Qwen3-8B，用于消息总结等轻量任务）"""
    model = init_chat_model(
        "Qwen/Qwen3-8B",
        model_provider="openai",
        api_key=API_KEY,
        base_url=BASE_URL,
        temperature=0.5,
        timeout=60,
        max_tokens=2048
    )
    return model
