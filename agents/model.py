from langchain.chat_models import init_chat_model
from dotenv import load_dotenv
import os
# 加载 .env 文件中的环境变量
load_dotenv()
def get_model():

    # 模型配置常量
    MODEL_NAME = "qwen3-max"
    MODEL_PROVIDER = "openai"
    API_KEY = os.getenv("DASHSCOPE_API_KEY")
    if not API_KEY:
        raise ValueError("未找到 DASHSCOPE_API_KEY 环境变量，请检查 .env 文件")
    BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    TEMPERATURE = 0.7
    TIMEOUT = 30
    MAX_TOKENS = 10000

    # 初始化聊天模型
    model = init_chat_model(
        MODEL_NAME,
        model_provider=MODEL_PROVIDER,
        api_key=API_KEY,
        base_url=BASE_URL,
        temperature=TEMPERATURE,
        timeout=TIMEOUT,
        max_tokens=MAX_TOKENS
    )
    return model