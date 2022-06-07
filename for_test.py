from ginkgo.data.ginkgo_mongo import GinkgoMongo
from ginkgo.config.secure import HOST, PORT, USERNAME, PASSWORD, DATABASE

gm = GinkgoMongo(
    host=HOST, port=PORT, username=USERNAME, password=PASSWORD, database=DATABASE
)
print(gm)

codelist = gm.get_all_stockcode_by_mongo()
print(codelist)

code = codelist["code"][0]
print(code)


lastdate = gm.get_daybar_latestDate_by_mongo(code)
print(lastdate)
