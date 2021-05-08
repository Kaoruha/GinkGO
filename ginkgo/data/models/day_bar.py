from mongoengine import StringField, IntField, FloatField
from ginkgo.data.models.base_model import BaseModel


class DayBar(BaseModel):
    __abstract__ = True
    date = StringField(max_length=40, primary_key=True)
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
    is_ST = IntField()

    # meta = {'abstract': True}

    def __init__(
        self,
        date="0000/00/00",
        code="待插入指数代码",
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
        **kwargs
    ):
        BaseModel.__init__(self, *args, **kwargs)

        if date is None or date is "":
            self.date = "0000/00/00"
        else:
            self.date = str(date)

        if code is None or code is "":
            self.code = "待插入指数代码"
        else:
            self.code = str(code)

        if open is None or open is "":
            self.open = 0.0
        else:
            self.open = float(open)

        if high is None or high is "":
            self.high = 0.0
        else:
            self.high = float(high)

        if low is None or low is "":
            self.low = 0.0
        else:
            self.low = float(low)

        if close is None or close is "":
            self.close = 0.0
        else:
            self.close = float(close)

        if preclose is None or preclose is "":
            self.preclose = 0.0
        else:
            self.preclose = float(preclose)

        if volume is None or volume is "":
            self.volume = 0
        else:
            self.volume = float(volume)

        if amount is None or amount is "":
            self.amount = 0
        else:
            self.amount = float(amount)

        if adjust_flag is None or adjust_flag is "":
            self.adjust_flag = 0
        else:
            self.adjust_flag = int(adjust_flag)

        if turn is None or turn is "":
            self.turn = 0.0
        else:
            self.turn = float(turn)

        if trade_status is None or trade_status is "":
            self.trade_status = 0.0
        else:
            self.trade_status = int(trade_status)

        if pct_change is None or pct_change is "":
            self.pct_change = 0.0
        else:
            self.pct_change = float(pct_change)

        if is_ST is None or is_ST is "":
            self.is_ST = 0
        else:
            self.is_ST = int(is_ST)
