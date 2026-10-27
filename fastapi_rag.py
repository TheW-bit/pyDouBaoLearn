"""
阶段④ 第四课：RAG 整合进 FastAPI —— 带知识库的问答接口
==========================================================
把阶段③学的 RAG 和阶段④学的 FastAPI + 数据库拼起来：
  - 知识库：你的 Python 学习笔记（模拟私有文档）
  - 接口：POST /rag/chat —— 检索知识库 → 拼 prompt → 调大模型 → 存历史
  - 前端：聊天页面加一个"知识库问答"开关

本文件整合了前面课程的全部能力：
  第1课 数据库存历史（ChatHistory 表）
  第2课 流式输出（StreamingResponse）
  第3课 API Key 鉴权（verify_api_key）
  +     RAG 检索（embed/embed_many/cosine_sim/retrieve）

对比 fastapi_chat_db.py 的改进：
  - 之前：大模型凭自己的知识回答（可能瞎编）
  - 现在：先从知识库检索相关资料，让大模型"看着资料回答"

运行：venv/Scripts/python fastapi_rag.py
然后浏览器打开 http://127.0.0.1:8000/ 测试
"""

# ── FastAPI 部分 ──
from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel

# ── 大模型 API 部分 ──
import json
import urllib.request

# ── 数值计算（余弦相似度）──
import numpy as np

# ── 数据库 ORM ──
from sqlalchemy import create_engine, select, String, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session
import os

# ── 配置 ──
API_KEY = os.environ.get("ARK_API_KEY", "ark-你的火山方舟APIKey")
CHAT_MODEL = "doubao-seed-2-1-lite-260915"
EMBED_MODEL = "doubao-embedding-vision-251215"   # 向量模型
CHAT_URL = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
EMBED_URL = "https://ark.cn-beijing.volces.com/api/v3/embeddings/multimodal"

# ── 鉴权 ──
VALID_API_KEY = "my-secret-key-123456"

async def verify_api_key(x_api_key: str = Header(None)):
    if x_api_key != VALID_API_KEY:
        raise HTTPException(status_code=401, detail="无效的 API Key")
    return x_api_key

# ── 数据库（和 fastapi_chat_db.py 一样）──
engine = create_engine(
    "mysql+pymysql://root:123456@localhost:3306/students_api?charset=utf8mb4",
    echo=False
)

class Base(DeclarativeBase):
    pass

class ChatHistory(Base):
    """存每一轮对话"""
    __tablename__ = "chat_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(50))
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(String(2000))
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())


app = FastAPI(title="AI 助手（带知识库）")
Base.metadata.create_all(engine)


# ── 知识库：你的学习笔记（模拟私有文档）──
DOCS = [
    "FastAPI 是 Python 的 Web 框架，用装饰器声明路由，Pydantic 自动校验请求体，自动生成 /docs 接口文档。",
    "SQLAlchemy ORM 用 Python 类映射数据库表，Session 管理连接，不用手写 SQL。",
    "MySQL 连接用 pymysql 驱动，连接串格式 mysql+pymysql://用户:密码@地址:端口/库名。",
    "SSE 流式响应通过 stream=True 开启，服务器边生成边发，客户端逐行读 delta.content。",
    "项目数据库是 students_api，表 students，有 id/name/class/score 四个字段，共 20 个学生。",
    "RAG 检索增强生成：先把文档变成向量存起来，提问时把问题也变成向量，找最相似的几段，拼进 prompt 让大模型看着资料回答。",
    "Chroma 是向量数据库，PersistentClient 存本地，get_or_create_collection 建集合，add 存向量，query 检索。",
    "LangChain 框架把 RAG 流程封装成管道：Chroma.from_texts 一行存文档，as_retriever 检索，chain = prompt | llm | StrOutputParser。",
    "ngrok 内网穿透：ngrok http 8000 把本机端口暴露成公网地址，适合临时演示。",
    "FastAPI 鉴权用 Depends + Header：请求头带 X-API-Key，依赖函数里校验，不对就抛 401。",
]

# ── Embedding：文字 → 向量（一次处理一段）──
def embed(text):
    """把一段文字变成向量"""
    req = urllib.request.Request(
        EMBED_URL,
        data=json.dumps({
            "model": EMBED_MODEL,
            "input": [{"type": "text", "text": text}]
        }).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {API_KEY}"},
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    return result["data"]["embedding"]  # 多模态接口：data 是对象，直接取 embedding


# ── 批量向量化：遍历每段文档，逐段转成向量 ──
def embed_many(texts):
    """把多段文字逐段变成向量，返回向量列表"""
    return [embed(text) for text in texts]


# ── 余弦相似度 ──
def cosine_sim(a, b):
    a, b = np.array(a), np.array(b)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


# ── 检索：问题 → 找最相关的 top_k 段文档 ──
def retrieve(question, doc_vectors, top_k=3):
    q_vec = embed(question)
    scores = [cosine_sim(q_vec, dv) for dv in doc_vectors]
    top_idx = np.argsort(scores)[::-1][:top_k]
    return [(DOCS[i], scores[i]) for i in top_idx]


# ── 大模型流式调用 ──
def call_llm_stream(messages):
    req = urllib.request.Request(
        CHAT_URL,
        data=json.dumps({
            "model": CHAT_MODEL,
            "messages": messages,
            "stream": True
        }).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {API_KEY}"},
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        for line in resp:
            line = line.decode("utf-8").strip()
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            chunk = json.loads(data)
            content = chunk["choices"][0]["delta"].get("content", "")
            if content:
                yield content


# ── 启动时把知识库向量化（只做一次）──
print("正在向量化知识库...")
DOC_VECTORS = embed_many(DOCS)  # 10 段文档 → 10 个向量
print(f"知识库就绪：{len(DOCS)} 段文档已向量化")


# ── 请求体：user_id + question + 是否用知识库 ──
class ChatRequest(BaseModel):
    user_id: str
    question: str
    use_rag: bool = True   # 默认开启知识库问答


# ── 路由：POST /rag/chat 带知识库的对话接口 ──
@app.post("/rag/chat", dependencies=[Depends(verify_api_key)])
def rag_chat(req: ChatRequest):
    """
    带知识库的流式问答：
    1. 检索知识库，找和问题最相关的 3 段资料
    2. 拼 prompt：把资料塞进 system 消息
    3. 调大模型（流式）→ 逐块返回给前端
    4. 全部收完后存数据库
    """
    # 1. 检索知识库
    hits = retrieve(req.question, DOC_VECTORS, top_k=3)
    context = "\n".join(f"- {doc}" for doc, _ in hits)

    # 2. 拼 messages
    messages = [
        {"role": "system", "content": f"根据以下资料回答问题，不要编造：\n{context}"},
        {"role": "user", "content": req.question},
    ]

    # 3. 存用户问题
    with Session(engine) as session:
        session.add(ChatHistory(user_id=req.user_id, role="user", content=req.question))
        session.commit()

    # 4. 流式返回 + 攒起来存数据库
    answer_parts = []

    def generate():
        for chunk in call_llm_stream(messages):
            answer_parts.append(chunk)
            yield chunk
        answer = "".join(answer_parts)
        with Session(engine) as session:
            session.add(ChatHistory(user_id=req.user_id, role="assistant", content=answer))
            session.commit()

    return StreamingResponse(generate(), media_type="text/event-stream")


# ── 路由：GET / 聊天页面 ──
@app.get("/")
def index():
    return FileResponse("index.html")


# ── 路由：GET /history/{user_id} 查历史 ──
@app.get("/history/{user_id}", dependencies=[Depends(verify_api_key)])
def get_history(user_id: str):
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
