from mongoengine import Document, StringField, IntField, FloatField, BooleanField


class DayBar(Document):
    date = StringField(max_length=40, primary_key=True)
    code = StringField(max_length=40)
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
