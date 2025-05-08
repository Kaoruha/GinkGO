# import sys
# import unittest
# import datetime
# from time import sleep
# import pandas as pd
# from ginkgo.backtest.engines.engine_assembler_factory import *
# from ginkgo.data import get_engines


# class EngineAssembleTest(unittest.TestCase):
#     """
#     Test TDX data source
#     """

#     def __init__(self, *args, **kwargs) -> None:
#         super(EngineAssembleTest, self).__init__(*args, **kwargs)

#     def test_example_engine_assemble(self):
#         from ginkgo.data import init_example_data, fetch_and_update_cn_daybar, fetch_and_update_stockinfo

#         fetch_and_update_stockinfo()
#         fetch_and_update_cn_daybar("600594.SH", fast_mode=True)
#         fetch_and_update_cn_daybar("600000.SH", fast_mode=True)

#         init_example_data()
#         import time

#         time.sleep(2)
#         engine_name = "backtest_example"
#         engine_data = get_engines(name=engine_name)
#         if engine_data.shape[0] != 1:
#             print("Should have only one record about backtest_exampel, check the database.")
#         print(engine_data)
#         engine_id = engine_data.iloc[0]["uuid"]
#         assembler_backtest_engine(engine_id)
