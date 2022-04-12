"""
Author: Kaoru
Date: 2022-03-22 22:14:51
LastEditTime: 2022-04-03 01:08:53
LastEditors: Kaoru
Description: Be stronger,be patient,be confident and never say die.
FilePath: /Ginkgo/test/test_analyzer.py
What goes around comes around.
"""
import unittest
from src.backtest.analyzer.benchmark import BenchMark
from src.backtest.broker.base_broker import BaseBroker
from src.libs import GINKGOLOGGER as gl


class AnalyzerTest(unittest.TestCase):
    """
    分析类单元测试
    """

    def __init__(self, *args, **kwargs) -> None:
        super(AnalyzerTest, self).__init__(*args, **kwargs)

    def test_BenchMarkInit_OK(self):
        gl.logger.critical("BenchMark初始化测试开始.")
        param = [
            # 0name, 1target
            ("沪深300", "sh.000300"),
            ("沪市", "sh.000001"),
        ]
        for i in param:
            a = BenchMark(name=i[0], target=i[1])
            gl.logger.debug(a)
            self.assertEqual(
                first={"name": i[0], "tar": i[1]},
                second={"name": a.name, "tar": a.target},
            )
        gl.logger.critical("BenchMark初始化测试完成.")

    def test_BenchMarkRecord_OK(self):
        gl.logger.critical("BenchMark记录测试开始.")
        a = BenchMark()
        b = BaseBroker()
        a.record(timestamp="2019-01-11", broker=b)
        print(a.raw)
        gl.logger.critical("BenchMark记录测试完成.")

    def test_BenchMarkReport_OK(self):
        gl.logger.critical("BenchMark报告测试开始.")
        gl.logger.critical("BenchMark报告测试完成.")
