"""
2.12 配套：把 SQLite 的 20 人数据迁移到 MySQL
================================================
思路：
  1. 从 SQLite students_api.db 读全部学生（裸 sqlite3）
  2. 用 SQLAlchemy 把它们批量写进 MySQL 的 students 表

运行：venv/Scripts/python migrate_to_mysql.py
"""
import sqlite3
from sqlalchemy import select
from sqlalchemy.orm import Session
from orm_mysql import engine, Base, Student   # 复用 orm_mysql.py 的 engine 和模型

# ① 从 SQLite 读 20 人
conn = sqlite3.connect("students_api.db")
conn.row_factory = sqlite3.Row
rows = conn.execute("SELECT name, class, score FROM students").fetchall()
conn.close()
print(f"从 SQLite 读到 {len(rows)} 人")

# ② 确保 MySQL 里表存在
Base.metadata.create_all(engine)

# ③ 写进 MySQL（ORM 版）
with Session(engine) as session:
    # 先看 MySQL 里有没有数据，避免重复插入
    existing = len(session.scalars(select(Student)).all())
    if existing > 0:
        print(f"MySQL 已有 {existing} 人，跳过迁移（防止重复插入）")
    else:
        for row in rows:
            session.add(Student(
                name=row["name"],
                class_=row["class"],
                score=row["score"],
            ))
        session.commit()
        print(f"✅ 已写入 MySQL {len(rows)} 人")

# ④ 验证：MySQL 里查一下
with Session(engine) as session:
    students = session.scalars(select(Student)).all()
    print(f"\nMySQL 现在共 {len(students)} 人，前 3 个：")
    for s in students[:3]:
        print(f"  id={s.id}  {s.name}  {s.class_}  {s.score}")
