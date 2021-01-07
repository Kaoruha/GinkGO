from mongoengine import Document, StringField, IntField, FloatField


class StockList(Document):
    date = StringField(20)
    code = StringField(20, primary_key=True)
    tradeStatus = IntField()
    code_name = StringField(20)

    