import time
import datetime
from ginkgo.data.ginkgo_data import GINKGODATA
from ginkgo.data.models.order import Order

GINKGODATA.drop_all()
GINKGODATA.create_all()

s = []

t2 = datetime.datetime.now()
for i in range(100):
    s.append(Order())
    print(f"{i}/100", end="\r")

GINKGODATA.add_all(s)
GINKGODATA.commit()
t3 = datetime.datetime.now()
print(t3 - t2)

r = GINKGODATA.session.query(Order).first()
print(r)
