# Upstream: BacktestTaskService (start_task/stop_task/cancel_task)
# Downstream: BacktestWorker node.py (_handle_task_assignment)
# Role: 回测派发契约 wire spec —— 判别联合 + DTO 信使（ADR-018）

"""
回测派发契约 DTO 层（ADR-018）。

判别联合（discriminated union）：StartAssignment | StopAssignment | CancelAssignment，
"哪个命令"是类型（ClassVar）非运行时字段，构造期即强制 stop 不能带 config。

唯一 owner 藏构造/校验/默认/序列化：
- 生产端 StartAssignment(...).to_payload() → producer.send(dict)
- 消费端 from_payload(raw) → match cmd（type-guard 分派）

详见 docs/adrs/ADR-018-backtest-assignment-contract.md
"""
from typing import ClassVar, Union

from pydantic import BaseModel, Field, ValidationError


class MalformedAssignmentError(ValueError):
    """from_payload 解析畸形 wire 载荷时抛出（缺 required / 未知或缺失 command / 类型错）。

    继承 ValueError：契约畸形属"输入错误"，消费端窄捕此异常标记任务失败 +
    提交 offset（at-least-once），不触发重投。
    """


class BacktestAssignmentConfig(BaseModel):
    """wire spec：start 命令的回测配置（11 字段，唯一默认表）。

    默认值原样来自消费端 node.py:346-353 的硬编码表（双源靠巧合对齐）；
    契约化后此表是唯一源，worker BacktestConfig 默认删除（迁移 ③）。
    """

    # required（min_length=1 拒空串，ADR-018 第⑤步补第③步删 worker 校验后的真空）
    start_date: str = Field(min_length=1)
    end_date: str = Field(min_length=1)

    # optional（唯一默认表 —— 改任一处须同步 service 哨兵 :712 的 100000.0）
    initial_cash: float = 100000.0
    commission_rate: float = 0.0003
    slippage_rate: float = 0.0001
    benchmark_return: float = 0.0
    max_position_ratio: float = 0.3
    stop_loss_ratio: float = 0.05
    take_profit_ratio: float = 0.15
    frequency: str = "DAY"
    analyzers: list[dict] = Field(default_factory=list)  # 透传 list[dict]，worker 侧转 AnalyzerConfig（ADR-010 信使/主体分离）


class _AssignmentBase(BaseModel):
    """三命令共享：task_uuid + command 标记 + to_payload 序列化。"""

    task_uuid: str
    command: ClassVar[str]  # 类型标记，非实例字段，不进 model_dump()

    def to_payload(self) -> dict:
        """model_dump() + 显式注入 command —— 目标 dict 非 json str（producer.send 收 dict）。"""
        payload = self.model_dump()
        payload["command"] = self.command
        return payload


class StartAssignment(_AssignmentBase):
    """启动回测命令：须带 portfolio + name + config。"""

    command: ClassVar[str] = "start"
    # required（min_length=1 拒空串，#5646 回归：与 config 字段同守 ADR-018 第⑤步真空）
    portfolio_uuid: str = Field(min_length=1)
    name: str = Field(min_length=1)
    config: BacktestAssignmentConfig


class StopAssignment(_AssignmentBase):
    """停止 running 任务（端点 docstring 有意区别于 cancel 的取消 created/pending）。

    注：消费侧 graceful-stop handler 未实现（A1），node.py 仅 WARN no-op；
    误带的 config 等多余字段由 from_payload 的 model_fields 过滤忽略——
    判别联合的守护在返回类型层面（本类无 config 字段）。
    """

    command: ClassVar[str] = "stop"


class CancelAssignment(_AssignmentBase):
    """取消 created/pending 任务。"""

    command: ClassVar[str] = "cancel"


# 判别联合类型别名（from_payload 返回类型 + 消费端 match 主体）
Assignment = Union[StartAssignment, StopAssignment, CancelAssignment]


def from_payload(raw: dict) -> Assignment:
    """按 command 分流返子类，pydantic 构造期校验 required/类型，畸形 raise MalformedAssignmentError。

    多余字段（如 stop 误带 config）按 model_fields 过滤忽略——守护在返回类型层面。
    """
    if not isinstance(raw, dict):
        raise MalformedAssignmentError(
            f"assignment payload must be dict, got {type(raw).__name__}"
        )

    command = raw.get("command")
    if command == "start":
        cls = StartAssignment
    elif command == "stop":
        cls = StopAssignment
    elif command == "cancel":
        cls = CancelAssignment
    else:
        # 缺 command 或未知 command 均畸形（今天消费 .get('command','start') 默认 start 的行为收紧）
        raise MalformedAssignmentError(f"unknown or missing command: {command!r}")

    # 只传子类已声明字段（model_fields 不含 ClassVar），多余键自动剔除
    fields = {k: v for k, v in raw.items() if k != "command" and k in cls.model_fields}
    try:
        return cls(**fields)
    except ValidationError as e:
        raise MalformedAssignmentError(str(e)) from e
