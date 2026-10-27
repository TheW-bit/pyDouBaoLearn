"""
2.15：RAG（检索增强生成）—— 让大模型读你自己的文档再回答
==========================================================
核心思想：大模型不知道你的私有知识（比如你项目用了什么数据库），
         RAG = 先从你的文档里搜相关片段，塞进 prompt 一起发给大模型，
         让大模型"看着资料回答"，而不是凭记忆瞎编。

完整流程：
  准备阶段（离线，只做一次）：
    你的文档 → 调 Embedding API → 每段文字变成向量 → 存起来
  查询阶段（每次提问都走一遍）：
    用户问题 → 问题也变成向量 → 算和每段文档的相似度 → 取最相关的 3 段
           → 把这 3 段拼进 system 消息 → 调大模型 → 打印回答

运行：venv/Scripts/python rag_demo.py
"""

# ── 导入标准库 ──
import json                  # JSON 字符串 ↔ Python 字典互转
import urllib.request         # 发 HTTP 请求（标准库，不用装）
import numpy as np            # 数值计算库（算余弦相似度用），你已经装过
import os

# ── 配置：三个常量，和你已跑通的代码一致 ──
API_KEY = os.environ.get("ARK_API_KEY", "ark-你的火山方舟APIKey")   # 火山方舟 API Key
CHAT_MODEL = "doubao-seed-2-1-lite-260915"                    # 对话模型（2.13 跑通的）
EMBED_MODEL = "doubao-embedding-vision-251215"               # 向量模型（多模态接口，支持纯文本）

# ── ① 你的私有文档（模拟知识库）──
# 实际项目里这些可能是 PDF、Word、网页爬下来的内容
# 这里直接用列表写 5 段学习笔记当例子
DOCS = [
    "FastAPI 是 Python 的 Web 框架，用装饰器声明路由，Pydantic 自动校验请求体，自动生成 /docs 接口文档。",
    "SQLAlchemy ORM 用 Python 类映射数据库表，Session 管理连接，不用手写 SQL。",
    "MySQL 连接用 pymysql 驱动，连接串格式 mysql+pymysql://用户:密码@地址:端口/库名。",
    "SSE 流式响应通过 stream=True 开启，服务器边生成边发，客户端逐行读 delta.content。",
    "项目数据库是 students_api，表 students，有 id/name/class/score 四个字段，共 20 个学生。",
]


def embed(texts):
    """
    把一段或多段文字变成向量（Embedding）。
    向量 = 一串数字，意思相近的文字向量也接近（语义坐标）。
    这里用多模态 embedding 接口，逐段文本单独请求。
    """
    vectors = []                          # 存每段文字对应的向量
    for text in texts:                    # 逐段处理（多模态接口一次只接受一个文本元素）
        # 构造 POST 请求
        req = urllib.request.Request(
            "https://ark.cn-beijing.volces.com/api/v3/embeddings/multimodal",  # 多模态 embedding 路径
            data=json.dumps({             # 请求体
                "model": EMBED_MODEL,     # 指定向量模型
                "input": [{"type": "text", "text": text}]   # 输入：一个文本类型的元素
            }).encode("utf-8"),            # 字典 → JSON 字符串 → 字节
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {API_KEY}"     # 认证
            },
            method="POST"
        )
        # 发请求并处理错误
        try:
            with urllib.request.urlopen(req) as resp:       # 发出去等响应
                result = json.loads(resp.read().decode("utf-8"))  # 字节 → 字符串 → 字典
        except urllib.error.HTTPError as e:                  # HTTP 错误（404/401 等）
            print(f"HTTP {e.code}: {e.read().decode('utf-8')}")
            raise
        # 多模态接口返回结构：data 是一个对象 {"embedding": [...]}，不是数组
        vectors.append(result["data"]["embedding"])
    return vectors


