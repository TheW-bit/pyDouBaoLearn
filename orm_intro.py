"""
第五课：SQLAlchemy ORM 入门
============================
ORM（Object-Relational Mapping，对象关系映射）：
  把数据库里的「表」映射成 Python 里的「类」，
  把「一行记录」映射成「一个对象」。
  好处：不用手写 SQL 字符串，用 Python 对象和方法操作数据库。

对照第四课的裸 SQL：
  裸 SQL：  cur.execute("SELECT * FROM students WHERE score < 60")
  ORM：    select(Student).where(Student.score < 60)   ← 直接写 Python

运行：venv/Scripts/python orm_intro.py
"""

# ── 导入 SQLAlchemy 的工具 ──
# create_engine：创建「引擎」，负责连接数据库
# select：生成查询语句对象（相当于 SELECT）
# DeclarativeBase：所有表模型的公共基类
# Mapped / mapped_column：给字段加类型注解，自动映射成数据库列
# Session：会话，一次数据库操作的工作区（相当于 cursor 的升级版）
from sqlalchemy import create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session


# ① 引擎：告诉 SQLAlchemy 连接哪个数据库
#    sqlite:///students_api.db 表示用当前目录下的 SQLite 文件
#    （换成 MySQL 只改这一行，其他代码不动——这就是 ORM 的好处）
engine = create_engine("sqlite:///students_api.db")


# ② 模型基类：我们的表模型都要继承它
#    SQLAlchemy 通过它认识所有模型、建表、做映射
class Base(DeclarativeBase):
    pass


# 填空 1：定义 Student 模型（一张表 = 一个 Python 类）
class Student(Base):
    """映射 students 表（第四课已建好，这里只做映射，不重建）"""

    __tablename__ = "students"          # 这个类对应数据库里哪张表

    # 字段映射：类的属性 = 表的列
    # id：主键，整数，自动递增（数据库自动生成 id）
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # name：字符串列
    name: Mapped[str]
    # class_：注意 class 是 Python 关键字不能当变量名，
    # 用 class_ 当 Python 属性名，mapped_column("class") 指定它映射到表里的 class 列
    class_: Mapped[str] = mapped_column("class")
    # score：整数列
    score: Mapped[int]


# ③ 查询全部学生
#    对照裸 SQL：SELECT * FROM students
def get_all():
    # with Session(engine)：开一个会话（用完自动关闭，和 with open 一样）
    with Session(engine) as session:
        # select(Student) 相当于 SELECT * FROM students
        # .scalars() 把每行结果转成 Student 对象（而不是原始元组）
        # .all() 取出全部 → 返回 list[Student]
        return session.scalars(select(Student)).all()


# 填空 2：查询不及格学生
#    对照裸 SQL：SELECT * FROM students WHERE score < 60
def get_failed():
    with Session(engine) as session:
        # .where(Student.score < 60) 相当于 WHERE score < 60
        # Student.score 是类属性，不是某个对象的分数，ORM 会把它翻译成 SQL 条件
        return session.scalars(
            select(Student).where(Student.score < 60)
        ).all()


# 填空 3：新增一个学生
#    对照裸 SQL：INSERT INTO students (name, class, score) VALUES (...)
#              + conn.commit()
def add_student():
    with Session(engine) as session:
        # 1. 造一个 Student 对象 = 造一条新记录
        new = Student(name="ORM新生", class_="A班", score=77)
        # 2. session.add() 把对象加入会话（相当于准备 INSERT，但还没真的写进库）
        session.add(new)
        # 3. session.commit() 提交事务——这步才真正写入数据库
        #    （和裸 SQL 一样，写操作必须 commit，不 commit = 没保存）
        session.commit()
        # 4. 提交后，数据库自动生成的自增 id 会回填到 new.id 上
        return new.id


# ── 主程序：运行时执行下面的代码 ──
#    __name__ == "__main__" 表示这个文件被直接运行时才执行
if __name__ == "__main__":
    # get_all() 返回 Student 对象列表，用列表推导式取出 id/name/score 打印
    print("全部学生：", [(s.id, s.name, s.score) for s in get_all()])
    print("不及格：", [(s.name, s.score) for s in get_failed()])
    print("新增学生 id：", add_student())
    print("新增后共：", len(get_all()), "人")
