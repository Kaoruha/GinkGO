# Upstream: ginkgo.data.cruds, ginkgo.trading.engines
# Downstream: ginkgo.client, ginkgo.trading.paper
# Role: 回测对比器 - 对比多个回测结果，计算指标，标注最佳表现

"""
BacktestComparator - 回测对比器

对比多个回测结果，计算关键指标，标注最佳表现。

核心功能:
- 加载多个回测结果
- 计算对比指标: total_return, sharpe_ratio, max_drawdown, win_rate 等
- 标注每个指标的最佳表现
- 支持净值曲线归一化

Usage:
    from ginkgo.trading.comparison.backtest_comparator import BacktestComparator

    comparator = BacktestComparator()
    result = comparator.compare(["bt_001", "bt_002", "bt_003"])
    print(result.best_performers)
    net_values = comparator.get_net_values(["bt_001"], normalized=True)
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple
import statistics
import uuid

from ginkgo.trading.comparison.models import ComparisonResult, NetValuePoint
from ginkgo.libs import GLOG


# 指标排序方向: True = 越大越好, False = 越小越好
METRIC_DIRECTION = {
    "total_return": True,
    "annualized_return": True,
    "sharpe_ratio": True,
    "sortino_ratio": True,
    "win_rate": True,
    "profit_factor": True,
    "max_drawdown": False,  # 越小越好
    "volatility": False,    # 越小越好
    "var": False,           # 越小越好
}


class BacktestComparator:
    """
    回测对比器

    对比多个回测结果，计算关键指标，标注最佳表现。

    Attributes:
        _results_cache: 回测结果缓存
        _mock_data: 模拟数据 (用于测试)
    """

    def __init__(self):
        """初始化回测对比器"""
        self._results_cache: Dict[str, Dict[str, Any]] = {}
        self._mock_data: Dict[str, Dict[str, Decimal]] = {}
        GLOG.INFO("BacktestComparator 初始化")

    def compare(self, backtest_ids: List[str]) -> ComparisonResult:
        """
        对比多个回测结果

        Args:
            backtest_ids: 回测 ID 列表

        Returns:
            ComparisonResult 对比结果
        """
        result = ComparisonResult(backtest_ids=backtest_ids)

        # 加载回测数据
        for bt_id in backtest_ids:
            data = self._load_backtest_result(bt_id)
            if data:
                self._results_cache[bt_id] = data

        # 如果没有真实数据，使用模拟数据
        if not self._results_cache and self._mock_data:
            for bt_id, metrics in self._mock_data.items():
                if bt_id in backtest_ids:
                    self._results_cache[bt_id] = metrics

        # 计算指标表格
        result.metrics_table = self._build_metrics_table(backtest_ids)

        # 计算最佳表现
        result.best_performers = self._calculate_best_performers(result.metrics_table)

        # 获取净值曲线
        result.net_values = self.get_net_values(backtest_ids, normalized=True)

        GLOG.INFO(f"完成回测对比: {len(backtest_ids)} 个回测")
        return result

    def compare_with_data(
        self,
        data: Dict[str, Dict[str, Decimal]],
    ) -> ComparisonResult:
        """
        使用提供的数据进行对比

        Args:
            data: 回测数据 {backtest_id: {metric_name: value}}

        Returns:
            ComparisonResult 对比结果
        """
        self._mock_data = data
        return self.compare(list(data.keys()))

    def _load_backtest_result(self, backtest_id: str) -> Optional[Dict[str, Any]]:
        """
        从数据库加载回测结果

        Args:
            backtest_id: 回测 ID

        Returns:
            回测结果字典，如果不存在返回 None
        """
        # TODO: 从数据库加载
        # from ginkgo import services
        # result_crud = services.data.cruds.backtest_result()
        # return result_crud.get_by_id(backtest_id)

        return None

    def _load_mock_data(self, data: Dict[str, Dict[str, Decimal]]) -> None:
        """
        加载模拟数据 (用于测试)

        Args:
            data: 模拟数据 {backtest_id: {metric_name: value}}
        """
        self._mock_data = data
        # 同时加载到 results_cache 以支持 get_best_performer
        for bt_id, metrics in data.items():
            self._results_cache[bt_id] = metrics

    def _build_metrics_table(
        self,
        backtest_ids: List[str],
    ) -> Dict[str, Dict[str, Decimal]]:
        """
        构建指标表格

        Args:
            backtest_ids: 回测 ID 列表

        Returns:
            指标表格 {metric_name: {backtest_id: value}}
        """
        metrics_table: Dict[str, Dict[str, Decimal]] = {}

        # 收集所有指标
        all_metrics = set()
        for bt_id in backtest_ids:
            data = self._results_cache.get(bt_id, {})
            all_metrics.update(data.keys())

        # 构建表格
        for metric in all_metrics:
            metrics_table[metric] = {}
            for bt_id in backtest_ids:
                data = self._results_cache.get(bt_id, {})
                value = data.get(metric)
                if value is not None:
                    if isinstance(value, (int, float)):
                        value = Decimal(str(value))
                    metrics_table[metric][bt_id] = value

        return metrics_table

    def _calculate_best_performers(
        self,
        metrics_table: Dict[str, Dict[str, Decimal]],
    ) -> Dict[str, str]:
        """
        计算每个指标的最佳表现

        Args:
            metrics_table: 指标表格

        Returns:
            最佳表现 {metric_name: backtest_id}
        """
        best_performers: Dict[str, str] = {}

        for metric_name, values in metrics_table.items():
            if not values:
                continue

            # 确定排序方向
            descending = METRIC_DIRECTION.get(metric_name, True)

            # 找最佳值
            sorted_items = sorted(
                values.items(),
                key=lambda x: x[1],
                reverse=descending
            )

            if sorted_items:
                best_performers[metric_name] = sorted_items[0][0]

        return best_performers

    def get_net_values(
        self,
        backtest_ids: List[str],
        normalized: bool = True,
    ) -> Dict[str, List[Tuple[str, Decimal]]]:
        """
        获取净值曲线

        Args:
            backtest_ids: 回测 ID 列表
            normalized: 是否归一化 (从 1.0 开始)

        Returns:
            净值曲线 {backtest_id: [(date, value), ...]}
        """
        net_values: Dict[str, List[Tuple[str, Decimal]]] = {}

        for bt_id in backtest_ids:
            # TODO: 从数据库加载净值曲线
            # 目前返回模拟数据
            curve = self._results_cache.get(bt_id, {}).get("net_values", [])

            if curve and normalized:
                # 归一化: 第一个点为 1.0
                if curve:
                    first_value = curve[0][1] if curve else Decimal("1")
                    if first_value != 0:
                        curve = [
                            (d, v / first_value)
                            for d, v in curve
                        ]

            net_values[bt_id] = curve

        return net_values

    def get_best_performer(self, metric_name: str) -> Optional[str]:
        """
        获取指定指标的最佳表现者

        Args:
            metric_name: 指标名称

        Returns:
            最佳回测 ID
        """
        if not self._results_cache:
            return None

        best_id = None
        best_value = None
        descending = METRIC_DIRECTION.get(metric_name, True)

        for bt_id, data in self._results_cache.items():
            value = data.get(metric_name)
            if value is None:
                continue

            if isinstance(value, (int, float)):
                value = Decimal(str(value))

            if best_value is None:
                best_value = value
                best_id = bt_id
            elif descending:
                if value > best_value:
                    best_value = value
                    best_id = bt_id
            else:
                if value < best_value:
                    best_value = value
                    best_id = bt_id

        return best_id

    def calculate_metrics(self, net_values: List[float]) -> Dict[str, Any]:
        """
        计算回测指标

        Args:
            net_values: 净值曲线列表

        Returns:
            指标字典
        """
        if not net_values or len(net_values) < 2:
            return {"total_return": Decimal("0")}

        metrics = {}

        # 总收益率
        total_return = net_values[-1] - net_values[0]
        metrics["total_return"] = Decimal(str(round(total_return, 6)))

        # 计算日收益率
        daily_returns = [
            (net_values[i] - net_values[i-1]) / net_values[i-1]
            for i in range(1, len(net_values))
        ]

        # 年化收益 (假设 252 交易日)
        if daily_returns:
            avg_daily_return = statistics.mean(daily_returns)
            metrics["annualized_return"] = Decimal(str(round(avg_daily_return * 252, 6)))

        # 最大回撤
        metrics["max_drawdown"] = Decimal(str(round(self.calculate_max_drawdown(net_values), 6)))

        return metrics

    def calculate_max_drawdown(self, net_values: List[float]) -> float:
        """
        计算最大回撤

        Args:
            net_values: 净值曲线列表

        Returns:
            最大回撤比例
        """
        if not net_values:
            return 0.0

        peak = net_values[0]
        max_dd = 0.0

        for value in net_values:
            if value > peak:
                peak = value
            dd = (peak - value) / peak if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd

        return max_dd

    def calculate_sharpe_ratio(
        self,
        daily_returns: List[float],
        risk_free_rate: float = 0.02,
    ) -> Optional[float]:
        """
        计算夏普比率

        Args:
            daily_returns: 日收益率列表
            risk_free_rate: 无风险利率 (年化)

        Returns:
            夏普比率
        """
        if not daily_returns or len(daily_returns) < 2:
            return None

        # 日无风险利率
        daily_rf = risk_free_rate / 252

        # 超额收益
        excess_returns = [r - daily_rf for r in daily_returns]

        # 均值和标准差
        mean_excess = statistics.mean(excess_returns)
        std_excess = statistics.stdev(excess_returns)

        if std_excess == 0:
            return 0.0

        # 年化夏普比率
        sharpe = (mean_excess / std_excess) * (252 ** 0.5)
        return sharpe

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "cached_results": len(self._results_cache),
            "mock_data_loaded": bool(self._mock_data),
        }
