import datetime
from mongoengine import Document, StringField, IntField, FloatField, BooleanField
from ginkgo_server.data.models.base_model import BaseModel


class StockInfo(BaseModel):
    code = StringField(max_length=20)
    trade_status = IntField(default=0)
    code_name = StringField(max_length=50)
    has_min_bar = BooleanField(default=True)

    def __init__(self,
                 code='待插入指数代码',
                 trade_status=0,
                 code_name='待插入指数名称',
                 *args,
                 **kwargs):
        BaseModel.__init__(self, *args, **kwargs)
        self.code = code
        self.trade_status = trade_status
        self.code_name = code_name
        self.has_min_bar = True
        # 切换Collection
        # base_classes = self.__class__.__bases__ or ()
        # base_class_names = ".".join(_.__name__ for _ in base_classes)
        # super(StockInfo, self).__init__()
        # self._cls = "{}.{}".format(base_class_names, self.__class__.__name__).strip(".")

    def set_min_bar(self, has_min_bar=True):
        """
        设置是否有MinBar，通常用来将指数代码添加到黑名单，方便后续遍历时直接跳过
        """
        self.has_min_bar = has_min_bar