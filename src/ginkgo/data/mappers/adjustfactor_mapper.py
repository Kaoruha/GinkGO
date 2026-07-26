"""AdjustfactorMapper — Adjustfactor Entity ↔ MAdjustfactor ORM 转换（ADR-010）。

承接原 Adjustfactor.to_model / Adjustfactor.from_model 内嵌逻辑
（entities/adjustfactor.py:134-159）。无 AdjustfactorDTO（项目未定义），
故只提供 to_model / from_model / from_models 三方法。

VO 动态表：to_model 多 model_class 形参，方法体内 model_class(...) 构造。
to_model 忠实原码：model_class(code=..., timestamp=..., fore_adjustfactor=...,
back_adjustfactor=..., adjustfactor=..., uuid=...)。
from_model 还原 uuid（原码即如此，无丢失）。

已知问题（留 Task 1.6 抹内嵌方法时统一评估，本 Mapper 不擅自修）：
- 原 to_model 传 fore_adjustfactor/back_adjustfactor（带下划线），但
  MAdjustfactor 字段名是 foreadjustfactor/backadjustfactor（无下划线），
  且 MAdjustfactor 无自定义 __init__，继承 MClickBase.__init__ 用 hasattr
  setattr——三字段名不匹配被静默丢弃。code/timestamp/uuid 字段名匹配故保真。

铁律：不 import CRUD；不含 to_dataframe（DF 出口留 CRUD）。
"""
from typing import List

from ginkgo.data.models import MAdjustfactor
from ginkgo.entities import Adjustfactor
from ginkgo.enums import SOURCE_TYPES
from ginkgo.libs import to_decimal, datetime_normalize


class AdjustfactorMapper:
    """Adjustfactor 双态互转。无状态，全部静态方法。"""

    # ------------------------------------------------------------------
    # Entity ↔ ORM
    # ------------------------------------------------------------------
    @staticmethod
    def to_model(entity: Adjustfactor, model_class=MAdjustfactor) -> MAdjustfactor:
        """Entity → ORM。ADR-029 阶段1:逐字段对齐 AdjustfactorCRUD._convert_input_item(strict mirror)。

        kwarg 改无下划线 foreadjustfactor/backadjustfactor(匹配 MAdjustfactor 字段名,修原带下划线
        被 MClickBase hasattr setattr 静默丢弃)。值用 getattr(entity,'foreadjustfactor',1.0)
        镜像 CRUD 占位策略:entity 属性实为 fore_adjustfactor(带下划线),getattr 'foreadjustfactor'
        取不到走默认 1.0——恒 1.0 是有意入库占位(后续计算覆盖,非 bug)。加 source(validate_input
        getattr 'source' public 属性默认 TUSHARE);timestamp datetime_normalize;去 uuid(镜像 CRUD
        不塞)。model_class 形参保留(VO 动态表选择)。
        """
        return model_class(
            code=entity.code,
            timestamp=datetime_normalize(entity.timestamp),
            foreadjustfactor=to_decimal(getattr(entity, 'foreadjustfactor', 1.0)),
            backadjustfactor=to_decimal(getattr(entity, 'backadjustfactor', 1.0)),
            adjustfactor=to_decimal(getattr(entity, 'adjustfactor', 1.0)),
            source=SOURCE_TYPES.validate_input(getattr(entity, 'source', SOURCE_TYPES.TUSHARE)),
        )

    @staticmethod
    def from_model(model: MAdjustfactor) -> Adjustfactor:
        """ORM → Entity。还原 uuid（原码即如此，无丢失）。

        忠实原码：getattr 兜底默认值（code→'defaultcode'，timestamp→'1990-01-01'，
        三 adjustfactor→0，uuid→''）。
        """
        if not isinstance(model, MAdjustfactor):
            raise TypeError(f"Expected MAdjustfactor instance, got {type(model).__name__}")

        return Adjustfactor(
            code=getattr(model, 'code', 'defaultcode'),
            timestamp=getattr(model, 'timestamp', '1990-01-01'),
            fore_adjustfactor=getattr(model, 'fore_adjustfactor', 0),
            back_adjustfactor=getattr(model, 'back_adjustfactor', 0),
            adjustfactor=getattr(model, 'adjustfactor', 0),
            uuid=getattr(model, 'uuid', ''),
        )

    @staticmethod
    def from_models(models) -> List[Adjustfactor]:
        return [AdjustfactorMapper.from_model(m) for m in models]
