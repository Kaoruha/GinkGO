import datetime
from sqlalchemy import (
    Float,
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
)
from ginkgo.data.models.base_model import BaseModel


class DayBar(BaseModel):
    __abstract__ = False
    __tablename__ = "daybar"
    code = Column(String)
    name = Column(String)
    date = Column(DateTime)
    open_ = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    preclose = Column(Float)
    volume = Column(Float)
    amount = Column(Float)
    adjust_flag = Column(Integer)
    turn = Column(Float)
    trade_status = Column(Integer)
    pct_change = Column(Float)
    is_st = Column(Integer)

    def __init__(
        self,
        date=datetime.datetime(2000, 1, 1, 0, 0, 0),
        code="defaultcode",
        name="defaultname",
        open_=0.0,
        high=0.0,
        low=0.0,
        close=0.0,
        preclose=0.0,
        volume=0.0,
        amount=0.0,
        adjust_flag=0,
        turn=0.0,
        trade_status=0,
        pct_change=0.0,
        is_st=0,
        *args,
        **kwargs,
    ):
        BaseModel.__init__(self, *args, **kwargs)
        self.date = date
        self.code = code
        self.name = name
        self.open_ = open_
        self.high = high
        self.low = low
        self.close = close
        self.preclose = preclose
        self.volume = volume
        self.amount = amount
        self.adjust_flag = adjust_flag
        self.turn = turn
        self.trade_status = trade_status
        self.pct_change = pct_change
        self.is_st = is_st

    def to_dict(self):
        keys = [
            "date",
            "code",
            "open",
            "high",
            "low",
            "close",
            "preclose",
            "volume",
            "amount",
            "adjust_flag",
            "turn",
            "trade_status",
            "pct_change",
            "is_st",
        ]
        item = {}
        for i in keys:
            item[i] = self.__getattribute__(i)
        return item

    def __repr__(self):
        s = "=" * 30
        s += "\nDaybar"
        s += f"\n     code: {self.code}"
        s += f"\n     date: {self.date}"
        s += f"\n     open: {self.open_}"
        s += f"\n     high: {self.high}"
        s += f"\n      low: {self.low}"
        s += f"\n    close: {self.close}"
        s += f"\n preclose: {self.preclose}"
        s += f"\n   volume: {self.volume}"
        s += f"\n   amount: {self.amount}"
        s += f"\n pct_change: {self.pct_change}"
        s += "\n"
        s += "=" * 30
        return s
