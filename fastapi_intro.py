"""
FastAPI 学生成绩 API（完整版：CRUD 四课合一）
============================================
第一课：3 个 GET 查询接口（全部/不及格/各班平均分）
第三课：POST 新增 + Pydantic 数据校验
第四课：PUT 修改 + DELETE 删除（CRUD 完整）

启动：venv/Scripts/uvicorn fastapi_intro:app --reload
验收：浏览器打开 http://127.0.0.1:8000/docs （FastAPI 自动生成的接口文档）
"""
import sqlite3
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, ConfigDict

# 创建 FastAPI 应用实例（app 是约定俗成的变量名）
app = FastAPI()
DB_PATH = "students_api.db"   # 数据库文件路径


def query(sql, params=()):
    """连接数据库、执行 SQL、返回全部结果行（读操作专用）
    为什么单独封这个函数：每个 GET 接口都要「连接→执行→取结果→关闭」，
    抽出来写一次就行。注意：它只用于「读」，写操作不能用（因为没 commit）。
    """
    conn = sqlite3.connect(DB_PATH)
    # row_factory = Row：让结果行能用 row["列名"] 取值（而不是 row[0] 下标）
    conn.row_factory = sqlite3.Row
    cur = conn.execute(sql, params)
    rows = cur.fetchall()      # 取出全部行
    conn.close()
    return rows


# Pydantic 数据模型：声明「POST /students 时客户端发来的 JSON 长什么样」
# FastAPI 会自动校验：name 必须是 str、score 必须是 int，
# 缺字段 / 类型错 → 自动返回 422 错误，不用我们手写 if 判断
class StudentIn(BaseModel):
    """POST /students 的请求体形状（In = 输入）"""
    name: str
    # class 是 Python 关键字，不能当字段名 → 用 class_ 当 Python 属性，
    # Field(alias="class") 告诉 FastAPI：JSON 里叫 "class"，不是 "class_"
    class_: str = Field(alias="class")
    score: int
    # populate_by_name=True：两种写法都能识别（JSON 传 "class" 或 "class_" 都行）
    model_config = ConfigDict(populate_by_name=True)


# ---------- GET 查询接口（第一课已毕业） ----------

@app.get("/")   # 装饰器：把下面函数注册成 GET 接口，路径是 /
def home():
    """首页：接口说明"""
    return {"message": "学生成绩 API（SQLite 版），接口文档见 /docs"}


@app.get("/students")   # GET /students → 返回全部学生
def get_students():
    rows = query("SELECT * FROM students")
    # 把 Row 对象列表转成普通字典列表（FastAPI 自动把字典转成 JSON）
    return [
        {"id": row["id"], "name": row["name"], "class": row["class"], "score": row["score"]}
        for row in rows
    ]


@app.get("/students/failed")   # GET /students/failed → 不及格学生
def get_failed():
    rows = query("SELECT * FROM students WHERE score < 60")
    return [
        {"id": row["id"], "name": row["name"], "class": row["class"], "score": row["score"]}
        for row in rows
    ]


@app.get("/students/avg")   # GET /students/avg → 各班平均分
def get_class_avg():
    # GROUP BY class：按班级分组，AVG(score) 算平均分
    rows = query("SELECT class, AVG(score) AS avg_score FROM students GROUP BY class")
    # 拼成 {"A班": 74.25, "B班": 67.5, "C班": 63.83} 这种字典
    return {row["class"]: round(row["avg_score"], 2) for row in rows}


# ---------- POST 新增（第三课） ----------

@app.post("/students")   # POST /students → 新增学生
def add_student(student: StudentIn):
    """接收 JSON → 校验通过后插入数据库 → 返回新学生（含自增 id）"""
    # 写操作四步：连接 → 执行 INSERT → commit 提交 → 关闭
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute(
        "INSERT INTO students(name, class, score) VALUES(?, ?, ?)",
        (student.name, student.class_, student.score)   # ? 占位符防 SQL 注入
    )
    conn.commit()              # ⚠️ 写操作必须 commit，不 commit = 没保存
    new_id = cur.lastrowid     # 拿回数据库自动生成的自增 id
    conn.close()
    # 返回新学生（FastAPI 自动转 JSON）
    return{"id": new_id, "name": student.name, "class": student.class_, "score": student.score}


# ---------- PUT 修改 + DELETE 删除（第四课） ----------

@app.put("/students/{student_id}")   # PUT /students/3 → 修改 id=3 的学生
def update_student(student_id: int, student: StudentIn):
    """路径参数 student_id 自动转成 int；body 自动校验成 StudentIn"""
    conn = sqlite3.connect(DB_PATH)
    # 1. 先查这个 id 是否存在
    rows = query("SELECT * FROM students WHERE id = ?", (student_id,))
    # 2. 不存在 → 抛 HTTPException(404)，FastAPI 自动返回 404 + JSON 错误
    if not rows:
        raise HTTPException(status_code=404, detail="学生不存在")
    # 3. 存在 → UPDATE 全量更新（name/class/score 都改掉）
    cur = conn.execute(
        "UPDATE students SET name = ?, class = ?, score = ? WHERE id = ?",
        (student.name, student.class_, student.score, student_id)
    )
    conn.commit()              # ⚠️ 写操作必须 commit
    conn.close()
    return{"id": student_id, "name": student.name, "class": student.class_, "score": student.score}


@app.delete("/students/{student_id}")   # DELETE /students/3 → 删除 id=3
def delete_student(student_id: int):
    conn = sqlite3.connect(DB_PATH)
    # 1. 先查是否存在，不存在 → 404
    rows = query("SELECT * FROM students WHERE id = ?", (student_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="学生不存在")
    # 2. DELETE 删除
    cur = conn.execute(
        "DELETE FROM students WHERE id = ?",
        (student_id,)
    )
    conn.commit()              # ⚠️ 写操作必须 commit
    conn.close()
    # 返回删除结果，顺便带上被删学生的名字
    return{"message": f"已删除学生：{rows[0]['name']}"}
