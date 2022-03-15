import datetime
from src.data.models.base_model import BaseModel
from mongoengine import Document, StringField, IntField, FloatField, BooleanField


class AdjustFactor(BaseModel):
    code = StringField(max_length=20)
    divid_operate_date = StringField(max_length=40)
    fore_adjust_factor = FloatField()
    back_adjust_factor = FloatField()
    adjust_factor = FloatField()

    def __init__(
        self,
        code="sh.000000",
        divid_operate_date="0000/00/00",
        fore_adjust_factor=0.0,
        back_adjust_factor=0.0,
        adjust_factor=0.0,
        *args,
        **kwargs
    ):
        BaseModel.__init__(self)
        if code is None or code is "":
            self.code = "sh.000000"
        else:
            self.code = str(code)

        if divid_operate_date is None or divid_operate_date is "":
            self.code = "0000/00/00"
        else:
            self.divid_operate_date = str(divid_operate_date)

        if fore_adjust_factor is None or fore_adjust_factor is "":
            self.fore_adjust_factor = 0
        else:
            self.fore_adjust_factor = float(fore_adjust_factor)

        if back_adjust_factor is None or back_adjust_factor is "":
            self.back_adjust_factor = 0
        else:
            self.back_adjust_factor = float(back_adjust_factor)

        if adjust_factor is None or adjust_factor is "":
            self.adjust_factor = 0
        else:
            self.adjust_factor = float(adjust_factor)
