import unittest
import datetime
from src.libs import GINKGOLOGGER as gl
from src.backtest.selector.random_selector import RandomSelector


class SelectorTest(unittest.TestCase):
    """
    选股模块类单元测试
    """

    def __init__(self, *args, **kwargs) -> None:
        super(SelectorTest, self).__init__(*args, **kwargs)

    def test_RNDSelectorInit_OK(self):
        print("")
        gl.logger.critical("RandomSelector初始化测试开始.")
        param = [
            # 0interval, 1count
            (0, 5),
            (2, 2),
            (10, 3),
        ]
        today = "2020-01-01"
        for i in param:
            s = RandomSelector(interval=i[0], count=i[1])
            if i[0] == 0:
                s.get_result(today=today)
                self.assertEqual(first={"count": i[1]}, second={"count": len(s.result)})
            else:
                r = s.get_result(today=today)
                for j in range(5):
                    for k in range(i[0]):
                        oldday = datetime.datetime.strptime(today, "%Y-%m-%d")
                        newday = oldday + datetime.timedelta(days=1)
                        today = newday.strftime("%Y-%m-%d")
                        s.get_result(today=today)
                    self.assertNotEqual(first=r, second=s.result)
                    r = s.result
                gl.logger.info(s.history)
        gl.logger.critical("RandomSelector初始化测试完成.")
