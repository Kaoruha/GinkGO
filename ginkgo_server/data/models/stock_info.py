from mongoengine import Document, StringField, IntField, FloatField, BooleanField


class StockInfo(Document):
    date = StringField(max_length=40)
    code = StringField(max_length=20)
    trade_status = IntField()
    code_name = StringField(max_length=50)
    has_min_bar = BooleanField()

    # meta = {'collection': code}
