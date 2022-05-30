from ginkgo.data.ginkgo_mongo import ginkgo_mongo as gm
from ginkgo.data.stock.baostock_data import bao_instance as bi

code = "sh.600232"

rs = bi.get_data(
    code=code,
    data_frequency="5",
    start_date="2020-01-01",
    end_date="2022-05-05",
)
gm.update_min5(code, rs)
