from mongoengine import StringField, IntField, FloatField
from src.data.models.base_model import BaseModel


class Min5Bar(BaseModel):
    __abstract__ = True
    date = StringField(max_length=40)
    code = StringField(max_length=40)
    time = StringField(max_length=40, primary_key=True)
    open = FloatField()
    high = FloatField()
    low = FloatField()
    close = FloatField()
    volume = FloatField()
    amount = FloatField()
    adjust_flag = IntField()

    # meta = {'abstract': True}

    def __init__(
        self,
        date="0000/00/00",
        code="待插入指数代码",
        time="19991111093500000",
        open=0.0,
        high=0.0,
        low=0.0,
        close=0.0,
        volume=0,
        amount=0,
        adjust_flag=0,
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

        if time is None or time is "":
            self.time = "19991111093500000"
        else:
            self.time = str(time)

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
