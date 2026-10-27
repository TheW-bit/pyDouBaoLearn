import pandas as pd

# 1. 创建表格：从字典创建 DataFrame
students = pd.DataFrame({                       # ① DataFrame（不是 DateFrame）
    "name":   ["张三", "李四", "王五", "赵六", "孙七"],
    "class":  ["A班", "A班", "B班", "B班", "A班"],
    "scores": [85, 58, 92, 45, 76]
})

# 2. 查看数据
print(students.head(2))       # 前 2 行
print(students.shape)         # (5, 3) → 5 行 3 列
print(students.describe())    # 统计摘要

# 3. 选取某一列
print(students["scores"])              # 单列 → Series
print(students[["name", "scores"]])    # 多列要两层方括号

# 4. 筛选不及格
failed = students[students["scores"] < 60]
print(failed)

# 5. 进阶：存成 CSV 再读回来
students.to_csv("students.csv", index=False)
df = pd.read_csv("students.csv")
print(df.head())
