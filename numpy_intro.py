import numpy as np

# 成绩数据
students = [
    {"name": "张三", "scores": 80},
    {"name": "李四", "scores": 95},
    {"name": "王五", "scores": 75},
    {"name": "赵六", "scores": 90},
    {"name": "孙七", "scores": 55}
]

# 把成绩转换成numpy数组
score_list = [s["scores"] for s in students]
score_array = np.array(score_list)  # numpy数组,就这一句

# 使用np的方法计算 平均值，最高分，最低分
average_score = score_array.mean()
max_score = score_array.max()
min_score = score_array.min()

# 不及格
failed = score_array[score_array < 60]

print("平均分：", average_score)
print("最高分：", max_score)
print("最低分：", min_score)
print("不及格：", failed)