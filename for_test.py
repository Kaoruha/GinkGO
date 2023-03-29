import time
import datetime
from ginkgo.data.ginkgo_data import GINKGODATA
from ginkgo.data.models.model_order import MOrder
from ginkgo.data.models.model_daybar import MDaybar

GINKGODATA.drop_all()
GINKGODATA.create_all()

s = []

t2 = datetime.datetime.now()
for i in range(100):
    o = MDaybar()
    print(o)
    s.append(o)
    # o.dire = 2
    print(f"{i}/100", end="\r")

GINKGODATA.add_all(s)
GINKGODATA.commit()
t3 = datetime.datetime.now()
print(t3 - t2)

r = GINKGODATA.session.query(MDaybar).first()
print(r)
