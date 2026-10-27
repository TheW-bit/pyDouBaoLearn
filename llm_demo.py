"""
2.13：大模型 API 调用（普通模式，一次性返回完整回复）
=====================================================
用标准库 urllib（不用装 requests），调火山方舟豆包大模型。
原理：和你调自己的 FastAPI /students 是同一个 HTTP POST，只是方向反过来。

运行前：填好 API_KEY 和 ENDPOINT（火山方舟控制台申请）
运行：venv/Scripts/python llm_demo.py
"""
import json
import urllib.request
import os

# ── 填你自己的密钥 ──
API_KEY = os.environ.get("ARK_API_KEY", "ark-你的火山方舟APIKey")        # 火山方舟 → API Key 管理
ENDPOINT = "doubao-seed-2-1-lite-260915"      # 模型名（控制台示例里带的，不用接入点 ID）
URL = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"

# 请求体：messages 是对话历史，role 有 user / assistant / system
payload = {
    "model": ENDPOINT,
    "messages": [
        {"role": "user", "content": "用一句话解释什么是并发"}
    ]
}

# 构造 POST 请求
req = urllib.request.Request(
    URL,
    data=json.dumps(payload).encode("utf-8"),
    headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"   # 认证：Bearer + Key
    },
    method="POST"
)

# 发请求 → 等回复 → 读字节 → 转字符串 → 转字典
with urllib.request.urlopen(req) as resp:
    result = json.loads(resp.read().decode("utf-8"))

# 取出回复内容（路径：choices[0].message.content）
reply = result["choices"][0]["message"]["content"]
print("大模型回复：", reply)
