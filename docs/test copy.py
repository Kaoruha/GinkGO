import numpy as np


# a = np.full((2, 3), 0.0, dtype=np.float)
# print(a)
# # for i in range(a.shape[1]):
# #     a[0,i]=3
# a[0,4] = 22

# print(a)
a_length = 2
b_length = 2
for i in range(a_length):
    for r in range(b_length):
        old = i * b_length
        s = old + r
        print(s)