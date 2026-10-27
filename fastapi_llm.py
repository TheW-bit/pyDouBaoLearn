"""
2.18：FastAPI + 大模型整合 —— AI 对话 Web 接口
==========================================================
把你之前学的两块拼起来：
  - FastAPI（阶段②学的 Web 框架）
  - 大模型 API（阶段③学的）
  = 一个可以对话的后端接口

运行：venv/Scripts/python fastapi_llm.py
然后浏览器打开 http://127.0.0.1:8000/docs 测试
"""

# ── 导入：FastAPI 部分 ──
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# ── 导入：大模型 API 部分 ──
import json
import urllib.request
import os

# ── 配置 ──
API_KEY = os.environ.get("ARK_API_KEY", "ark-你的火山方舟APIKey")
CHAT_MODEL = "doubao-seed-2-1-lite-260915"
CHAT_URL = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"

# ── 创建 FastAPI 应用 ──
app = FastAPI(
    title="AI 助手 API",
    summary="基于 RAG 的智能问答服务",
    version="0.1.0",
)


# ── 定义请求体格式 ──
class ChatRequest(BaseModel):
    question: str          # 用户的问题
    history: list = []    # 对话历史（可选，多轮对话用）


# ── 封装大模型流式调用（生成器，逐块 yield）──
def call_llm_stream(messages):
    """调火山方舟大模型，流式返回生成器"""
    req = urllib.request.Request(
        CHAT_URL,
        data=json.dumps({
            "model": CHAT_MODEL,
            "messages": messages,
            "stream": True          # 开启流式
        }).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}"
        },
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        for line in resp:
            line = line.decode("utf-8").strip()
            # SSE 格式：每行以 data: 开头
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":       # 结束标志
                break
            chunk = json.loads(data)
            content = chunk["choices"][0]["delta"].get("content", "")
            if content:
                yield content


# ── 路由：POST /chat 对话接口（普通模式）──
@app.post("/chat")
def chat(req: ChatRequest):
    """
    普通模式：一次性返回完整回答
    请求格式：{"question": "你好", "history": []}
    """
    messages = [
        {"role": "system", "content": "你是一个 helpful 的助手，简洁回答问题。"},
    ]
    messages.extend(req.history)
    messages.append({"role": "user", "content": req.question})

    # 把生成器里的内容拼成完整字符串
    answer = "".join(call_llm_stream(messages))
    return {"answer": answer}


# ── 路由：POST /chat/stream 对话接口（流式模式）──
@app.post("/chat/stream")
def chat_stream(req: ChatRequest):
    """
    流式模式：SSE 逐块返回，前端可以看到打字机效果
    """
    messages = [
        {"role": "system", "content": "你是一个 helpful 的助手，简洁回答问题。"},
    ]
    messages.extend(req.history)
    messages.append({"role": "user", "content": req.question})

    # StreamingResponse 把生成器内容逐块推给前端
    return StreamingResponse(
        call_llm_stream(messages),
        media_type="text/event-stream"
    )


# ── 启动服务器 ──
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
