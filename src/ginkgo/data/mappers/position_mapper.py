"""PositionMapper — Position Entity ↔ MPosition ORM 转换（ADR-010）。

承接原 Position.to_model / Position.from_model 内嵌逻辑
（entities/position.py:825-924）。无 PositionDTO（项目未定义），故只提供
to_model / from_model / from_models 三方法。

to_model 忠实原码：update() 3 位置参数（portfolio_id/engine_id/task_id），
settlement_queue 经 json.dumps(default=str) 序列化；update 后 model.uuid =
entity.uuid（给 ORM 赋 entity uuid，原码行为保留）。
from_model 还原 uuid（原码已如此，无 Order 式丢失 bug）；
settlement_queue 反序列化失败 fallback []（保留原码 try/except）。

铁律：不 import CRUD；不含 to_dataframe（DF 出口留 CRUD）。
"""
import datetime
import json
from typing import List

from ginkgo.data.models import MPosition
from ginkgo.entities import Position


class PositionMapper:
    """Position 双态互转。无状态，全部静态方法。"""

    # ------------------------------------------------------------------
    # Entity ↔ ORM
    # ------------------------------------------------------------------
    @staticmethod
    def to_model(entity: Position) -> MPosition:
        """Entity → ORM。3 位置参数 + model.uuid 赋值 + settlement_queue JSON 序列化。"""
        # 序列化结算队列为JSON（原码 default=str 兜底 datetime 等不可 JSON 序列化对象）
        # Position 无 settlement_queue property，直读私有属性（忠实原码）
        settlement_queue_json = json.dumps(entity._settlement_queue, default=str)

        model = MPosition()
        model.update(
            entity.portfolio_id,  # portfolio_id 位置参数 1
            entity.engine_id,     # engine_id 位置参数 2
            entity.task_id,       # task_id 位置参数 3
            code=entity.code,
            cost=entity.cost,
            volume=entity.volume,
            frozen_volume=entity.frozen_volume,
            settlement_frozen_volume=entity.settlement_frozen_volume,
            settlement_days=entity.settlement_days,
            settlement_queue_json=settlement_queue_json,
            frozen_money=entity.frozen_money,
            price=entity.price,
            fee=entity.fee,
        )
        # 设置UUID（原码行为：给 ORM 赋 entity 的 uuid）
        model.uuid = entity.uuid
        return model

    @staticmethod
    def from_model(model: MPosition) -> Position:
        """ORM → Entity。还原 uuid（原码已如此，无丢失 bug）。

        settlement_queue 反序列化失败时 fallback []（保留原码 try/except）。
        timestamp 硬编码 '2023-01-01 10:00:00' 为原码行为（Position 时间键
        不来自 MPosition，忠实搬运）。
        """
        if not isinstance(model, MPosition):
            raise TypeError(f"Expected MPosition instance, got {type(model).__name__}")

        # 创建Position实例，只传递非None值以使用构造函数默认值
        position_kwargs = {
            'portfolio_id': model.portfolio_id,
            'engine_id': model.engine_id,
            'task_id': model.task_id,
            'code': model.code,
            'cost': model.cost,
            'volume': model.volume,
            'price': model.price,
            'uuid': model.uuid,
            'timestamp': '2023-01-01 10:00:00'
        }

        # 只添加非None的可选字段
        if model.frozen_volume is not None:
            position_kwargs['frozen_volume'] = model.frozen_volume
        if model.settlement_frozen_volume is not None:
            position_kwargs['settlement_frozen_volume'] = model.settlement_frozen_volume
        if model.settlement_days is not None:
            position_kwargs['settlement_days'] = model.settlement_days
        if model.frozen_money is not None:
            position_kwargs['frozen_money'] = model.frozen_money
        if model.fee is not None:
            position_kwargs['fee'] = model.fee

        position = Position(**position_kwargs)

        # 反序列化结算队列JSON（失败 fallback []）
        # Position 无 settlement_queue property，直写私有属性（忠实原码）
        try:
            settlement_queue_data = json.loads(model.settlement_queue_json or "[]")
            position._settlement_queue = []

            for batch_data in settlement_queue_data:
                # 转换日期字符串回datetime对象
                batch = {
                    'volume': batch_data['volume'],
                    'buy_date': datetime.datetime.fromisoformat(batch_data['buy_date']),
                    'settlement_date': datetime.datetime.fromisoformat(batch_data['settlement_date'])
                }
                position._settlement_queue.append(batch)
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            position.log("ERROR", f"Failed to deserialize settlement_queue: {e}")
            position._settlement_queue = []

        return position

    @staticmethod
    def from_models(models) -> List[Position]:
        return [PositionMapper.from_model(m) for m in models]
