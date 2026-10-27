"""
2.16：向量数据库 Chroma —— 让 RAG 能存成千上万个文档
==========================================================
对比你现在的 rag_demo.py：
  - 旧：doc_vectors = embed(DOCS)  # 向量存内存列表，每次重跑都重新算 embedding
  - 新：Chroma 帮你存向量 + 原文 + 相似度搜索，不用自己算余弦

流程：
  1. pip install chromadb
  2. 创建/打开一个本地向量库（一个文件夹）
  3. add() 存文档（Chroma 自动调 embedding 或你自己传向量）
  4. query() 搜最相似的 top_k 段
  5. 拼进 prompt 调大模型（和 rag_demo.py 一样）

运行：venv/Scripts/python chroma_demo.py
"""

# ── 导入标准库和第三方库 ──
import json
import urllib.request
import chromadb                   # 向量数据库，刚装好
import os

# ── 配置：三个常量，和 rag_demo.py 完全一样 ──
API_KEY = os.environ.get("ARK_API_KEY", "ark-你的火山方舟APIKey")
CHAT_MODEL = "doubao-seed-2-1-lite-260915"
EMBED_MODEL = "doubao-embedding-vision-251215"

# ── 准备：还是那 5 段学习笔记 ──
DOCS = [
    "FastAPI 是 Python 的 Web 框架，用装饰器声明路由，Pydantic 自动校验请求体，自动生成 /docs 接口文档。",
    "SQLAlchemy ORM 用 Python 类映射数据库表，Session 管理连接，不用手写 SQL。",
    "MySQL 连接用 pymysql 驱动，连接串格式 mysql+pymysql://用户:密码@地址:端口/库名。",
    "SSE 流式响应通过 stream=True 开启，服务器边生成边发，客户端逐行读 delta.content。",
    "项目数据库是 students_api，表 students，有 id/name/class/score 四个字段，共 20 个学生。",
]


def get_embedding(text):
    """把一段文字变成向量（和 rag_demo.py 的 embed() 功能一样，只是单段版）"""
    req = urllib.request.Request(
        "https://ark.cn-beijing.volces.com/api/v3/embeddings/multimodal",
        data=json.dumps({
            "model": EMBED_MODEL,
            "input": [{"type": "text", "text": text}]
        }).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}"
        },
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    return result["data"]["embedding"]   # 返回单个向量 list[float]


def chat(messages):
    """调大模型对话接口（和 rag_demo.py 完全一样）"""
    req = urllib.request.Request(
        "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
        data=json.dumps({"model": CHAT_MODEL, "messages": messages, "stream": True}).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {API_KEY}"},
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        # 读取流式响应，每行一个 JSON 对象
        # 每个对象包含一个 delta 字段，是新增的内容
        for line in resp:
            line = line.decode("utf-8").strip()
            if line.startswith("data:"):
                # 跳过 data: 前缀，只保留 JSON 内容
                line = line[5:]
                # 解析 JSON 字符串
                result = json.loads(line.decode("utf-8"))
                content = result["choices"][0]["message"]["content"]
                if content:
                    yield


# ── 主程序 ──
if __name__ == "__main__":
    # ① 创建 Chroma 客户端，数据存在本地 ./chroma_db 文件夹
    #    第二次运行时会自动读取已有数据，不会重复算 embedding
    client = chromadb.PersistentClient(path="./chroma_db")

    # ② 创建/获取一个 collection（相当于数据库里的一张表）
    #    get_or_create = 有就拿，没有就建
    col = client.get_or_create_collection("my_docs")

    # ③ 如果 collection 是空的，把 5 段文档加进去
    #    关键：col.count() 看当前有多少段，>0 说明已经存过了，跳过
    if col.count() == 0:
        print("① 首次运行，正在把 5 段文档存入 Chroma...")
        for i, doc in enumerate(DOCS):
            col.add(
                ids=[f"doc_{i}"],                    # 每段一个唯一 id
                documents=[doc],                     # 原文
                embeddings=[get_embedding(doc)],    # 你算好的向量
            )
        print(f"   已存入 {col.count()} 段文档")
    else:
        print(f"① Chroma 已有 {col.count()} 段文档，跳过存入")

    # ④ 提问，让 Chroma 帮你搜最相似的 top3
    question = "我的项目里数据库是怎么连接的？用了什么驱动？"
    print(f"\n② 检索相关片段（问题：{question}）")
    results = col.query(
        query_embeddings=[get_embedding(question)],   # 问题变成向量
        n_results=3,                                   # 返回最相似的 3 段
    )
    # results["documents"][0] 是搜到的原文列表
    # results["distances"][0] 是对应的距离列表（越小越相似）
    for doc, dist in zip(results["documents"][0], results["distances"][0]):
        print(f"   距离={dist:.3f}  {doc[:40]}...")

    # ⑤ 把搜到的资料拼进 system 消息，调大模型
    context = "\n".join(f"- {doc}" for doc in results["documents"][0])
    messages = [
        {"role": "system", "content": f"根据以下资料回答问题，不要编造：\n{context}"},
        {"role": "user", "content": question}
    ]

    print("\n③ 大模型回答：")
    print(chat(messages))

    # ⑥ 验证：再跑一次，看会不会跳过存入
    #    第二次运行时你应该看到"已有 5 段文档，跳过存入"
    #    这就是 Chroma 比 rag_demo.py 强的地方：向量存本地，不用每次重算
