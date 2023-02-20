import datetime
import pandas as pd
from sqlalchemy import (
    Float,
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
)
from ginkgo.data.models.base_model import BaseModel
from ginkgo.util.methdispatch import methdispatch
from ginkgo.libs import GINKGOLOGGER as gl


class DayBar(BaseModel):
    __abstract__ = False
    __tablename__ = "daybar"
    code = Column(String)
    name = Column(String)
    date = Column(DateTime)
    open_ = Column(Float)
    high_ = Column(Float)
    low_ = Column(Float)
    close_ = Column(Float)
    preclose_ = Column(Float)
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
        high_=0.0,
        low_=0.0,
        close_=0.0,
        preclose_=0.0,
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
        self.columns = [
            "date",
            "code",
            "open_",
            "high_",
            "low_",
            "close_",
            "preclose_",
            "volume",
            "amount",
            "adjust_flag",
            "turn",
            "trade_status",
            "pct_change",
            "is_st",
        ]
        setattr(self, "code", code)
        setattr(self, "date", date)
        setattr(self, "name", name)
        setattr(self, "open_", open_)
        setattr(self, "high_", high_)
        setattr(self, "low_", low_)
        setattr(self, "close_", close_)
        setattr(self, "preclose_", preclose_)
        setattr(self, "volume", volume)
        setattr(self, "amount", amount)
        setattr(self, "adjust_flag", adjust_flag)
        setattr(self, "turn", turn)
        setattr(self, "trade_status", trade_status)
        setattr(self, "pct_change", pct_change)
        setattr(self, "is_st", is_st)

    def to_dict(self):
        item = {}
        for i in self.columns:
            item[i] = self.__getattribute__(i)
        return item

    @methdispatch
    def df_convert(self, df):
        gl.logger.error("func() df_convert only support DataFrame and Series")

    @df_convert.register(pd.DataFrame)
    def _(self, df):
        for i in self.columns:
            setattr(self, i, df.loc[0, i])

    @df_convert.register(pd.core.series.Series)
    def _(self, df):
        for i in self.columns:
            setattr(self, i, df[i])

    def __repr__(self):
        s = "=" * 30
        s += "\nDaybar Info"
        for i in self.columns:
            s += f"\n{i} : {self.__getattribute__(i)}"
        s += "\n"
        s += "=" * 30
        return s
