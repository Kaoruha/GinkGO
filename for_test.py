from ginkgo.data.ginkgo_mongo import ginkgo_mongo as gm

d = gm.get_trade_day()
print(d)
# d = d[(d > "2020-01-01") & (d < "2020-01-22")]
# print(d)
# print(d.iloc[0])
print(d.shape[0])
print(len(d))
