import unittest
import random
import datetime
import pandas as pd
from decimal import Decimal

from ginkgo.backtest.entities.adjustfactor import Adjustfactor

# TODO AI Gen need check


class TestAdjustfactor(unittest.TestCase):
    def setUp(self):
        # 预生成一组随机参数字典
        self.param_list = []
        for _ in range(random.randint(5, 10)):
            param = {
                "code": f"code_{random.randint(1000, 9999)}",
                "timestamp": datetime.datetime(
                    random.randint(1990, 2030),
                    random.randint(1, 12),
                    random.randint(1, 28),
                ),
                "fore_adjustfactor": random.uniform(0.1, 10),
                "back_adjustfactor": random.uniform(0.1, 10),
                "adjustfactor": random.uniform(0.1, 10),
            }
            self.param_list.append(param)

    def test_create_by_params(self):
        # 测试通过直接参数创建实例
        for param in self.param_list:
            obj = Adjustfactor(**param)
            self.assertEqual(obj.code, param["code"])
            self.assertEqual(obj.timestamp, param["timestamp"])
            self.assertEqual(obj.fore_adjustfactor, Decimal(str(param["fore_adjustfactor"])))
            self.assertEqual(obj.back_adjustfactor, Decimal(str(param["back_adjustfactor"])))
            self.assertEqual(obj.adjustfactor, Decimal(str(param["adjustfactor"])))

    def test_create_by_series(self):
        # 测试通过 pd.Series 创建实例
        for param in self.param_list:
            series = pd.Series(param)
            obj = Adjustfactor()
            obj.set(series)
            self.assertEqual(obj.code, param["code"])
            self.assertEqual(obj.timestamp, param["timestamp"])
            self.assertEqual(obj.fore_adjustfactor, Decimal(str(param["fore_adjustfactor"])))
            self.assertEqual(obj.back_adjustfactor, Decimal(str(param["back_adjustfactor"])))
            self.assertEqual(obj.adjustfactor, Decimal(str(param["adjustfactor"])))
