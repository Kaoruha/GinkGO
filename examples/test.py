a = 10

for i in range(20):
    print(a+i)

from src.data.ginkgo_mongo import ginkgo_mongo as gm

s = gm.get_dayBar_by_mongo(code='sh.000001')
print(s)
