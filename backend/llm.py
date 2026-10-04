import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI



#以后换模型或者换 API 地址，只需要修改 .env
load_dotenv()

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
    temperature=0
)