# 阶段④ 第五课自检脚本：验证 Chroma 持久化（不启动 Web 服务、不依赖 MySQL）
# 用法：venv/Scripts/python test_persist.py
# 只做三件事：
#   1) 首次：把 10 段文档向量化存进 ./chroma_db 的 rag_docs 集合
#   2) 二次：再次运行本脚本，应从磁盘直接读（打印"从磁盘加载"）
#   3) 检索：问一个问题，Chroma 返回最相关的 3 段
import json
import urllib.request
import chromadb
import os

# ── 配置（和 fastapi_rag_persist.py 一致）──
API_KEY = os.environ.get("ARK_API_KEY", "ark-你的火山方舟APIKey")
EMBED_MODEL = "doubao-embedding-vision-251215"
EMBED_URL = "https://ark.cn-beijing.volces.com/api/v3/embeddings/multimodal"

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
    return result["data"]["embedding"]

# ── 知识库（和 fastapi_rag_persist.py 一致）──
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

CHROMA_DIR = "./chroma_db"
COLLECTION_NAME = "rag_docs"

client = chromadb.PersistentClient(path=CHROMA_DIR)
col = client.get_or_create_collection(COLLECTION_NAME)

if col.count() == 0:
    print("首次运行：向量化并存入 Chroma ...")
    for i, doc in enumerate(DOCS):
        vec = embed(doc)
        col.add(ids=[f"doc_{i}"], documents=[doc], embeddings=[vec])
    print(f"知识库已存入磁盘（{col.count()} 段），下次启动直接读取")
else:
    print(f"从磁盘加载知识库（{col.count()} 段），跳过向量化 ✓")

# 检索验证
q_vec = embed("怎么用 FastAPI 做接口")
res = col.query(query_embeddings=[q_vec], n_results=3)
for doc, dist in zip(res["documents"][0], res["distances"][0]):
    print(f"  [{dist:.3f}] {doc[:30]}...")
