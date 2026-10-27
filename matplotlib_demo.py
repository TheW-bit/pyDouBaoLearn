# -*- coding: utf-8 -*-
"""第三课 Matplotlib 示例：三种基本图（Agg 后端，保存到 charts 文件夹）"""
import os                                # 文件/文件夹操作标准库
import matplotlib
matplotlib.use("Agg")                    # ① 无窗口后端：不弹窗，直接存图（服务器/无 GUI 环境标配）
import matplotlib.pyplot as plt
import pandas as pd

# 确保图表文件夹存在（不存在就自动创建，避免保存时报错）
os.makedirs("charts", exist_ok=True)

# 中文字体配置（Windows 必配，否则中文会显示成方框）
plt.rcParams["font.sans-serif"] = ["SimHei"]   # 指定中文字体
plt.rcParams["axes.unicode_minus"] = False     # 负号正常显示

# 读回第二课生成的 CSV（把之前的成果直接用起来！）
students = pd.read_csv("students.csv")

# ===== 图 1：柱状图（对比） =====
plt.figure(figsize=(8, 4))
bars = plt.bar(students["name"], students["scores"], color="#4C9BE1")
plt.axhline(60, color="red", linestyle="--", linewidth=1)  # 及格线
plt.title("学生成绩对比（柱状图）")
plt.ylabel("分数")
for bar, score in zip(bars, students["scores"]):
    plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
             str(score), ha="center", fontsize=9)
plt.savefig("charts/bar_chart.png", dpi=100)   # ② 存图替代弹窗
plt.close()                                    # ③ 关闭画布，释放内存
print("已生成 charts/bar_chart.png")

# ===== 图 2：折线图（趋势） =====
days = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
minutes = [30, 45, 20, 60, 90, 120, 80]   # 每天学 Python 的分钟数（示例数据）
plt.figure(figsize=(8, 4))
plt.plot(days, minutes, marker="o", color="#52C41A")
plt.title("一周学习时长变化（折线图）")
plt.ylabel("分钟")
plt.savefig("charts/line_chart.png", dpi=100)
plt.close()
print("已生成 charts/line_chart.png")

# ===== 图 3：散点图（相关性） =====
hours = [2, 3, 1, 5, 4, 6, 3, 7]        # 每周学习小时数（示例数据）
scores = [55, 62, 45, 78, 70, 85, 66, 92]
plt.figure(figsize=(8, 4))
plt.scatter(hours, scores, color="#FA8C16", s=60)
plt.title("学习时长与成绩的关系（散点图）")
plt.xlabel("每周学习小时数")
plt.ylabel("成绩")
plt.savefig("charts/scatter_chart.png", dpi=100)
plt.close()
print("已生成 charts/scatter_chart.png")
