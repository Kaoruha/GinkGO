# Upstream: ResultService (回测结果), AnalyzerService (分析器记录)
# Downstream: SingleReport, ComparisonReport, SegmentReport, RollingReport
# Role: AnalysisEngine — 回测分析统一入口，编排数据加载、指标计算和报告生成


"""
AnalysisEngine — 回测分析统一入口

编排数据加载、指标计算和报告生成的全流程：
- 加载 ALL 分析器记录 (必需) + signal/order/position (可选)
- 基于已加载的分析器名称自动注册 RollingMean/RollingStd/CV/IC 指标
- 通过 MetricRegistry 检查可用指标并计算
- 生成 SingleReport / ComparisonReport / SegmentReport / RollingReport
"""

from typing import Dict, List, Optional

import pandas as pd

from ginkgo.libs import GLOG
from ginkgo.trading.analysis.metrics.base import DataProvider, MetricRegistry
from ginkgo.trading.analysis.metrics.analyzer_metrics import (
    RollingMean, RollingStd, CV, IC,
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

    # ============================================================
    # 分析器记录加载
    # ============================================================

    def _load_analyzer_records(self, run_id: str, portfolio_id: str = None) -> Dict[str, pd.DataFrame]:
        """加载所有分析器记录，按 name 分组返回

        不使用 analyzer_name 过滤，加载该 run 下的全部分析器记录。

        Args:
            run_id: 运行标识
            portfolio_id: 组合标识 (可选)

        Returns:
            Dict[str, pd.DataFrame]，每个 DataFrame 包含 ["timestamp", "value"] 列，
            按 timestamp 排序。无数据时返回空字典。
        """
        result = self._analyzer_service.get_by_run_id(
            run_id=run_id,
            portfolio_id=portfolio_id,
            limit=100000,
        )
        if not result.is_success() or not result.data:
            return {}

        records = result.data
        grouped: Dict[str, list] = {}
        for obj in records:
            name = getattr(obj, "name", None) or obj.__dict__.get("name")
            if name is None:
                continue
            d = {k: v for k, v in vars(obj).items() if not k.startswith("_")}
            grouped.setdefault(name, []).append(d)

        dataframes: Dict[str, pd.DataFrame] = {}
        for name, rows in grouped.items():
            df = pd.DataFrame(rows)
            if "timestamp" in df.columns and "value" in df.columns:
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                df["value"] = pd.to_numeric(df["value"], errors="coerce")
                df = df.sort_values("timestamp").reset_index(drop=True)
                df = df[["timestamp", "value"]]
                dataframes[name] = df

        return dataframes

    def _auto_register_metrics(self, analyzer_names: List[str]):
        """基于已加载的分析器名称自动注册指标实例

        为每个分析器注册 RollingMean/RollingStd/CV (window=20)，
        并为非 net_value 的分析器注册 IC 指标。

        Args:
            analyzer_names: 分析器名称列表
        """
        self._registry = MetricRegistry()  # fresh registry
        window = 20
        for name in analyzer_names:
            for metric_cls in [RollingMean, RollingStd, CV]:
                try:
                    self._registry.register_instance(metric_cls(analyzer_name=name, window=window))
                except Exception as e:
                    GLOG.WARNING(f"注册 {metric_cls.__name__}({name}) 失败: {e}")
        # IC: each analyzer vs future returns (net_value changes)
        for name in analyzer_names:
            if name == "net_value":
                continue
            try:
                self._registry.register_instance(IC(analyzer_name=name, method="spearman", lag=1))
            except Exception as e:
                GLOG.WARNING(f"注册 IC({name}) 失败: {e}")

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

        分析器记录为必需数据，缺失时抛出 ValueError。
        signal/order/position 为可选数据，加载失败时跳过并记录警告。
        加载完成后自动注册与已加载分析器对应的指标实例。

        Args:
            run_id: 运行标识
            portfolio_id: 组合标识 (可选)

        Returns:
            填充了数据的 DataProvider

        Raises:
            ValueError: 分析器记录不可用时抛出
        """
        dp = DataProvider()

        # 1. 加载全部分析器记录 (必需)
        analyzer_dfs = self._load_analyzer_records(run_id, portfolio_id)
        if not analyzer_dfs:
            raise ValueError(
                f"无法加载分析器记录 (run_id={run_id}, "
                f"portfolio_id={portfolio_id})"
            )
        for name, df in analyzer_dfs.items():
            dp.add(name, df)

        # 2. 自动注册指标
        self._auto_register_metrics(list(analyzer_dfs.keys()))

        # 3. 加载 signal (可选)
        try:
            sig_df = self._load_signals(run_id, portfolio_id)
            if sig_df is not None and len(sig_df) > 0:
                dp.add("signal", sig_df)
        except Exception as e:
            GLOG.WARNING(f"加载 signal 数据失败，跳过: {e}")

        # 4. 加载 order (可选)
        try:
            ord_df = self._load_orders(run_id, portfolio_id)
            if ord_df is not None and len(ord_df) > 0:
                dp.add("order", ord_df)
        except Exception as e:
            GLOG.WARNING(f"加载 order 数据失败，跳过: {e}")

        # 5. 加载 position (可选)
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
        self, run_id: str, portfolio_id: str = None, window: int = 60, step: int = 1
    ) -> RollingReport:
        """滚动窗口分析

        Args:
            run_id: 运行标识
            portfolio_id: 组合标识 (可选)
            window: 窗口大小 (天数)
            step: 滑动步长 (默认 1)

        Returns:
            RollingReport 实例
        """
        dp = self._load_data(run_id, portfolio_id)
        return RollingReport(run_id=run_id, registry=self._registry, data=dp, window=window, step=step)
