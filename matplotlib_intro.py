# -*- coding: utf-8 -*-
"""第三课作业：Matplotlib 三图 + 班级平均分进阶"""
import matplotlib
matplotlib.use("Agg")                 # ① 无窗口后端（我已写好示范）
import matplotlib.pyplot as plt
import pandas as pd
import os
os.makedirs("charts", exist_ok=True)

# ===== 填空 1：中文字体配置（必写，两行）=====
# 提示：plt.rcParams["font.sans-serif"] = ["SimHei"]
#       plt.rcParams["axes.unicode_minus"] = False
# 你的代码写在这里：
# ...
plt.rcParams["font.sans-serif"] = ["SimHei"]
plt.rcParams["axes.unicode_minus"] = False 



students = pd.read_csv("students.csv")

# ===== 必做 1：柱状图（学生成绩对比 + 及格线）=====
# 提示：plt.figure → plt.bar(姓名, 分数, color=?) → plt.axhline(60,...)
#       plt.title / plt.ylabel → plt.savefig("charts/bar_chart.png") → plt.close()
# 你的代码写在这里：
# ...
plt.figure(figsize=(8,4))
bars = plt.bar(students["name"], students["scores"], color="#4C9BE1")  # 绘制柱状图：x轴为学生姓名，y轴为学生分数，柱状颜色为天蓝色(#4C9BE1)
# 绘制及格线
plt.axhline(60, color="red", linestyle="--", linewidth=2)  # 及格线
# 添加标题和y轴标签
plt.ylabel("分数")
plt.title("学生成绩对比（柱状图）")
# 添加柱状图标签（姓名）
for bar, score in zip(bars, students["scores"]):
    plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
             str(score), ha="center", fontsize=9)   
# 保存图表
plt.savefig("charts/bar_chart.png", dpi=100)
plt.close()
print("已生成 charts/bar_chart.png")



# ===== 必做 2：折线图（一周学习时长）=====
days = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
minutes = [30, 45, 20, 60, 90, 120, 80]
# 提示：plt.plot(days, minutes, marker="?", color=?) → 存 charts/line_chart.png
# 你的代码写在这里：
# ...
plt.figure(figsize=(8,4))
plt.plot(days, minutes, marker="o", color="#52C41A")
plt.title("一周学习时长变化（折线图）")
plt.ylabel("分钟")
plt.savefig("charts/line_chart.png", dpi=100)
plt.close()
print("已生成 charts/line_chart.png")

# ===== 必做 3：散点图（学习时长 vs 成绩）=====
hours = [2, 3, 1, 5, 4, 6, 3, 7]
study_scores = [55, 62, 45, 78, 70, 85, 66, 92]
# 提示：plt.scatter(hours, study_scores, s=?) → 存 charts/scatter_chart.png
# 你的代码写在这里：
# ...
plt.figure(figsize=(8,4))
plt.scatter(hours, study_scores, color="#FA8C16", s=60)
plt.title("学习时长与成绩的关系（散点图）")
plt.xlabel("每周学习小时数")
plt.ylabel("成绩")
plt.savefig("charts/scatter_chart.png", dpi=100)
plt.close()
print("已生成 charts/scatter_chart.png")

# ===== 进阶：班级平均分柱状图 =====
# 提示：先 groupby 算平均（Pandas 第二课知识），再 plt.bar 画
#       class_avg = students.groupby("class")["scores"].mean()
#       存 charts/class_avg.png
# 你的代码写在这里：
# ...
class_avg = students.groupby("class")["scores"].mean() # 按班级分组，计算每个班级的平均分
plt.figure(figsize=(8,4))
avg_bars = plt.bar(class_avg.index, class_avg.values, color="#4C9BE1")
plt.title("班级平均分（柱状图）")
plt.ylabel("平均分")
for bar, avg in zip(avg_bars, class_avg.values):
    plt.text(bar.get_x() + bar.get_width() / 2, avg, str(avg), ha="center", fontsize=9) # 添加柱状图标签（平均分）, 居中对齐, 字体大小为9
plt.savefig("charts/class_avg.png", dpi=100) # 保存图表
plt.close()
print("已生成 charts/class_avg.png")