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
        self.date = '2020-01-01'

    def update_price(self):
        return (12.0,'2020-01-02')

    def reset_position(self, is_t1) -> Position:
        p = Position(
            is_t1=is_t1,
            code=self.code,
            name=self.name,
            cost=self.price,
            volume=self.volume,
            date=self.date
        )
        return p

    def test_PositionInitT1_OK(self) -> None:
        """
        初始化持仓实例
        """
        # TODO ist1 false的情况回头需要补上
        p = Position(
            code=self.code,
            cost=self.price,
            name=self.name,
            volume=self.volume,
            date=self.date
        )
        print(p)
        self.assertEqual(
            first={
                'code': self.code,
                'price': self.price,
                'name': self.name,
                'volume': self.volume,
                't1frozen': self.volume,
                'sellfrozen': 0,
                'avaliable':0,
                'date': self.date
            },
            second={
                'code': p.code,
                'price': p.last_price,
                'name': p.name,
                'volume': p.volume,
                't1frozen': p.frozen_t1,
                'sellfrozen': p.frozen_sell,
                'avaliable': p.avaliable_volume,
                'date': p.date
            }
        )

    def test_UpdateDate_OK(self) -> None:
        param = [
            ('2020-01-02', '2020-01-02'),
            ('2020-02-01', '2020-02-01'),
            ('2021-01-01', '2021-01-01'),
        ]
        for i in param:
            p = self.reset_position(is_t1=True)
            p.update_date(i[0])
            self.assertEqual(
                first={
                    'date':i[1]
                },
                second={
                    'date':p.date
                }
            )

    def test_UpdateDate_FAILED(self) -> None:
        # TODO 日期有效性还需要校验
        param = [
            ('2019-01-01', '2020-01-01'),
            ('2019-02-01', '2020-01-01'),
            ('2020', '2020-01-01'),
        ]
        for i in param:
            p = self.reset_position(is_t1=True)
            p.update_date(i[0])
            self.assertEqual(
                first={
                    'date':i[1]
                },
                second={
                    'date':p.date
                }
            )

    def test_UpdatePrice_OK(self) -> None:
        p = self.reset_position(is_t1=True)
        param = [
            (11, '2020-01-01', 10, '2020-01-01'),
            (10.5, '2020-01-02', 10.5, '2020-01-02'),
            (11.1, '2020-01-03', 11.1, '2020-01-03'),
            (13.6, '2020-02-01', 13.6, '2020-02-01')
        ]
        for i in param:
            p.update_last_price(price=i[0], date=i[1])
            self.assertEqual(
                first={
                    'price':i[2],
                    'date': i[3],
                    'total': i[2] * self.volume
                },
                second={
                    'date': p.date,
                    'price':p.last_price,
                    'total': p.market_value
                }
            )


    # def test_UnfreezeT1_OK(self) -> None:
    #     p = self.reset_position(is_t1=True)
    #     self.assertEqual(
    #         first={
    #             'code': self.code,
    #             'price': self.price,
    #             'name': self.name,
    #             'volume': self.volume,
    #             't1frozen': self.volume,
    #             'sellfrozen': 0,
    #             'avaliable':0,
    #             'date': self.date,
    #             'total':self.volume * self.price
    #         },
    #         second={
    #             'code': p.code,
    #             'price': p.last_price,
    #             'name': p.name,
    #             'volume': p.volume,
    #             't1frozen': p.frozen_t1,
    #             'sellfrozen': p.frozen_sell,
    #             'avaliable': p.avaliable_volume,
    #             'date': p.date,
    #             'total':p.market_value
    #         }
    #     )
    #     up = self.update_price()
    #     p.update_last_price(up[0], up[1])
    #     self.assertEqual(
    #         first={
    #             'price':up[0],
    #             'date':up[1],
    #             'volume':self.volume,
    #             't1frozen':0,
    #             'sellfrozen':0,
    #             'avaliable':self.volume,
    #             'total':self.volume * up[0]
    #         },
    #         second={
    #             'price':p.last_price,
    #             'date':p.date,
    #             'volume':p.volume,
    #             't1frozen':p.frozen_t1,
    #             'sellfrozen':p.frozen_sell,
    #             'avaliable':p.avaliable_volume,
    #             'total':p.market_value
    #         }
    #     )

    # def test_PreSell_OK(self) -> None:
    #     param = [
    #         (True, 1000, '2020-01-01')
    #     ]
    #     for i in param:
    #         p = self.reset_position(is_t1=i[0])
    #         p.pre_sell(volume=i[1], date=i[2])
    #         self.assertEqual(
    #             first={
    #                 'code': self.code,
    #                 'name': self.name,
    #                 'volume': self.volume,
    #             },
    #             second={
    #                 'code': self.code,
    #                 'name': self.name,
    #                 'volume': self.volume,
    #             }
    #         )

    # def test_PreSell_FAILED(self) -> None:
    #     pass
