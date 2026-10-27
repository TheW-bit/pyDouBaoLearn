"""
第二课：初始化学生成绩数据库 students_api.db
=============================================
作用：建表 + 插入 20 个学生的测试数据
特点：可重复运行（先 DROP 旧表再建），用来「重置基线」
运行：venv/Scripts/python init_db.py
"""
import sqlite3

# 20 名学生的测试数据（列表里每个字典 = 一个学生）
# 成绩设计：故意让 7 个人 < 60（不及格），蒋十六=60 算及格
students = [
    {"name": "张三", "class": "A班", "score": 85},
    {"name": "李四", "class": "A班", "score": 58},   # 不及格
    {"name": "王五", "class": "B班", "score": 92},
    {"name": "赵六", "class": "B班", "score": 45},   # 不及格
    {"name": "孙七", "class": "A班", "score": 76},
    {"name": "周八", "class": "C班", "score": 63},
    {"name": "吴九", "class": "C班", "score": 41},   # 不及格
    {"name": "郑十", "class": "A班", "score": 98},
    {"name": "王十一", "class": "B班", "score": 55},  # 不及格
    {"name": "冯十二", "class": "C班", "score": 88},
    {"name": "陈十三", "class": "A班", "score": 72},
    {"name": "褚十四", "class": "B班", "score": 39},  # 不及格
    {"name": "卫十五", "class": "C班", "score": 95},
    {"name": "蒋十六", "class": "A班", "score": 60},  # =60 算及格
    {"name": "沈十七", "class": "B班", "score": 84},
    {"name": "韩十八", "class": "C班", "score": 52},  # 不及格
    {"name": "杨十九", "class": "A班", "score": 67},
    {"name": "朱二十", "class": "B班", "score": 90},
    {"name": "秦二十一", "class": "C班", "score": 44},  # 不及格
    {"name": "尤二十二", "class": "A班", "score": 78},
]

# 连接数据库（文件不存在会自动创建）
conn = sqlite3.connect("students_api.db")
cur = conn.cursor()

# 建表：可重复运行
# DROP TABLE IF EXISTS：先把旧表删掉（如果存在）→ 保证每次跑都是干净的 20 人
cur.execute("DROP TABLE IF EXISTS students")
# CREATE TABLE：建表，定义列
#   id：主键，INTEGER PRIMARY KEY AUTOINCREMENT = 自增 id（1,2,3... 自动生成）
#   name/class/score：分别是学生姓名、班级、成绩，都不能为空
cur.execute("""
    CREATE TABLE students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        class TEXT NOT NULL,
        score INTEGER NOT NULL
    )
""")

# 批量插入：executemany 一次插入多行（比循环 execute 快）
# ? 是占位符：防 SQL 注入，也避免手拼字符串出错
cur.executemany(
    "INSERT INTO students (name, class, score) VALUES (?, ?, ?)",
    [(s["name"], s["class"], s["score"]) for s in students]
)

conn.commit()    # ⚠️ 写操作必须 commit，否则数据不落盘
conn.close()     # 用完关闭连接
print(f"数据库创建完成：students_api.db，共插入 {len(students)} 名学生")
