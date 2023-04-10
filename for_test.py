from ginkgo.data.ginkgo_data import GINKGODATA
from ginkgo.data.models.model_order import MOrder
from ginkgo.backtest.event.capital_update import EventCapitalUpdate


GINKGODATA.drop_table(MOrder)
GINKGODATA.create_table(MOrder)
o = MOrder()
GINKGODATA.add(o)
GINKGODATA.commit()
uuid = o.uuid
e = EventCapitalUpdate()
e.get_order(uuid)
print(e)
