import unittest
from src.backtest.event_engine import EventEngine
from src.libs import GINKGOLOGGER as gl
from src.data.data_engine import DataEngine


class TestDataEngine(unittest.TestCase):
    def reset(self):
        return DataEngine()

    def test_CheckCodeExist_OK(self):
        print("")
        gl.logger.critical("数据引擎检查代码测试开始")
        d = self.reset()
        params = [
            "sh.000005",
            "bj.871642",
            "sh.000001",
            "上证综合指数",
            "宁波能源",
            "建设机械",
            "sh.600987",
        ]
        for i in params:
            self.assertEqual(first=True, second=d.check_code_exist(i))

        gl.logger.critical("数据引擎检查代码测试完成:")

    def test_SaveToCache_OK(self):
        print("")
        gl.logger.critical("数据引擎缓存测试开始")
        d = self.reset()
        params = [
            "sh.000005",
            "sh.000001",
        ]
        count = 0
        for i in params:
            count += 1
            d.save_to_cache(code=i)
            self.assertEqual(first=count, second=len(d.data_cache))
        gl.logger.critical("数据引擎缓存测试完成:")

    def test_GetBarByCache_OK(self):
        print("")
        gl.logger.critical("数据引擎获取缓存数据测试开始")
        d = self.reset()
        params = [
            "sh.000005",
            "sh.000001",
        ]
        count = 0
        for i in params:
            count += 1
            d.save_to_cache(code=i)
            self.assertEqual(first=count, second=len(d.data_cache))
        params2 = [("sh.000001", "2020-01-21")]
        for i in params2:
            result = d.get_bar_by_cache(code=i[0], start=i[1], end=i[1])
            self.assertEqual(first=1, second=result.shape[0])

        gl.logger.critical("数据引擎获取缓存数据测试完成")

    def test_GetDaybar_OK(self):
        print("")
        gl.logger.critical("数据引擎获取数据测试开始")
        d = self.reset()
        eg = EventEngine()
        d.set_event_engine(eg)
        params = [
            ("sh.000005", 1),
            ("sh.000001", 2),
        ]
        for i in params:
            d.get_daybar(code=i[0], date="2020-01-21")
            self.assertEqual(first=i[1], second=eg._event_queue.qsize())
        gl.logger.critical("数据引擎获取数据测试完成")
