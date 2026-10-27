"""
2.14：大模型 API（SSE 流式模式，打字机效果）
=============================================
和 llm_demo.py 只有两处不同：
  ① 请求体加 "stream": True
  ② 响应从 read() 一次读 → for line in resp 逐行读，取值从 message.content → delta.content

运行前：同样填 API_KEY 和 ENDPOINT
运行：venv/Scripts/python llm_stream.py
"""
import json
import urllib.request
import os

API_KEY = os.environ.get("ARK_API_KEY", "ark-你的火山方舟APIKey")
ENDPOINT = "doubao-seed-2-1-lite-260915"
URL = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"

payload = {
    "model": ENDPOINT,
    "messages": [
        {"role": "user", "content": "用三句话介绍 Python"}
    ],
    "stream": True        # ① 开启流式
}

req = urllib.request.Request(
    URL,
    data=json.dumps(payload).encode("utf-8"),
    headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    },
    method="POST"
)

# ② 逐行读响应（不是 read() 一次拿全部）
with urllib.request.urlopen(req) as resp:
    for line in resp:
        line = line.decode("utf-8").strip()
        # SSE 格式：每行以 "data:" 开头
        if line.startswith("data:"):
            data = line[5:].strip()
            if data == "[DONE]":          # 结束标志
                break
            chunk = json.loads(data)
            # 每个 chunk 只有增量内容（delta，不是完整 message）
            content = chunk["choices"][0]["delta"].get("content", "")
            print(content, end="", flush=True)   # 不换行，立即输出 → 打字机效果

print()   # 最后换一行
