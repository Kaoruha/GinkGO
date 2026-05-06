# DEPRECATED: 本文件中 _save_result / _result_crud 相关逻辑已废弃，未来将被移除。
# 验证结果存储方案需重新设计。计算逻辑（segment_stability / monte_carlo）可保留。
# Upstream: API Server (validation routes)
# Downstream: BaseService, AnalyzerRecordCRUD
# Role: 回测验证计算服务（分段稳定性、蒙特卡洛模拟）

import numpy as np
from typing import List, Optional
from ginkgo.data.services.base_service import BaseService, ServiceResult
from ginkgo.libs import GLOG

ANALYZER_LABELS = {
    "net_value": "净值",
    "ProfitAna": "每日盈亏",
    "annualized_return": "年化收益",
    "sharpe_ratio": "夏普比率",
    "max_drawdown": "最大回撤",
    "win_rate": "胜率",
    "hold_pct": "仓位占比",
    "order_count": "订单数",
    "signal_count": "信号数",
    "sortino_ratio": "Sortino 比率",
    "calmar_ratio": "Calmar 比率",
    "volatility": "波动率",
    "underwater_time": "水下时间",
    "var_cvar": "VaR",
    "skew_kurtosis": "偏度/峰度",
    "consecutive_pnl": "连续盈亏",
    "trade_win_rate": "交易胜率",
    "avg_win_loss_ratio": "盈亏比",
    "profit_factor": "利润因子",
    "avg_holding_period": "平均持仓天数",
    "max_consecutive_losses": "最大连续亏损",
}


