"""
2.17 补充：LangChain 流式输出
对比 llm_stream.py（手写 SSE 逐行读）
LangChain 里用 llm.stream() 或 chain.stream() 一行搞定
"""
from langchain_openai import ChatOpenAI
import os

API_KEY = os.environ.get("ARK_API_KEY", "ark-你的火山方舟APIKey")
CHAT_MODEL = "doubao-seed-2-1-lite-260915"
BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"

llm = ChatOpenAI(model=CHAT_MODEL, api_key=API_KEY, base_url=BASE_URL)

# 手写版要自己写：urllib + for line in resp + data: 解析 + delta.content
# LangChain 版：一个 for 循环逐块拿
print("LangChain 流式输出：")
for chunk in llm.stream("用三句话介绍 Python"):
    print(chunk.content, end="", flush=True)

print()  # 最后换行
