import unittest
from src.backtest.postion import Position
from src.backtest.sizer.base_sizer import BaseSizer


class PositionTest(unittest.TestCase):
    """
    持仓类单元测试
    """

    def __init__(self, *args, **kwargs):
        super(PositionTest, self).__init__(*args, **kwargs)
        self.code = 'test_01'
        self.name = 'test_position'
        self.price = 10.0
        self.volume = 10000
        self.date = '2000-01-01'

    def reset_position(self) -> Position:
        p = Position(
            code=self.code,
            name=self.name,
            cost=self.price,
            volume=self.volume,
            date=self.date
        )
        return p

    def test_PositionInit_OK(self) -> None:
        """
        初始化持仓实例
        """
        p = Position(
            code=self.code,
            cost=self.price,
            name=self.name,
            volume=self.volume,
            date=self.date
        )
        self.assertEqual(
            first={
                'code': self.code,
                'price': self.price,
                'name': self.name,
                'volume': self.volume,
                't1frozen': self.volume,
                'date': self.date
            },
            second={
                'code': p.code,
                'price': p.market_price,
                'name': p.name,
                'volume': p.volume,
                't1frozen': p.t1frozen,
                'date': p.date
            }
        )

