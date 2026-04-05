# Upstream: ResultService (回测结果), AnalyzerService (分析器记录)
# Downstream: SingleReport, ComparisonReport, SegmentReport, RollingReport
# Role: AnalysisEngine — 回测分析统一入口，编排数据加载、指标计算和报告生成


"""
AnalysisEngine — 回测分析统一入口

编排数据加载、指标计算和报告生成的全流程：
- 加载 net_value (必需) + signal/order/position (可选)
- 通过 MetricRegistry 检查可用指标并计算
- 生成 SingleReport / ComparisonReport / SegmentReport / RollingReport
"""

from typing import List, Optional

import pandas as pd

from ginkgo.libs import GLOG
from ginkgo.trading.analysis.metrics.base import DataProvider, MetricRegistry
from ginkgo.trading.analysis.metrics.portfolio import (
    AnnualizedReturn, MaxDrawdown, SharpeRatio, SortinoRatio,
    Volatility, CalmarRatio, RollingSharpe, RollingVolatility,
)
from ginkgo.trading.analysis.metrics.signal import (
    SignalCount, LongShortRatio, DailySignalFreq,
)
from ginkgo.trading.analysis.metrics.order import FillRate, AvgSlippage, CancelRate
from ginkgo.trading.analysis.metrics.position import MaxPositions, ConcentrationTopN
from ginkgo.trading.analysis.metrics.cross_source import (
    SignalOrderConversion, SignalIC,
)
from ginkgo.trading.analysis.reports.single import SingleReport
from ginkgo.trading.analysis.reports.comparison import ComparisonReport
from ginkgo.trading.analysis.reports.segment import SegmentReport
from ginkgo.trading.analysis.reports.rolling import RollingReport


