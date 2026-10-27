"""
阶段④ 第1-3课合集：FastAPI + 大模型 + 数据库存对话历史 + 流式输出 + 鉴权
==========================================================
用 MySQL（phpStudy 自带）
本文件按学习进度逐步升级，含三课内容：
  第1课：数据库存对话历史（/chat 自动查历史、自动存）
  第2课：流式输出（/chat/stream 打字机效果）
  第3课：API Key 鉴权（请求头 X-API-Key，verify_api_key 依赖）

对比 fastapi_llm.py 的改进：
  - 之前：history 由前端传，后端不存，关掉就没了
  - 现在：history 由后端从 MySQL 查，自动存、自动取

运行：venv/Scripts/python fastapi_chat_db.py
然后浏览器打开 http://127.0.0.1:8000/ 测试
"""

# ── FastAPI 部分 ──
from fastapi import FastAPI, Depends, Header, HTTPException
from pydantic import BaseModel

# ── 大模型 API 部分 ──
import json
import urllib.request

# ── 数据库 ORM 部分（SQLite，不用装任何东西）──
from sqlalchemy import create_engine, select, String, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session
import os

# ── 配置 ──
API_KEY = os.environ.get("ARK_API_KEY", "ark-你的火山方舟APIKey")
CHAT_MODEL = "doubao-seed-2-1-lite-260915"
CHAT_URL = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"

# ── 鉴权配置：只有带正确 API Key 的请求才能访问 ──
VALID_API_KEY = "my-secret-key-123456"  # 你自己定的密钥

async def verify_api_key(x_api_key: str = Header(None)):
    """依赖函数：检查请求头里的 X-API-Key 对不对"""
    if x_api_key != VALID_API_KEY:
        raise HTTPException(status_code=401, detail="无效的 API Key")
    return x_api_key

# MySQL 连接（和你 orm_mysql.py 一模一样）
engine = create_engine(
    "mysql+pymysql://root:123456@localhost:3306/students_api?charset=utf8mb4",
    echo=False
)


class Base(DeclarativeBase):
    pass


# ── 对话历史表模型 ──
class ChatHistory(Base):
    """存每一轮对话：用户问了什么，大模型答了什么"""
    __tablename__ = "chat_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(50))       # 用户标识
    role: Mapped[str] = mapped_column(String(20))         # user 或 assistant
    content: Mapped[str] = mapped_column(String(2000))   # 对话内容
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())


# ── 创建 FastAPI 应用 ──
app = FastAPI(title="AI 对话接口（带历史存储）",
    summary="基于 RAG 的智能问答服务",
    version="0.1.0",
)

# 启动时自动建表
Base.metadata.create_all(engine)


# ── 请求体格式：只需要 user_id + question，不用传 history 了 ──
class ChatRequest(BaseModel):
    user_id: str          # 用户标识（谁在聊天）
    question: str         # 用户的问题


# ── 封装大模型流式调用（生成器，逐块 yield）──
def call_llm(messages):
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


# ── 路由：POST /chat ──
@app.post("/chat", dependencies=[Depends(verify_api_key)])
def chat(req: ChatRequest):
    """
    带历史存储的对话接口。
    前端只需要传 user_id 和 question，后端自动管理历史。
    """
    with Session(engine) as session:
        # 1. 从数据库查这个用户最近 10 轮对话（20 条消息）
        history_rows = session.scalars(
            select(ChatHistory)
            .where(ChatHistory.user_id == req.user_id)
            .order_by(ChatHistory.id.desc())
            .limit(20)
        ).all()
        history_rows = list(reversed(history_rows))  # 倒序查的，正过来

        # 2. 拼 messages：系统设定 + 历史 + 当前问题
        messages = [
            {"role": "system", "content": "你是一个 helpful 的助手，简洁回答问题。"},
        ]
        for row in history_rows:
            messages.append({"role": row.role, "content": row.content})
        messages.append({"role": "user", "content": req.question})

        # 3. 把用户的问题存进数据库
        session.add(ChatHistory(user_id=req.user_id, role="user", content=req.question))
        session.commit()

    # 4. 调大模型（生成器 → 拼成完整字符串）
    answer = "".join(call_llm(messages))

    # 5. 把大模型的回答存进数据库
    with Session(engine) as session:
        session.add(ChatHistory(user_id=req.user_id, role="assistant", content=answer))
        session.commit()

    return {"answer": answer}


# ── 路由：POST /chat/stream 流式对话接口 ──
@app.post("/chat/stream", dependencies=[Depends(verify_api_key)])
def chat_stream(req: ChatRequest):
    """
    流式模式：SSE 逐块返回，前端看到打字机效果
    """
    from fastapi.responses import StreamingResponse

    with Session(engine) as session:
        history_rows = session.scalars(
            select(ChatHistory)
            .where(ChatHistory.user_id == req.user_id)
            .order_by(ChatHistory.id.desc())
            .limit(20)
        ).all()
        history_rows = list(reversed(history_rows))

        messages = [
            {"role": "system", "content": "你是一个 helpful 的助手，简洁回答问题。"},
        ]
        for row in history_rows:
            messages.append({"role": row.role, "content": row.content})
        messages.append({"role": "user", "content": req.question})

        session.add(ChatHistory(user_id=req.user_id, role="user", content=req.question))
        session.commit()

    # 流式生成器：一边收大模型的字，一边返回给前端，同时攒起来存数据库
    answer_parts = []

    def generate():
        for chunk in call_llm(messages):
            answer_parts.append(chunk)
            yield chunk
        # 全部收完后存数据库
        answer = "".join(answer_parts)
        with Session(engine) as session:
            session.add(ChatHistory(user_id=req.user_id, role="assistant", content=answer))
            session.commit()

    return StreamingResponse(generate(), media_type="text/event-stream")


# ── 路由：GET /  返回聊天网页 ──
@app.get("/")
def index():
    """返回聊天页面"""
    from fastapi.responses import FileResponse
    return FileResponse("index.html")


# ── 路由：GET /history/{user_id} 查对话历史 ──
@app.get("/history/{user_id}", dependencies=[Depends(verify_api_key)])
def get_history(user_id: str):
    """查某个用户的所有对话历史"""
    with Session(engine) as session:
        rows = session.scalars(
            select(ChatHistory)
            .where(ChatHistory.user_id == user_id)
            .order_by(ChatHistory.id.asc())
        ).all()
        return {
            "user_id": user_id,
            "count": len(rows),
            "history": [
                {"role": r.role, "content": r.content, "time": str(r.created_at)}
                for r in rows
            ]
        }


# ── 启动服务器 ──
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
