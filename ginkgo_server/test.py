# from pymongo import MongoClient

# host = "127.0.0.1"
# client = MongoClient(host, 27017)
# # 连接mydb数据库,账号密码认证
# client["quant"].authenticate(
#     "ginkgo", "caonima123", mechanism="SCRAM-SHA-1"
# )  # 先连接系统默认数据库admin
# # 下面一条更改是关键，我竟然尝试成功了，不知道为啥，先记录下踩的坑吧
# # 让admin数据库去认证密码登录，好吧，既然成功了，
# # quant = client.db  # 再连接自己的数据库mydb
# collection = client["quant"]["stock_info"]  # myset集合，同上解释
# collection.insert({"name": "zhangsan", "age": 18})  # 插入一条数据，如果没出错那么说明连接成功
# for i in collection.find():
#     print(i)


# a = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
# print(a[8:12])

# for i in range(1):
#     print(i)

# import pandas as pd
# t = {'id':[1,2,3,4,5],'name':['Alice','Alice','Alice','Alice','Alice']}
# g = {'id':[6,7,8,9,10],'name':['Bob','Bob','Bob','Bob','Bob']}
# df1 = pd.DataFrame(data=t)
# df2 = pd.DataFrame(g)
# print(df1)
# print(df2)
# print('='*20)
# s = pd.concat([df1,df2],join='inner')
# print(s)

from ginkgo_server.libs.thread_manager import thread_manager as tm
tm.kill_all()