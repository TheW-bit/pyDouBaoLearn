"""
2.17：LangChain —— 用框架重写 RAG
==========================================================
和 rag_demo.py 做对比：
  - 手写版：urllib 发请求、自己算余弦相似度、自己拼 messages（143 行）
  - LangChain 版：框架帮你做这些，核心逻辑只要 10 行（68 行）

运行：venv/Scripts/python langchain_demo.py
"""

# ── 导入标准库 ──
import json                  # JSON 字符串 ↔ Python 字典互转
import urllib.request         # 发 HTTP 请求（标准库）

# ── 导入 LangChain 组件（都是框架帮你封装好的）──
from langchain_openai import ChatOpenAI          # 大模型客户端（兼容 OpenAI 格式）
from langchain_core.embeddings import Embeddings # Embedding 抽象基类（自定义类要继承它）
from langchain_core.prompts import ChatPromptTemplate  # Prompt 模板（自动格式化变量）
from langchain_core.output_parsers import StrOutputParser  # 输出解析器（把模型输出转成字符串）
from langchain_core.runnables import RunnablePassthrough   # 透传（把输入原样传下去）
from langchain_community.vectorstores import Chroma        # Chroma 向量数据库封装
import os


# ── 配置：和你之前跑通的代码一致 ──
API_KEY = os.environ.get("ARK_API_KEY", "ark-你的火山方舟APIKey")   # 火山方舟 API Key
CHAT_MODEL = "doubao-seed-2-1-lite-260915"                    # 对话模型
EMBED_MODEL = "doubao-embedding-vision-251215"               # 向量模型（多模态接口）
BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"        # 火山方舟基础地址


class VolcanoEmbeddings(Embeddings):
    """
    自定义 Embedding 类：包装火山方舟多模态接口。
    为什么要自定义？因为 LangChain 自带的 OpenAIEmbeddings 走的是
    标准 OpenAI 的 /embeddings 路径，而火山方舟的 embedding 是
    /embeddings/multimodal（多模态接口），路径不一样，所以要自己包装。

    继承 Embeddings 基类，必须实现两个方法：
      - embed_documents(texts)：批量嵌入文档
      - embed_query(text)：嵌入单条查询
    """

    def embed_documents(self, texts):
        """批量嵌入文档（建库时调），返回向量列表"""
        return [self._embed(t) for t in texts]   # 列表推导：逐段调 _embed

    def embed_query(self, text):
        """嵌入单条查询（检索时调），返回一个向量"""
        return self._embed(text)

    def _embed(self, text):
        """实际发请求调火山方舟 embedding 接口（和你之前写的 get_embedding 一模一样）"""
        req = urllib.request.Request(
            f"{BASE_URL}/embeddings/multimodal",   # 多模态 embedding 路径
            data=json.dumps({                        # 请求体
                "model": EMBED_MODEL,
                "input": [{"type": "text", "text": text}]   # 输入一个文本元素
            }).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {API_KEY}"
            },
            method="POST")
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        # 多模态接口返回结构：data 是对象 {"embedding": [...]}，不是数组
        return result["data"]["embedding"]


# ── 你的私有文档（模拟知识库，和 rag_demo.py 一样）──
DOCS = [
    "FastAPI 是 Python 的 Web 框架，用装饰器声明路由，Pydantic 自动校验请求体。",
    "SQLAlchemy ORM 用 Python 类映射数据库表，Session 管理连接，不用手写 SQL。",
    "MySQL 连接用 pymysql 驱动，连接串 mysql+pymysql://用户:密码@地址:端口/库名。",
    "SSE 流式响应通过 stream=True 开启，逐行读 delta.content。",
    "项目数据库是 students_api，表 students，20 个学生。",
]


# ── 主程序：直接运行这个文件时执行 ──
if __name__ == "__main__":
    # ① 创建大模型客户端
    # 对比手写版：你之前要自己写 urllib POST 到 /chat/completions
    # LangChain 版：ChatOpenAI 一行搞定，改 base_url 就能接火山方舟
    llm = ChatOpenAI(model=CHAT_MODEL, api_key=API_KEY, base_url=BASE_URL)

    # ② 创建 embedding 对象（就是上面自定义的那个类）
    embeddings = VolcanoEmbeddings()

    # ③ 创建向量库，存入文档
    # 对比手写版：你之前要自己写 embed(DOCS) → 存内存列表 → 自己算余弦相似度
    # LangChain 版：Chroma.from_texts() 一行搞定，自动调 embedding + 存向量
    # persist_directory：数据存本地文件夹，第二次运行不用重新算
    vectorstore = Chroma.from_texts(
        texts=DOCS, embedding=embeddings,
        persist_directory="./chroma_db_lc",
    )

    # ④ 创建检索器：给一个问题，自动返回最相关的 top_k 段文档
    # 对比手写版：你之前要自己写 retrieve() 函数，算相似度 → argsort → 取 top_k
    # LangChain 版：as_retriever() 一行搞定，search_kwargs={"k": 3} 就是 top 3
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

    # ⑤ 定义 prompt 模板
    # {context} 和 {question} 是占位符，运行时会被自动替换
    # 对比手写版：你之前要手动拼 messages 列表
    # LangChain 版：模板写好，传变量进去就行
    prompt = ChatPromptTemplate.from_messages([
        ("system", "根据以下资料回答问题，不要编造：\n{context}"),  # system 消息注入检索到的资料
        ("user", "{question}"),                                      # user 消息放用户问题
    ])

    # ⑥ 组装 RAG chain（LangChain 的核心：管道符 | 把组件串起来）
    # 对比 Linux 管道：A | B | C，A 的输出是 B 的输入，B 的输出是 C 的输入
    # 流程：用户问题 → 检索器找相关文档 → 拼成 prompt → 调大模型 → 输出转字符串
    chain = (
        # 输入是用户问题字符串，我们构造一个字典：
        #   context：从检索器拿文档，再用 lambda 把 Document 对象列表拼成纯文本
        #   question：RunnablePassthrough() 把用户问题原样传下去
        {"context": retriever | (lambda docs: "\n".join(d.page_content for d in docs)),
         "question": RunnablePassthrough()}
        | prompt       # 把 {context} 和 {question} 填进模板，生成完整 messages
        | llm          # 把 messages 发给大模型，拿到模型输出
        | StrOutputParser()  # 把模型输出（AIMessage 对象）转成纯字符串
    )

    # ⑦ 提问！chain.invoke() 就是跑一遍整个流程
    question = "我的项目里数据库是怎么连接的？用了什么驱动？"
    print("问题：", question)
    print("回答：", chain.invoke(question))
