import datetime
from sqlalchemy import (
    Sequence,
    Column,
    Integer,
    String,
    Boolean,
    MetaData,
    DateTime,
)
from ginkgo.data.models.base_model import BaseModel


class StockInfo(BaseModel):
    __abstract__ = False
    __tablename__ = "stockinfo"
    code = Column(String)
    name = Column(String)
    trade_status = Column(Integer)
    has_min5 = Column(Boolean)
    # __table_args__ = (engines.MergeTree(order_by=["code"]),)

    def __init__(
        self,
        code="default code",
        trade_status=0,
        code_name="default name",
        *args,
        **kwargs,
    ):
        BaseModel.__init__(self, *args, **kwargs)
        self.code = code
        self.name = code_name
        self.trade_status = trade_status
        self.has_min5 = True

    def __repr__(self):
        s = BaseModel.__repr__(self)
        s += f"\ncode: {self.code}"
        s += f"\nname: {self.name}"
        s += f"\ntrade_status: {self.trade_status}"
        s += f"\nmin5: {self.has_min5}"
        return s


# class StockInfo(BaseModel):
#     code = StringField(max_length=20)
#     trade_status = IntField(default=0)
#     code_name = StringField(max_length=50)
#     has_min_bar = BooleanField(default=True)

#     def __init__(
#         self, code="待插入指数代码", trade_status=0, code_name="待插入指数名称", *args, **kwargs
#     ):
#         BaseModel.__init__(self, *args, **kwargs)
#         if code is None or code is "":
#             self.code = "待插入指数代码"
#         else:
#             self.code = str(code)

#         if trade_status is None or trade_status is "":
#             self.trade_status = 0
#         else:
#             self.trade_status = int(trade_status)

#         if code_name is None or code_name is "":
#             self.code_name = "待插入指数名称"
#         else:
#             self.code_name = str(code_name)

#         self.has_min_bar = True

#     def set_min_bar(self, has_min_bar=True):
#         """
#         设置是否有MinBar，通常用来将指数代码添加到黑名单，方便后续遍历时直接跳过
#         """
#         self.has_min_bar = has_min_bar