class ValidationService(BaseService):
    """回测验证服务：基于已有 analyzer_record 数据计算验证指标

    DEPRECATED: _save_result / _result_crud 相关逻辑已废弃，未来将被移除。
    验证结果存储方案需重新设计。计算逻辑（segment_stability / monte_carlo）可保留。
    """

    def __init__(self, analyzer_record_crud=None, validation_result_crud=None):
        super().__init__(crud_repo=analyzer_record_crud)
        self._analyzer_crud = analyzer_record_crud
        self._result_crud = validation_result_crud

    @staticmethod
    def _get_analyzer_class(name: str):
        """通过名称查找分析器类，读取 aggregation_type 等类属性"""
        import inspect
        from ginkgo.trading.analysis.analyzers.base_analyzer import BaseAnalyzer
        for cls in BaseAnalyzer.__subclasses__():
            sig = inspect.signature(cls.__init__)
            name_param = sig.parameters.get('name')
            if name_param and name_param.default == name:
                return cls
        return None

    def get_available_metrics(self, task_id: str, portfolio_id: str) -> ServiceResult:
        """查询 analyzer_record 表中该任务实际存在的分析器名称及中文标签"""
        try:
            records = self._analyzer_crud.get_by_task_id(
                task_id=task_id,
                portfolio_id=portfolio_id,
                page_size=10000,
            )
            names = sorted(set(r.name for r in records))
            metrics = []
            for n in names:
                cls = self._get_analyzer_class(n)
                agg_type = getattr(cls, 'aggregation_type', 'mean') if cls else 'mean'
                metrics.append({"name": n, "label": ANALYZER_LABELS.get(n, n), "aggregation_type": agg_type})
            return ServiceResult.success(data={"metrics": metrics})
        except Exception as e:
            GLOG.ERROR(f"获取可用指标失败: {e}")
            return ServiceResult.error(f"获取可用指标失败: {e}")

    def _get_net_value_records(self, task_id: str, portfolio_id: str):
        """获取指定任务的 net_value 记录，按 business_timestamp 升序"""
        records = self._analyzer_crud.get_by_task_id(
            task_id=task_id,
            portfolio_id=portfolio_id,
            analyzer_name="net_value",
            page_size=10000,
        )
        # 记录默认按 timestamp 降序，反转为升序
        return list(reversed(records))

    @staticmethod
    def _records_to_returns(records) -> np.ndarray:
        """将 net_value 记录转为日收益率数组"""
        values = np.array([float(r.value) for r in records])
        return np.diff(values) / values[:-1]

    @staticmethod
    def _split_returns(returns: np.ndarray, n_segments: int) -> List[np.ndarray]:
        """将收益率数组等分为 n_segments 段"""
        length = len(returns)
        base_size = length // n_segments
        remainder = length % n_segments
        segments = []
        start = 0
        for i in range(n_segments):
            size = base_size + (1 if i < remainder else 0)
            segments.append(returns[start:start + size])
            start += size
        return segments

    @staticmethod
    def _calc_segment_metrics(daily_returns: np.ndarray) -> dict:
        """计算单段的关键指标"""
        if len(daily_returns) == 0:
            return {"total_return": 0, "sharpe": 0, "max_drawdown": 0, "win_rate": 0}

        # 累计收益
        cumulative = np.cumprod(1 + daily_returns)
        total_return = cumulative[-1] - 1

        # 夏普比率（年化）
        std = np.std(daily_returns, ddof=1)
        if std == 0:
            sharpe = 0.0
        else:
            sharpe = float(np.mean(daily_returns) / std * np.sqrt(252))

        # 最大回撤
        peak = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - peak) / peak
        max_drawdown = float(-np.min(drawdown)) if len(drawdown) > 0 else 0.0

        # 胜率
        win_rate = float(np.sum(daily_returns > 0) / len(daily_returns))

        return {
            "total_return": round(float(total_return), 6),
            "sharpe": round(sharpe, 4),
            "max_drawdown": round(max_drawdown, 6),
            "win_rate": round(win_rate, 4),
        }

    @staticmethod
    def _calc_stability_score(segment_returns: List[float]) -> float:
        """计算稳定性评分，含阈值保护"""
        mean_abs = np.mean(np.abs(segment_returns))
        if mean_abs < 0.001:
            return 0.0
        score = 1.0 - float(np.std(segment_returns) / mean_abs)
        return max(0.0, round(score, 4))

    @staticmethod
    def _get_time_range(records) -> tuple:
        """从记录获取起止时间"""
        if not records:
            return None, None
        timestamps = [r.business_timestamp or r.timestamp for r in records if (r.business_timestamp or r.timestamp)]
        if not timestamps:
            return None, None
        return min(timestamps), max(timestamps)

    DEFAULT_METRICS = ["annualized_return", "sharpe_ratio", "max_drawdown", "win_rate"]

    def segment_stability(
        self,
        task_id: str,
        portfolio_id: str,
        n_segments_list: Optional[List[int]] = None,
        metrics: Optional[List[str]] = None,
    ) -> ServiceResult:
        """分段稳定性验证 — 按指定分析器分段聚合取均值"""
        if n_segments_list is None:
            n_segments_list = [2, 4, 8]
        if metrics is None:
            metrics = list(self.DEFAULT_METRICS)

        try:
            import datetime as dt

            # 构建分析器名称→聚合类型查找表
            agg_types = {}
            for m in metrics:
                cls = self._get_analyzer_class(m)
                agg_types[m] = getattr(cls, 'aggregation_type', 'mean') if cls else 'mean'

            # 获取时间范围
            nv_records = self._get_net_value_records(task_id, portfolio_id)
            if len(nv_records) < 10:
                return ServiceResult.error("数据不足：net_value 记录少于 10 条")

            time_start, time_end = self._get_time_range(nv_records)
            if not time_start or not time_end:
                return ServiceResult.error("无法确定回测时间范围")

            # 计算稳定性评分用（基于 net_value 收益率）
            returns = self._records_to_returns(nv_records)

            windows = []
            for n in n_segments_list:
                if n > len(returns):
                    continue

                # 时间段边界
                total_seconds = (time_end - time_start).total_seconds()
                seg_duration = total_seconds / n
                boundaries = [time_start + dt.timedelta(seconds=seg_duration * i) for i in range(n + 1)]

                # 一次性查询所有分析器记录，在内存中按 name 分组
                all_records = self._analyzer_crud.get_by_task_id(
                    task_id=task_id,
                    portfolio_id=portfolio_id,
                    page_size=50000,
                )
                by_name = {}
                for r in all_records:
                    by_name.setdefault(r.name, []).append(r)
                # 确保每个分析器的记录按时间升序（delta 聚合需要首尾值）
                for name in by_name:
                    by_name[name].sort(key=lambda r: r.business_timestamp or r.timestamp)

                # 按段聚合每个指标
                segments_data = []
                for seg_idx in range(n):
                    seg_dict = {}
                    for metric_name in metrics:
                        metric_records = by_name.get(metric_name, [])
                        seg_values = [
                            float(r.value) for r in metric_records
                            if boundaries[seg_idx] <= (r.business_timestamp or r.timestamp) < boundaries[seg_idx + 1]
                        ]
                        agg_type = agg_types.get(metric_name, 'mean')
                        if agg_type == "delta" and len(seg_values) >= 2:
                            seg_dict[metric_name] = round(seg_values[-1] - seg_values[0], 6)
                        else:
                            seg_dict[metric_name] = round(float(np.mean(seg_values)), 6) if seg_values else 0.0
                    segments_data.append(seg_dict)

                # 稳定性评分（基于用户选中指标的各段值计算，取均值）
                per_metric_scores = []
                for metric_name in metrics:
                    seg_values = [s.get(metric_name, 0) for s in segments_data]
                    per_metric_scores.append(self._calc_stability_score(seg_values))
                stability_score = round(float(np.mean(per_metric_scores)), 4) if per_metric_scores else 0.0

                windows.append({
                    "n_segments": n,
                    "segments": segments_data,
                    "stability_score": stability_score,
                    "available_metrics": metrics,
                })

            if not windows:
                return ServiceResult.error("分段数均大于数据长度，无法计算")

            return ServiceResult.success(data={"windows": windows})

        except Exception as e:
            GLOG.ERROR(f"分段稳定性计算失败: {e}")
            return ServiceResult.error(f"计算失败: {e}")

    def _save_result(self, task_id: str, portfolio_id: str, method: str,
                     config: dict, result_data: dict, score: float = None) -> str:
        """持久化验证结果，返回记录 uuid"""
        import json
        from ginkgo.data.models.model_validation_result import MValidationResult, VALIDATION_STATUS

        record = MValidationResult(
            task_id=task_id,
            portfolio_id=portfolio_id,
            method=method,
            config=json.dumps(config, ensure_ascii=False),
            result=json.dumps(result_data, ensure_ascii=False),
            score=score,
            status=VALIDATION_STATUS.COMPLETED,
        )
        self._result_crud.add(record)
        return record.uuid

    @staticmethod
    def _calc_monte_carlo_stats(
        simulated_returns: np.ndarray,
        actual_return: float,
        confidence: float,
    ) -> dict:
        """从模拟收益分布计算统计指标"""
        sorted_returns = np.sort(simulated_returns)
        n = len(sorted_returns)

        # VaR: 置信水平对应的分位数
        var_idx = int(n * (1 - confidence))
        var = float(sorted_returns[var_idx])

        # CVaR: 尾部均值
        cvar = float(np.mean(sorted_returns[:var_idx + 1]))

        # 损失概率
        loss_probability = float(np.sum(simulated_returns < 0) / n)

        # 实际收益在模拟分布中的百分位
        percentile = float(np.searchsorted(sorted_returns, actual_return) / n * 100)

        return {
            "var": round(var, 6),
            "cvar": round(cvar, 6),
            "loss_probability": round(loss_probability, 4),
            "percentile": round(percentile, 2),
        }

    def monte_carlo(
        self,
        task_id: str,
        portfolio_id: str,
        n_simulations: int = 10000,
        confidence: float = 0.95,
    ) -> ServiceResult:
        """蒙特卡洛模拟验证"""
        try:
            records = self._get_net_value_records(task_id, portfolio_id)
            if len(records) < 10:
                return ServiceResult.error("数据不足：net_value 记录少于 10 条")

            returns = self._records_to_returns(records)
            actual_return = float(np.prod(1 + returns) - 1)

            # Bootstrap：有放回抽样
            n_days = len(returns)
            simulated_returns = np.empty(n_simulations)
            for i in range(n_simulations):
                sampled = np.random.choice(returns, size=n_days, replace=True)
                simulated_returns[i] = float(np.prod(1 + sampled) - 1)

            stats = self._calc_monte_carlo_stats(simulated_returns, actual_return, confidence)
            stats["actual_return"] = round(actual_return, 6)
            stats["n_simulations"] = n_simulations

            # 分布直方图数据（分桶）
            hist, bin_edges = np.histogram(simulated_returns, bins=50)
            stats["distribution"] = {
                "counts": hist.tolist(),
                "bins": [round(float(b), 6) for b in bin_edges.tolist()],
            }

            # 持久化结果
            if self._result_crud:
                self._save_result(
                    task_id=task_id,
                    portfolio_id=portfolio_id,
                    method="monte_carlo",
                    config={"version": 1, "n_simulations": n_simulations, "confidence": confidence},
                    result_data=stats,
                )

            return ServiceResult.success(data=stats)

        except Exception as e:
            GLOG.ERROR(f"蒙特卡洛模拟失败: {e}")
            return ServiceResult.error(f"模拟失败: {e}")
