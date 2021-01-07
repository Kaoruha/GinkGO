from mongoengine import Document, StringField, IntField, FloatField


class DayBar(Document):
    date = StringField(20, primary_key=True)
    code = StringField(20)
    open = FloatField()
    high = FloatField()
    low = FloatField()
    close = FloatField()
    preclose = FloatField()
    volume = IntField()
    amount = IntField()
    adjustflag = IntField()
    turn = FloatField()
    tradestatus = IntField()
    pctChg = FloatField()
    isST = IntField()