def cosine_sim(a, b):
    """
    余弦相似度：衡量两个向量有多接近。
    值范围 -1 ~ 1，越接近 1 表示两段文字意思越相关。
    公式：cos(a,b) = 点积 / (模长 × 模长)
    """
    a, b = np.array(a), np.array(b)       # 转成 numpy 数组
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def retrieve(question, doc_vectors, top_k=3):
    """
    检索：根据用户问题，从文档向量里找最相关的 top_k 段。
    步骤：问题 → 问题向量 → 和每段文档算相似度 → 取分数最高的 top_k 个下标
    """
    q_vec = embed([question])[0]                          # 问题变成向量（列表里取第 0 个）
    scores = [cosine_sim(q_vec, dv) for dv in doc_vectors]  # 列表推导：每段文档算一个相似度分数
    # np.argsort 返回排序后的下标（从小到大），[::-1] 反转为从大到小，[:top_k] 取前 top_k 个
    top_idx = np.argsort(scores)[::-1][:top_k]
    # 返回 [(文档原文, 分数), ...]
    return [(DOCS[i], scores[i]) for i in top_idx]


def chat_stream(messages):
    """
    【流式版】调大模型对话接口（和 llm_stream.py 一样）。
    返回一个生成器，逐块 yield 增量文字。

    ── 和之前普通版 chat() 的区别 ──
    普通版：一次性发请求 → 等几秒 → 拿到完整文字 → return 出来
    流式版：发请求 → 边生成边收 → 每收到一小块就 yield 一块
    """
    req = urllib.request.Request(
        "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
        # 【区别1】请求体多了 "stream": True
        # 普通版只有 {"model": CHAT_MODEL, "messages": messages}
        data=json.dumps({"model": CHAT_MODEL, "messages": messages, "stream": True}).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {API_KEY}"},
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        # 【区别2】不是 read() 一次性读完全部
        # 普通版：result = json.loads(resp.read().decode("utf-8"))
        # 流式版：for line in resp 逐行读 SSE 数据
        for line in resp:
            line = line.decode("utf-8").strip()
            if line.startswith("data:"):
                data = line[5:].strip()
                # 【区别3】收到 [DONE] 结束标志就 break
                if data == "[DONE]":
                    break
                chunk = json.loads(data)
                # 【区别4】取 delta.content（增量），不是 message.content（完整）
                # 普通版：return result["choices"][0]["message"]["content"]
                content = chunk["choices"][0]["delta"].get("content", "")
                if content:
                    # 【区别5】用 yield 逐块返回，不是 return 一次性返回
                    yield content


# ── 主程序：直接运行这个文件时执行 ──
if __name__ == "__main__":
    # 用户的问题（大模型本身不知道答案，需要靠 RAG 检索私有文档）
    question = "我的项目里数据库是怎么连接的？用了什么驱动？"

    # ① 准备阶段：把所有文档向量化
    # 实际项目里这步只做一次，向量可以存起来不用每次重算
    print("① 正在把文档向量化...")
    doc_vectors = embed(DOCS)             # 5 段文档 → 5 个向量

    # ② 检索阶段：根据问题找最相关的 3 段文档
    print(f"② 检索相关片段（问题：{question}）")
    hits = retrieve(question, doc_vectors, top_k=3)   # 返回 [(文档, 分数), ...]
    # 打印检索结果：排名 + 相似度分数 + 文档前 40 个字
    for i, (doc, score) in enumerate(hits, 1):
        print(f"   [{i}] 相似度={score:.3f}  {doc[:40]}...")

    # ③ 拼接 prompt：把搜到的资料塞进 system 消息
    # system 消息 = 给模型的"系统设定"，告诉它该怎么回答
    context = "\n".join(f"- {doc}" for doc, _ in hits)   # 3 段文档用换行拼成一段资料
    messages = [
        # 关键：把私有知识通过 system 消息注入 prompt
        {"role": "system", "content": f"根据以下资料回答问题，不要编造：\n{context}"},
        {"role": "user", "content": question}             # 用户的问题放 user 消息
    ]

    # ④ 【流式】调大模型，逐块打印（打字机效果）
    # 普通版：print(chat(messages))  ← 等几秒一次性蹦出全部
    # 流式版：for chunk in chat_stream(messages)  ← 边收边打，字一个一个出来
    print("\n③ 大模型回答：")
    for chunk in chat_stream(messages):
        # end="" 不换行（接在一起），flush=True 立即输出（不缓冲）
        print(chunk, end="", flush=True)
    print()  # 最后换行
