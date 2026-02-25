# Upstream: ginkgo.data.cruds, ginkgo.trading.engines
# Downstream: ginkgo.client, ginkgo.trading.paper
# Role: 回测对比数据模型 - 对比结果、净值曲线等

"""
回测对比数据模型

定义回测对比相关的数据结构:
- ComparisonResult: 对比结果
- NetValueCurve: 净值曲线
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple
import uuid


@dataclass
class ComparisonResult:
    """
    回测对比结果

    存储多个回测结果的对比数据。

    Attributes:
        comparison_id: 对比 ID
        backtest_ids: 参与对比的回测 ID 列表
        metrics_table: 指标表格 {metric_name: {backtest_id: value}}
        best_performers: 每个指标的最佳表现 {metric_name: backtest_id}
        net_values: 净值曲线 {backtest_id: [(date, value), ...]}
        created_at: 创建时间
    """
    comparison_id: str = ""
    backtest_ids: List[str] = field(default_factory=list)
    metrics_table: Dict[str, Dict[str, Decimal]] = field(default_factory=dict)
    best_performers: Dict[str, str] = field(default_factory=dict)
    net_values: Dict[str, List[Tuple[str, Decimal]]] = field(default_factory=dict)
    created_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """初始化后处理"""
        if not self.comparison_id:
            self.comparison_id = f"cmp_{uuid.uuid4().hex[:8]}"
        if self.created_at is None:
            self.created_at = datetime.now()

    def get_ranking(self, metric_name: str, descending: bool = True) -> List[str]:
        """
        获取指定指标的排名

        Args:
            metric_name: 指标名称
            descending: 是否降序排列 (默认 True，高值在前)

        Returns:
            排序后的回测 ID 列表
        """
        if metric_name not in self.metrics_table:
            return []

        metric_values = self.metrics_table[metric_name]
        sorted_items = sorted(
            metric_values.items(),
            key=lambda x: x[1],
            reverse=descending
        )
        return [item[0] for item in sorted_items]

    def get_metric(self, metric_name: str, backtest_id: str) -> Optional[Decimal]:
        """
        获取指定回测的指定指标值

        Args:
            metric_name: 指标名称
            backtest_id: 回测 ID

        Returns:
            指标值，如果不存在返回 None
        """
        if metric_name not in self.metrics_table:
            return None
        return self.metrics_table[metric_name].get(backtest_id)

    def get_winner(self, metric_name: str) -> Optional[str]:
        """
        获取指定指标的最佳表现者

        Args:
            metric_name: 指标名称

        Returns:
            最佳回测 ID，如果不存在返回 None
        """
        return self.best_performers.get(metric_name)

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "comparison_id": self.comparison_id,
            "backtest_ids": self.backtest_ids,
            "metrics_table": {
                k: {kk: str(vv) for kk, vv in v.items()}
                for k, v in self.metrics_table.items()
            },
            "best_performers": self.best_performers,
            "net_values": {
                k: [(d, str(v)) for d, v in vals]
                for k, vals in self.net_values.items()
            },
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "metadata": self.metadata,
        }

    def to_dataframe(self):
        """
        转换为 pandas DataFrame

        Returns:
            pandas DataFrame，每行是一个回测，每列是一个指标
        """
        try:
            import pandas as pd
        except ImportError:
            return None

        rows = []
        for bt_id in self.backtest_ids:
            row = {"backtest_id": bt_id}
            for metric_name, values in self.metrics_table.items():
                row[metric_name] = float(values.get(bt_id, 0))
            rows.append(row)

        return pd.DataFrame(rows)

    def to_html_table(self) -> str:
        """
        生成 HTML 表格

        Returns:
            HTML 表格字符串
        """
        lines = ['<table class="comparison-table">']

        # 表头
        lines.append('<thead><tr>')
        lines.append('<th>指标</th>')
        for bt_id in self.backtest_ids:
            lines.append(f'<th>{bt_id}</th>')
        lines.append('</tr></thead>')

        # 表体
        lines.append('<tbody>')
        for metric_name, values in self.metrics_table.items():
            lines.append('<tr>')
            lines.append(f'<td>{metric_name}</td>')
            for bt_id in self.backtest_ids:
                value = values.get(bt_id, Decimal("0"))
                is_best = self.best_performers.get(metric_name) == bt_id
                cell_class = 'class="best"' if is_best else ''
                lines.append(f'<td {cell_class}>{float(value):.4f}</td>')
            lines.append('</tr>')
        lines.append('</tbody>')
        lines.append('</table>')

        return '\n'.join(lines)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ComparisonResult":
        """从字典反序列化"""
        # 转换 metrics_table 中的字符串为 Decimal
        metrics_table = {}
        for metric_name, values in data.get("metrics_table", {}).items():
            metrics_table[metric_name] = {
                k: Decimal(v) for k, v in values.items()
            }

        # 转换 net_values
        net_values = {}
        for bt_id, vals in data.get("net_values", {}).items():
            net_values[bt_id] = [(d, Decimal(v)) for d, v in vals]

        # 转换 created_at
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        return cls(
            comparison_id=data.get("comparison_id", ""),
            backtest_ids=data.get("backtest_ids", []),
            metrics_table=metrics_table,
            best_performers=data.get("best_performers", {}),
            net_values=net_values,
            created_at=created_at,
            metadata=data.get("metadata", {}),
        )


@dataclass
class NetValuePoint:
    """
    净值曲线点

    Attributes:
        date: 日期
        value: 净值
        backtest_id: 关联的回测 ID
    """
    date: str
    value: Decimal
    backtest_id: str = ""

    def to_tuple(self) -> Tuple[str, Decimal]:
        """转换为元组 (date, value)"""
        return (self.date, self.value)

    @classmethod
    def from_tuple(cls, t: Tuple[str, Any], backtest_id: str = "") -> "NetValuePoint":
        """从元组创建"""
        return cls(
            date=t[0],
            value=Decimal(str(t[1])) if not isinstance(t[1], Decimal) else t[1],
            backtest_id=backtest_id,
        )
