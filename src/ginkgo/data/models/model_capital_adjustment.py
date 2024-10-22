import pandas as pd
import datetime
from typing import Optional

from decimal import Decimal
from functools import singledispatchmethod
from sqlalchemy import Column, String, Integer, DECIMAL, Enum
from sqlalchemy.orm import Mapped, mapped_column

from ginkgo.data.models.model_clickbase import MClickBase
from ginkgo.libs import datetime_normalize, base_repr, Number, to_decimal
from ginkgo.enums import SOURCE_TYPES, CAPITALADJUSTMENT_TYPES


class MCapitalAdjustment(MClickBase):
    __abstract__ = False
    __tablename__ = "capital_adjustment"

    """
    'category', 'name', 'fenhong', 'peigujia'
    'songzhuangu', 'peigu', 'suogu', 'panqianliutong', 'panhouliutong',
    'qianzongguben', 'houzongguben', 'fenshu', 'xingquanjia'
    """

    code: Mapped[str] = mapped_column(String(32), default="ginkgo_test_code")
    type: Mapped[CAPITALADJUSTMENT_TYPES] = mapped_column(
        Enum(CAPITALADJUSTMENT_TYPES), default=CAPITALADJUSTMENT_TYPES.OTHER
    )
    fenhong: Mapped[Decimal] = mapped_column(DECIMAL(20, 8), default=0)
    peigujia: Mapped[Decimal] = mapped_column(DECIMAL(20, 8), default=0)
    songzhuangu: Mapped[Decimal] = mapped_column(DECIMAL(20, 8), default=0)
    peigu: Mapped[Decimal] = mapped_column(DECIMAL(20, 8), default=0)
    suogu: Mapped[Decimal] = mapped_column(DECIMAL(20, 8), default=0)
    panqianliutong: Mapped[Decimal] = mapped_column(DECIMAL(20, 8), default=0)
    panhouliutong: Mapped[Decimal] = mapped_column(DECIMAL(20, 8), default=0)
    qianzongguben: Mapped[Decimal] = mapped_column(DECIMAL(20, 8), default=0)
    houzongguben: Mapped[Decimal] = mapped_column(DECIMAL(20, 8), default=0)
    fenshu: Mapped[Decimal] = mapped_column(DECIMAL(20, 8), default=0)
    xingquanjia: Mapped[Decimal] = mapped_column(DECIMAL(20, 8), default=0)

    @singledispatchmethod
    def update(self, *args, **kwargs) -> None:
        raise NotImplementedError("Unsupported type")

    @update.register(str)
    def _(
        self,
        code: str,
        timestamp: Optional[any] = None,
        type: CAPITALADJUSTMENT_TYPES = None,
        fenhong: Optional[Number] = None,
        peigujia: Optional[Number] = None,
        songzhuangu: Optional[Number] = None,
        peigu: Optional[Number] = None,
        suogu: Optional[Number] = None,
        panqianliutong: Optional[Number] = None,
        panhouliutong: Optional[Number] = None,
        qianzongguben: Optional[Number] = None,
        houzongguben: Optional[Number] = None,
        fenshu: Optional[Number] = None,
        xingquanjia: Optional[Number] = None,
        source: Optional[SOURCE_TYPES] = None,
        *args,
        **kwargs,
    ) -> None:
        self.code = code
        if timestamp is not None:
            self.timestamp = datetime_normalize(timestamp)
        if type is not None:
            self.type = type
        if fenhong is not None:
            self.fenhong = to_decimal(fenhong)
        if peigujia is not None:
            self.peigujia = to_decimal(peigujia)
        if songzhuangu is not None:
            self.songzhuangu = to_decimal(songzhuangu)
        if peigu is not None:
            self.peigu = to_decimal(peigu)
        if suogu is not None:
            self.suogu = to_decimal(suogu)
        if panqianliutong is not None:
            self.panqianliutong = to_decimal(panqianliutong)
        if panhouliutong is not None:
            self.panhouliutong = to_decimal(panhouliutong)
        if qianzongguben is not None:
            self.qianzongguben = to_decimal(qianzongguben)
        if houzongguben is not None:
            self.houzongguben = to_decimal(houzongguben)
        if fenshu is not None:
            self.fenshu = to_decimal(fenshu)
        if xingquanjia is not None:
            self.xingquanjia = to_decimal(xingquanjia)
        if source is not None:
            self.source = source

    @update.register(pd.Series)
    def _(self, df: pd.Series, *args, **kwargs) -> None:
        self.code = df["code"]
        self.type = df["type"]
        self.fenhong = to_decimal(df["fenhong"])
        self.peigujia = to_decimal(df["peigujia"])
        self.songzhuangu = to_decimal(df["songzhuangu"])
        self.peigu = to_decimal(df["peigu"])
        self.suogu = to_decimal(df["suogu"])
        self.panqianliutong = to_decimal(df["panqianliutong"])
        self.panhouliutong = to_decimal(df["panhouliutong"])
        self.qianzongguben = to_decimal(df["qianzongguben"])
        self.houzongguben = to_decimal(df["houzongguben"])
        self.fenshu = to_decimal(df["fenshu"])
        self.xingquanjia = to_decimal(df["xingquanjia"])
        self.timestamp = datetime_normalize(df["timestamp"])
        if "source" in df.keys():
            self.source = df["source"]

    def __repr__(self) -> None:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 12, 46)
