import datetime
from ginkgo_server.data.models.base_model import BaseModel
from mongoengine import Document, StringField, IntField, FloatField, BooleanField


class AdjustFactor(BaseModel):
    code = StringField(max_length=20)
    divid_operate_date = StringField(max_length=40)
    fore_adjust_factor = FloatField()
    back_adjust_factor = FloatField()
    adjust_factor = FloatField()

    def __init__(self,
                 code='sh.000000',
                 divid_operate_date='0000/00/00',
                 fore_adjust_factor=0.0,
                 back_adjust_factor=0.0,
                 adjust_factor=0.0,
                 *args,
                 **kwargs):
        BaseModel.__init__(self)
        self.code = code
        self.divid_operate_date = divid_operate_date
        self.fore_adjust_factor = fore_adjust_factor
        self.back_adjust_factor = back_adjust_factor
        self.adjust_factor = adjust_factor
        # 切换Collection
        # self.switch_collection(collection_name='stock_info')