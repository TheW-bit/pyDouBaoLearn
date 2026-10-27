"""
阶段④ 第五课：Chroma 向量库持久化 —— 知识库向量存盘，重启不丢
================================================================
对比阶段④第四课（fastapi_rag.py）的改进：

  之前（第四课）：DOC_VECTORS = embed_many(DOCS)
                 → 每次启动都重新调用 embedding 接口，把 10 段文档重新向量化
  现在（第五课）：向量存进 ./chroma_db 文件夹（本地向量数据库）
                 → 第一次启动向量化并存盘，第二次启动直接从磁盘读，跳过向量化

  Chroma 就是阶段③第四课学的本地向量数据库（PersistentClient）：
    - PersistentClient(path="./chroma_db")  数据存本地文件夹，关电脑不丢
    - get_or_create_collection("my_docs")   相当于一张"向量表"，有就拿没有就建
    - col.add(ids, documents, embeddings)   存一段文档 = id + 原文 + 向量
    - col.query(query_embeddings, n_results) 给一个问题向量，返回最相似的 top_k 段

本文件保留第四课全部能力：存历史（ChatHistory 表）+ 流式（StreamingResponse）
+ 鉴权（verify_api_key）+ RAG 检索（改为 Chroma 检索，不再手写余弦相似度）。

运行：venv/Scripts/python fastapi_rag_persist.py
第一次启动会自动创建 ./chroma_db 并向量化 10 段文档（终端会打印）
第二次启动直接读磁盘，终端打印"从磁盘加载"说明持久化生效
然后浏览器打开 http://127.0.0.1:8000/ 测试（勾选知识库问答）
"""

# ── FastAPI 部分 ──
from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel

# ── 大模型 API 部分 ──
import json
import urllib.request

# ── Chroma 向量数据库 ──
import chromadb

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


app = FastAPI(title="AI 助手（带知识库 · Chroma 持久化）")
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


# ── Chroma 向量库初始化（第五课核心）──
CHROMA_DIR = "./chroma_db"          # 向量数据库存本地文件夹
COLLECTION_NAME = "rag_docs"        # 集合名 = 一张"向量表"（用独立名字，避免和
                                    # 阶段③ LangChain 课遗留的 my_docs 集合混在一起）

# PersistentClient：数据落盘到 ./chroma_db，关电脑不丢
client = chromadb.PersistentClient(path=CHROMA_DIR)

# get_or_create_collection：有就拿已有的，没有就新建
col = client.get_or_create_collection(COLLECTION_NAME)

if col.count() == 0:
    # 第一次启动：向量化并存入 Chroma
    print("首次运行：正在向量化知识库并存入 Chroma ...")
    for i, doc in enumerate(DOCS):
        vec = embed(doc)             # 每段文档单独转向量
        col.add(
            ids=[f"doc_{i}"],        # 每段的唯一 id
            documents=[doc],         # 原文
            embeddings=[vec]         # 向量
        )
    print(f"知识库已存入磁盘（{col.count()} 段），下次启动直接读取")
else:
    # 第二次启动：直接从磁盘读，不再调用 embedding 接口
    print(f"从磁盘加载知识库（{col.count()} 段），跳过向量化 ✓")


# ── 检索：问题 → Chroma 查最相关的 top_k 段（替代手写余弦相似度）──
def retrieve(question, top_k=3):
    q_vec = embed(question)                        # 问题也转成向量
    results = col.query(                          # Chroma 内部算相似度并排序
        query_embeddings=[q_vec],
        n_results=top_k
    )
    docs = results["documents"][0]                 # 命中的原文列表
    dists = results["distances"][0]                # 对应的距离（越小越相似）
    return list(zip(docs, dists))                  # [(原文, 距离), ...]


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


# ── 请求体：user_id + question + 是否用知识库 ──
class ChatRequest(BaseModel):
    user_id: str
    question: str
    use_rag: bool = True   # 默认开启知识库问答


# ── 路由：POST /rag/chat 带知识库的对话接口 ──
@app.post("/rag/chat", dependencies=[Depends(verify_api_key)])
def rag_chat(req: ChatRequest):
    """
    带知识库的流式问答（Chroma 持久化版）：
    1. Chroma 检索知识库，找和问题最相关的 3 段资料
    2. 拼 prompt：把资料塞进 system 消息
    3. 调大模型（流式）→ 逐块返回给前端
    4. 全部收完后存数据库
    """
    # 1. 检索知识库（从 Chroma 磁盘读，重启不丢）
    hits = retrieve(req.question, top_k=3)
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
