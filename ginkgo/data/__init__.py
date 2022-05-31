# import pymongo

# mongo_client = pymongo.MongoClient("localhost", 27017)

# db = mongo_client.quant

# dblist = mongo_client.list_database_names()

# print(dblist)

# if "quant" in dblist:
#     print("quant已经存在")
# else:
#     print("quant不存在")

# db = mongo_client.quant
# factor = db['adjust_factor']

# for s in factor.find({},{'name':'hello2'}):
#     factor.update_one(s,{'$set':{'name':'hello22_new'}})

# for x in factor.find():
#     print(x)
#     factor.delete_one(x)

# for x in factor.find():
#     print(x)
