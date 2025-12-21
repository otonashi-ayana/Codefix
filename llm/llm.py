from langchain_openai import ChatOpenAI
from runtime_env import *
from utils.tools import *

SYSTEM_PROMPT = """You are an senior expert in code bug fixing. Here are some regulations:
- For natural language, response with Chinese.
"""

model = ChatOpenAI(
    model=MODEL,
    api_key=API_KEY,
    base_url=BASE_URL,
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2
)
