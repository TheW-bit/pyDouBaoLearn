# -*- coding: utf-8 -*-
"""SQL 入门作业：学生成绩库（sqlite3，零安装）"""
import sqlite3

# 1. 连接数据库（没有文件会自动创建 students.db）
conn = sqlite3.connect("students.db")
cur = conn.cursor() # 创建游标对象：是通过数据库连接（conn）生成的、用于执行SQL语句与获取查询结果的操作介质

# 2. 建表：students（id 主键、name、class、score）
cur.execute("""CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    class TEXT,
    score INTEGER
)""")

# 可重复运行：先清空表，避免每次运行重复插入 5 行
cur.execute("DELETE FROM students")

# 3. 插入第二课的 5 个学生（张三85/A班、李四58/A班、王五92/B班、赵六45/B班、孙七76/A班）
# 填空 1：用一条语句插 5 行（提示：executemany + 列表，占位符用 ?）
# 你的代码写在这里：
# ...
cur.executemany("INSERT INTO students (name, class, score) VALUES (?, ?, ?)",
                  [("张三", "A班", 85), ("李四", "A班", 58), ("王五", "B班", 92), ("赵六", "B班", 45), ("孙七", "A班", 76)]) # 插入 5 行数据
conn.commit() # 提交事务：将插入操作写入数据库文件


# 4. 查询全部学生
cur.execute("SELECT * FROM students")
# 填空 2：把结果取出来并逐行打印（提示：cur.fetchall() + for 循环）
# 你的代码写在这里：
# ...
for row in cur.fetchall():
    # 遍历查询结果，打印行数据
    print(row)



# 5. 查询不及格的学生（score < 60）
# 填空 3：补全 SQL 的 WHERE 条件，取结果并打印
# 你的代码写在这里：
# ...
cur.execute("SELECT * FROM students WHERE score < 60")  # 查询不及格的学生
failed_students = cur.fetchall()  # 取出查询结果
print("\n=== 不及格学生 ===")
for row in failed_students:
    # 遍历查询结果，打印行数据
    print(row)




    
# 6. 按班级统计平均分（GROUP BY + AVG，提示：这部分已给出，跑通后对照输出）
cur.execute("SELECT class, AVG(score) FROM students GROUP BY class")
print("\n=== 班级平均分 ===")
for row in cur.fetchall():
    print(f"{row[0]}班平均分: {row[1]}")    # 打印班级和平均分

# 提交事务 + 关闭连接
conn.commit()
conn.close()
