import time
import numpy as np
data = list(np.random.randint(0,100,1000000))
arr = np.array(data)
strat = time.time()
total1 = sum(data)
print("列表求和：",round(time.time() - strat,4),"秒")

strat = time.time()
total2 = arr.sum()
print("numpy求和：",round(time.time() - strat,4),"秒")
print("结果一致：",total1 == total2)
