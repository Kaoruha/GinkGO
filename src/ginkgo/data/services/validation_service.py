# Upstream: API Server (validation routes)
# Downstream: BaseService, AnalyzerRecordCRUD
# Role: 回测验证计算服务（分段稳定性、蒙特卡洛模拟）

import numpy as np
from typing import List, Optional
from ginkgo.data.services.base_service import BaseService, ServiceResult
from ginkgo.libs import GLOG


class ValidationService(BaseService):
    """回测验证服务：基于已有 analyzer_record 数据计算验证指标"""

    def __init__(self, analyzer_record_crud=None, validation_result_crud=None):
        super().__init__(crud_repo=analyzer_record_crud)
        self._analyzer_crud = analyzer_record_crud
        self._validation_result_crud = validation_result_crud

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

    def segment_stability(
        self,
        task_id: str,
        portfolio_id: str,
        n_segments_list: Optional[List[int]] = None,
    ) -> ServiceResult:
        """分段稳定性验证"""
        if n_segments_list is None:
            n_segments_list = [2, 4, 8]

        try:
            records = self._get_net_value_records(task_id, portfolio_id)
            if len(records) < 10:
                return ServiceResult.error("数据不足：net_value 记录少于 10 条")

            returns = self._records_to_returns(records)

            windows = []
            for n in n_segments_list:
                if n > len(returns):
                    continue
                segments = self._split_returns(returns, n)
                seg_metrics = [self._calc_segment_metrics(s) for s in segments]
                seg_returns = [m["total_return"] for m in seg_metrics]
                stability_score = self._calc_stability_score(seg_returns)

                windows.append({
                    "n_segments": n,
                    "segments": seg_metrics,
                    "stability_score": stability_score,
                })

            if not windows:
                return ServiceResult.error("分段数均大于数据长度，无法计算")

            return ServiceResult.success(data={"windows": windows})

        except Exception as e:
            GLOG.ERROR(f"分段稳定性计算失败: {e}")
            return ServiceResult.error(f"计算失败: {e}")

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

            return ServiceResult.success(data=stats)

        except Exception as e:
            GLOG.ERROR(f"蒙特卡洛模拟失败: {e}")
            return ServiceResult.error(f"模拟失败: {e}")
