import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI


def _env_int(
    name: str,
    default: int,
    *,
    minimum: int = 0,
) -> int:
    """读取整数配置；配置错误时回退到安全默认值。"""

    try:
        value = int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        value = default

    return max(minimum, value)



#以后换模型或者换 API 地址，只需要修改 .env
load_dotenv()

LLM_TIMEOUT_SECONDS = _env_int(
    "LLM_TIMEOUT_SECONDS",
    90,
    minimum=1,
)
LLM_MAX_RETRIES = _env_int(
    "LLM_MAX_RETRIES",
    2,
)
LLM_MAX_TOKENS = _env_int(
    "LLM_MAX_TOKENS",
    2048,
    minimum=1,
)

llm = ChatOpenAI(
    model=os.getenv(
        "LLM_MODEL",
        "deepseek-v4-flash"
    ),
    streaming=True,
    api_key=os.getenv(
        "DEEPSEEK_API_KEY"
    ),
    base_url=os.getenv(
        "LLM_BASE_URL",
        "https://api.deepseek.com"
    ),
    temperature=0,
    timeout=LLM_TIMEOUT_SECONDS,
    max_retries=LLM_MAX_RETRIES,
    max_tokens=LLM_MAX_TOKENS,
)
