import datetime
from mongoengine import Document, StringField, IntField, FloatField, BooleanField
from ginkgo_server.data.models.base_model import BaseModel


class DayBar(BaseModel):
    __abstract__ = True
    date = StringField(max_length=40)
    code = StringField(max_length=40)
    open = FloatField()
    high = FloatField()
    low = FloatField()
    close = FloatField()
    preclose = FloatField()
    volume = FloatField()
    amount = FloatField()
    adjust_flag = IntField()
    turn = FloatField()
    tradestatus = IntField()
    pct_change = FloatField()
    is_ST = StringField()

    # meta = {'abstract': True}

    def __init__(self,
                 date='0000/00/00',
                 code='待插入指数代码',
                 open=0.0,
                 high=0.0,
                 low=0.0,
                 close=0.0,
                 preclose=0.0,
                 volume=0,
                 amount=0,
                 adjust_flag=0,
                 turn=0.0,
                 trade_status=0,
                 pct_change=0.0,
                 is_ST=0,
                 *args,
                 **kwargs):
        BaseModel.__init__(self, *args, **kwargs)
        self.date = date
        self.code = code
        self.open = open
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
        self.is_ST = is_ST
