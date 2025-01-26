# THe class will support db connection, based on sqlalchemy
# Mongodb, Clickhouse, etc

from ginkgo.data.drivers import create_redis_connection
import datetime

key = "tick_update_99991.SZ1"
date = "2020-01-01"
date2 = "2020-01-02"
r = create_redis_connection()
r.sadd(key, date)
r.sadd(key, date2)
r.expire(key, 60)
t0 = datetime.datetime.now()
# for i in range(10000000):
#     res = r.smembers(key)
#     t1 = datetime.datetime.now()
#     avg = (t1-t0)/ (i+1)
#     print(f"count: {i+1} avg: {avg}")

data = r.smembers(key)
new_data = {item.decode('utf-8') for item in data}
print(new_data)
for i in range(10000000):
    exists = date in new_data
    print(f"Element exists: {exists}")
    t1 = datetime.datetime.now()
    avg = (t1-t0)/ (i+1)
    print(f"count: {i+1} avg: {avg}")

