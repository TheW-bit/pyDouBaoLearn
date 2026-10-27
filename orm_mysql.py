"""
2.12：SQLAlchemy 连 MySQL（对比 orm_intro.py 的 SQLite 版）
=========================================================
和 SQLite 版唯一的区别就是 engine 那一行（数据库 URL），
其他模型/查询/写操作代码完全一样 —— 这就是 ORM 的好处。

运行：venv/Scripts/python orm_mysql.py
前置：MySQL 已启动，root/123456，数据库 students_api 已建
"""
from sqlalchemy import create_engine, select, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session

# ── 关键区别：MySQL 连接串 ──
# 格式：mysql+pymysql://用户名:密码@地址:端口/库名?charset=utf8mb4
# pymysql 是驱动（刚才 pip install 的），其余和 SQLite 版一样
engine = create_engine(
    "mysql+pymysql://root:123456@localhost:3306/students_api?charset=utf8mb4",
    echo=False   # True 会打印生成的 SQL，调试用
)


class Base(DeclarativeBase):
    pass


# Student 模型和 orm_intro.py 一模一样（ORM 让代码复用）
class Student(Base):
    """映射 MySQL students_api 库里的 students 表"""
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # ⚠️ MySQL 要求 VARCHAR 指定长度（SQLite 的 TEXT 不用），这是和 SQLite 版的唯一模型差异
    name: Mapped[str] = mapped_column(String(50))
    class_: Mapped[str] = mapped_column("class", String(20))
    score: Mapped[int]


if __name__ == "__main__":
    # 1. 建表（MySQL 里还没有 students 表，这一行自动建）
    #    对比 SQLite 版：SQLite 表是 init_db.py 建的，这里 ORM 自己建
    Base.metadata.create_all(engine)
    print("✅ MySQL students 表已就绪（不存在则创建）")

    # 2. 测试：查一下当前有多少人
    with Session(engine) as session:
        count = len(session.scalars(select(Student)).all())
        print(f"当前 MySQL students 表有 {count} 人")
