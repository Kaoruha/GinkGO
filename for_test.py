from ginkgo.data.ginkgo_data import GinkgoData
from ginkgo.enums import FREQUENCY_TYPES
from ginkgo.data.sources.ginkgo_baostock import GinkgoBaoStock
from ginkgo.data.drivers.ginkgo_clickhouse import GinkgoClickhouse
from ginkgo.libs.ginkgo_conf import GCONF

gd = GinkgoData()


# t = gd.get_bar_lastdate("sh.000002", FREQUENCY_TYPES.DAY)
# print(t)


# rs = gd.bs.fetch_cn_stock_daybar("sh.000066", "2000-01-01", "2023-01-01")
# rs = gd.bs.fetch_cn_stock_daybar("sh.600990", "2004-05-10", "2012-07-27")
# print(rs)


from ginkgo.backtest.matchmaknig.sim_matchmaking import MatchMaking_Sim

m = MatchMaking_Sim()
for i in range(20):
    print(m.ratio)
