from mongoengine import Document, StringField, IntField, FloatField, BooleanField


class AdjustFactor(Document):
    code = StringField(max_length=20)
    date = StringField(max_length=20)
    divid_operate_date = StringField(max_length=40)
    fore_adjust_factor = FloatField()
    back_adjust_factor = FloatField()
    adjust_factor = FloatField()
    is_latest = BooleanField(default=True)
