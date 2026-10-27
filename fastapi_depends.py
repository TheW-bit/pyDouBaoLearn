"""
P0 第一课：依赖注入 Depends（FastAPI 的灵魂）
============================================
本课知识点：
1. 什么是依赖注入：把「多个接口都要重复写的逻辑」抽成依赖函数，用 Depends 注入
2. 三种实战场景：
   ① 分页参数共用（Query 校验 + 默认值）
   ② 数据库连接管理（yield 自动打开/提交/关闭）
   ③ 接口鉴权（Header 校验 token）
3. 对比：不写依赖 → 每个接口重复 3 行分页代码；写了依赖 → 一行 Depends 搞定

启动：venv/Scripts/uvicorn fastapi_depends:app --reload
验收：浏览器打开 http://127.0.0.1:8000/docs
"""
import sqlite3
from typing import Annotated
from fastapi import FastAPI, Depends, Query, Header, HTTPException

app = FastAPI()
DB_PATH = "students_api.db"   # 沿用第二课建的学生库

# ══════════════════════════════════════════════════════════════
# 场景一：分页参数共用（课程原版场景：新闻列表 / 用户列表都要分页）
# ══════════════════════════════════════════════════════════════

# 1. 定义依赖函数：它长得就像一个普通函数，但专门给别的接口「供参数」
async def common_pagination(
    page: int = Query(1, ge=1, description="页码，从1开始"),          # Query 校验：page>=1
    page_size: int = Query(10, ge=1, le=50, description="每页条数"),  # Query 校验：1<=page_size<=50
):
    """分页依赖：自动解析 ?page=2&page_size=10，算好 offset/limit 返回"""
    return {"offset": (page - 1) * page_size, "limit": page_size}


# 2. 用法：接口参数里写 commons: dict = Depends(common_pagination)
#    → FastAPI 看到 Depends 就会自动调用依赖函数，把返回值传给接口
@app.get("/news")
async def get_news(commons: dict = Depends(common_pagination)):
    """模拟新闻列表（没连库，只是演示参数被自动注入了）"""
    return {"news": [1, 2, 3], **commons}   # 展开后带出 offset/limit


@app.get("/users")
async def get_users(commons: dict = Depends(common_pagination)):
    """模拟用户列表：同一个依赖，零重复代码"""
    return {"users": ["张三", "李四"], **commons}


# ══════════════════════════════════════════════════════════════
# 场景二：数据库连接管理（企业级标准写法，重点！）
# 用 yield 的依赖叫「有清理的依赖」：请求进来打开连接 → 接口用完 → 自动收尾
# ══════════════════════════════════════════════════════════════

def get_db():
    """数据库连接依赖：
    yield 之前 = 请求进来时执行（打开连接）
    yield 之后 = 接口返回前自动执行（提交/回滚/关闭）→ 不用每个接口自己管了
    """
    # check_same_thread=False：FastAPI 的同步依赖和接口可能在不同线程执行，
    # 不加这个参数会报 "SQLite objects created in a thread can only be used in that same thread"
    # （这是 SQLite + FastAPI 最经典的坑；换成 MySQL/PostgreSQL 连接池则天然没这问题）
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn            # 把连接「借」给接口用
        conn.commit()         # 接口正常结束 → 提交事务
    except Exception:
        conn.rollback()       # 出异常 → 回滚，防止写一半
        raise
    finally:
        conn.close()          # 无论成败都关闭连接，不泄漏


@app.get("/students")
async def get_students(db: sqlite3.Connection = Depends(get_db),
                       commons: dict = Depends(common_pagination)):
    """GET /students?page=1&page_size=5 → 分页查学生
    两个 Depends 可以叠加：一个给连接，一个给分页参数
    """
    rows = db.execute(
        "SELECT * FROM students LIMIT ? OFFSET ?",
        (commons["limit"], commons["offset"]),
    ).fetchall()
    return [dict(r) for r in rows]


@app.post("/students")
async def add_student(name: str, class_: str, score: int,
                      db: sqlite3.Connection = Depends(get_db)):
    """POST /students?name=测试&class_=A班&score=88 → 新增学生
    注意：这里不需要手动 commit/close，get_db 依赖自动搞定
    """
    cur = db.execute(
        "INSERT INTO students (name, class, score) VALUES (?, ?, ?)",
        (name, class_, score),
    )
    return {"id": cur.lastrowid, "name": name, "class": class_, "score": score}


# ══════════════════════════════════════════════════════════════
# 场景三：接口鉴权（你 RAG 项目里的 API Key 校验，放依赖里才是正规军）
# ══════════════════════════════════════════════════════════════

VALID_TOKEN = "pyL-2026"   # 演示用硬编码，真实项目应从环境变量读取

def verify_token(authorization: str = Header(...)):
    """鉴权依赖：要求请求头带 Authorization: Bearer pyL-2026
    Header(...) 表示这个参数必须从请求头取，缺了自动返回 422
    """
    if authorization != f"Bearer {VALID_TOKEN}":
        raise HTTPException(status_code=401, detail="无效的 token")
    return {"user": "admin"}   # 返回值可继续传给接口用


@app.get("/secure/data")
async def secure_data(auth: dict = Depends(verify_token)):
    """受保护的接口：先过鉴权依赖，才执行到这里"""
    return {"message": f"欢迎 {auth['user']}，这是机密数据"}


# ══════════════════════════════════════════════════════════════
# 为什么不写依赖的坏样子（对比用，已注释）
# 如果 get_students 不写依赖，分页逻辑得每个接口手写：
#   page: int = Query(1, ge=1)
#   page_size: int = Query(10, ge=1, le=50)
#   offset = (page - 1) * page_size
# 三个接口 = 9 行重复代码，改了 page_size 上限要改三处 → 依赖注入一次性解决
# ══════════════════════════════════════════════════════════════