class AnalysisEngine:
    """回测分析引擎

    统一入口，负责数据加载、指标注册和报告生成。

    Args:
        result_service: ResultService 实例 (signal/order/position 数据)
        analyzer_service: AnalyzerService 实例 (net_value 等分析器记录)
    """

    def __init__(self, result_service, analyzer_service):
        self._result_service = result_service
        self._analyzer_service = analyzer_service
        self._registry = MetricRegistry()
        self._register_builtin_metrics()

    # ============================================================
    # 内置指标注册
    # ============================================================

    def _register_builtin_metrics(self):
        """注册所有内置指标类"""
        builtin_metrics = [
            # Portfolio 层级 (8个)
            AnnualizedReturn, MaxDrawdown, SharpeRatio, SortinoRatio,
            Volatility, CalmarRatio, RollingSharpe, RollingVolatility,
            # Signal 层级 (3个)
            SignalCount, LongShortRatio, DailySignalFreq,
            # Order 层级 (3个)
            FillRate, AvgSlippage, CancelRate,
            # Position 层级 (2个)
            MaxPositions, ConcentrationTopN,
            # 跨数据源 (2个)
            SignalOrderConversion, SignalIC,
        ]
        for metric_cls in builtin_metrics:
            try:
                self._registry.register(metric_cls)
            except Exception as e:
                GLOG.WARNING(f"注册内置指标 {metric_cls.__name__} 失败: {e}")

    # ============================================================
    # 数据加载
    # ============================================================

    def _load_net_value(self, run_id: str, portfolio_id: str = None) -> Optional[pd.DataFrame]:
        """加载 net_value 分析器记录，转换为 DataFrame

        Args:
            run_id: 运行标识
            portfolio_id: 组合标识 (可选)

        Returns:
            包含 timestamp, value 列的 DataFrame，加载失败返回 None
        """
        result = self._analyzer_service.get_by_run_id(
            run_id=run_id,
            portfolio_id=portfolio_id,
            analyzer_name="net_value",
            limit=10000,
            as_dataframe=True,
        )
        if not result.is_success() or result.data is None:
            return None

        df = result.data
        if isinstance(df, pd.DataFrame) and len(df) > 0:
            # 确保 timestamp 和 value 列存在
            if "timestamp" not in df.columns and "value" not in df.columns:
                # 尝试从 analyzer_record 字段映射
                if "name" in df.columns and "timestamp" in df.columns:
                    pass  # 原始格式，需要转换
                else:
                    return None
            return df
        return None

    def _load_signals(self, run_id: str, portfolio_id: str = None) -> Optional[pd.DataFrame]:
        """加载 Signal 记录，转换为 DataFrame

        Args:
            run_id: 运行标识
            portfolio_id: 组合标识 (可选)

        Returns:
            Signal DataFrame，加载失败返回 None
        """
        result = self._result_service.get_signals(
            run_id=run_id,
            portfolio_id=portfolio_id,
            page=0,
            page_size=10000,
        )
        if not result.is_success() or result.data is None:
            return None

        records = result.data.get("data", [])
        if not records:
            return None

        return self._entities_to_dataframe(records)

    def _load_orders(self, run_id: str, portfolio_id: str = None) -> Optional[pd.DataFrame]:
        """加载 Order 记录，转换为 DataFrame

        Args:
            run_id: 运行标识
            portfolio_id: 组合标识 (可选)

        Returns:
            Order DataFrame，加载失败返回 None
        """
        result = self._result_service.get_orders(
            run_id=run_id,
            portfolio_id=portfolio_id,
        )
        if not result.is_success() or result.data is None:
            return None

        records = result.data.get("data", [])
        if not records:
            return None

        return self._entities_to_dataframe(records)

    def _load_positions(self, run_id: str, portfolio_id: str = None) -> Optional[pd.DataFrame]:
        """加载 Position 记录，转换为 DataFrame

        Args:
            run_id: 运行标识
            portfolio_id: 组合标识 (可选)

        Returns:
            Position DataFrame，加载失败返回 None
        """
        result = self._result_service.get_positions(
            run_id=run_id,
            portfolio_id=portfolio_id,
        )
        if not result.is_success() or result.data is None:
            return None

        records = result.data.get("data", [])
        if not records:
            return None

        return self._entities_to_dataframe(records)

    @staticmethod
    def _entities_to_dataframe(records: list) -> pd.DataFrame:
        """将实体对象列表转换为 DataFrame

        提取每个对象的 __dict__，忽略以 _ 开头的私有属性。

        Args:
            records: 实体对象列表

        Returns:
            转换后的 DataFrame
        """
        rows = []
        for obj in records:
            d = {}
            for k, v in vars(obj).items():
                if not k.startswith("_"):
                    d[k] = v
            rows.append(d)
        return pd.DataFrame(rows)

    def _load_data(self, run_id: str, portfolio_id: str = None) -> DataProvider:
        """加载所有数据源到 DataProvider

        net_value 为必需数据，缺失时抛出 ValueError。
        signal/order/position 为可选数据，加载失败时跳过并记录警告。

        Args:
            run_id: 运行标识
            portfolio_id: 组合标识 (可选)

        Returns:
            填充了数据的 DataProvider

        Raises:
            ValueError: net_value 数据不可用时抛出
        """
        dp = DataProvider()

        # 1. 加载 net_value (必需)
        nv_df = self._load_net_value(run_id, portfolio_id)
        if nv_df is None:
            raise ValueError(
                f"无法加载 net_value 数据 (run_id={run_id}, "
                f"portfolio_id={portfolio_id})"
            )
        dp.add("net_value", nv_df)

        # 2. 加载 signal (可选)
        try:
            sig_df = self._load_signals(run_id, portfolio_id)
            if sig_df is not None and len(sig_df) > 0:
                dp.add("signal", sig_df)
        except Exception as e:
            GLOG.WARNING(f"加载 signal 数据失败，跳过: {e}")

        # 3. 加载 order (可选)
        try:
            ord_df = self._load_orders(run_id, portfolio_id)
            if ord_df is not None and len(ord_df) > 0:
                dp.add("order", ord_df)
        except Exception as e:
            GLOG.WARNING(f"加载 order 数据失败，跳过: {e}")

        # 4. 加载 position (可选)
        try:
            pos_df = self._load_positions(run_id, portfolio_id)
            if pos_df is not None and len(pos_df) > 0:
                dp.add("position", pos_df)
        except Exception as e:
            GLOG.WARNING(f"加载 position 数据失败，跳过: {e}")

        return dp

    # ============================================================
    # 分析接口
    # ============================================================

    def analyze(self, run_id: str, portfolio_id: str = None) -> SingleReport:
        """生成单次回测分析报告

        Args:
            run_id: 运行标识
            portfolio_id: 组合标识 (可选)

        Returns:
            SingleReport 实例

        Raises:
            ValueError: net_value 数据不可用时抛出
        """
        dp = self._load_data(run_id, portfolio_id)
        return SingleReport(run_id=run_id, registry=self._registry, data=dp)

    def compare(self, run_ids: List[str], portfolio_id: str = None) -> ComparisonReport:
        """对比多次回测运行

        Args:
            run_ids: 运行标识列表
            portfolio_id: 组合标识 (可选)

        Returns:
            ComparisonReport 实例
        """
        reports = [self.analyze(rid, portfolio_id) for rid in run_ids]
        return ComparisonReport(reports)

    def time_segments(
        self, run_id: str, portfolio_id: str = None, freq: str = "M"
    ) -> SegmentReport:
        """按时间分段分析

        Args:
            run_id: 运行标识
            portfolio_id: 组合标识 (可选)
            freq: 分段频率 ("M"=月, "Q"=季, "Y"=年)

        Returns:
            SegmentReport 实例
        """
        dp = self._load_data(run_id, portfolio_id)
        return SegmentReport(run_id=run_id, registry=self._registry, data=dp, freq=freq)

    def rolling(
        self, run_id: str, portfolio_id: str = None, window: int = 60
    ) -> RollingReport:
        """滚动窗口分析

        Args:
            run_id: 运行标识
            portfolio_id: 组合标识 (可选)
            window: 窗口大小 (天数)

        Returns:
            RollingReport 实例
        """
        dp = self._load_data(run_id, portfolio_id)
        return RollingReport(run_id=run_id, registry=self._registry, data=dp, window=window)

    def register_metric(self, metric_cls) -> None:
        """注册自定义指标

        Args:
            metric_cls: 指标类，需满足 Metric Protocol
        """
        self._registry.register(metric_cls)
