"""
进阶题：100 万个数求和，Python 列表 vs NumPy，谁快？
运行：python numpy_speed.py
"""
import time
import numpy as np

# 1. 生成 100 万个 0~99 的随机整数
data = list(np.random.randint(0, 100, 1000000))  # np 生成 → 转成列表
arr = np.array(data)                              # 列表转回数组（对照组）

# 2. 列表求和：Python 一个个加
start = time.time()
total1 = sum(data)                                # 内置 sum 逐个累加
time_list = time.time() - start

# 3. NumPy 求和：底层 C 语言整批算
start = time.time()
total2 = arr.sum()                                # 数组方法，一次算完
time_numpy = time.time() - start

print(f"列表求和: {time_list:.4f} 秒, 结果 {total1}")
print(f"NumPy求和: {time_numpy:.4f} 秒, 结果 {total2}")
print(f"结果一致: {total1 == total2}")
print(f"NumPy 快了 {time_list / time_numpy:.1f} 倍")
