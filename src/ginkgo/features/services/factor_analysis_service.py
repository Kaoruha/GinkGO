#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Upstream: factor_crud (因子 PIT 读取), bar_service.get_bars_df (bars)
# Downstream: factor_cli analyze (#6794 验收3), walk_forward_factor_evaluation evaluator (#6793)
# Role: 因子效果分析编排器 — IC/IR/decay/分层/turnover 一站式 (#6794 验收1)

"""
因子效果分析编排器 (#6794 验收1)。

编排休眠 research analyzer (ICAnalyzer / FactorDecayAnalyzer / FactorLayering):
读 PIT 因子 + bars → 算前瞻收益 (PIT 截断) → 调三分析器 → 内联 turnover → 汇总报告。

PIT: 前瞻收益由 compute_forward_returns 按 realized_cutoff 截断 (验收2);
     因子读取由调用方 (analyze_factor) 经 factor_crud 按时间窗口 PIT 取数。

与 FactorService 职责分离: FactorService=因子物化, 本服务=物化后的因子效果分析。

接口差异 (编排须分别构造收益表):
  - ICAnalyzer 期望 return_Nd 多周期列 (return_col=None → 用 f"return_{period}d")
  - FactorDecayAnalyzer / FactorLayering 期望单 "return" 列 (return_col="return")
  → 编排器把 return_1d 重命名为 return 喂给 decay/layering。

turnover (#6794 验收5): LayeringStatistics.turnover 字段休眠未填充, 此处内联算
  (跨日分组成员 Jaccard 距离均值), 不 patch FactorLayering.run (降低休眠代码扰动)。
"""

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

import pandas as pd

from ginkgo.libs import GLOG
from ginkgo.data.services.base_service import ServiceResult
from ginkgo.research.forward_returns import compute_forward_returns
from ginkgo.research.ic_analysis import ICAnalyzer
from ginkgo.research.decay_analysis import FactorDecayAnalyzer
from ginkgo.research.layering import FactorLayering


def _normalize_bars_df(df: pd.DataFrame) -> pd.DataFrame:
    """归一 bars DataFrame 列名/类型 以匹配 forward_returns 期望。

    - bar 用 timestamp 列, forward_returns 用 date → 重命名
    - bar close 存 Decimal → float (避免后续 division 异常)
    """
    out = df.copy()
    if "timestamp" in out.columns and "date" not in out.columns:
        out = out.rename(columns={"timestamp": "date"})
    if "close" in out.columns:
        out["close"] = pd.to_numeric(out["close"], errors="coerce")
    return out


class FactorAnalysisService:
    """因子效果分析编排器 (#6794 验收1)。"""

    def analyze_from_dataframes(
        self,
        factor_df: pd.DataFrame,
        bars_df: pd.DataFrame,
        periods: List[int] = (1, 5, 10, 20),
        n_groups: int = 5,
        realized_cutoff: Optional[datetime] = None,
        method: str = "spearman",
        max_lag: int = 20,
    ) -> ServiceResult:
        """从已加载的 factor/bars DataFrame 跑全因子效果分析。

        Args:
            factor_df: 因子表, 需含 date/code/factor_value
            bars_df: K线表, 需含 date/code/close (编排器算前瞻收益)
            periods: 前瞻收益周期列表
            n_groups: 分层数
            realized_cutoff: PIT 截止 (前瞻收益 d+N 超此值置 NaN)
            method: IC 计算方法 (spearman/pearson)
            max_lag: decay 分析最大滞后

        Returns:
            ServiceResult.data = {ic, ir, ic_by_period, ir_by_period,
                                  decay, turnover, layering_spread, layering}
            各 analyzer 失败时 graceful skip (对应字段留空), 不阻断整体。
        """
        result = ServiceResult(data={})
        periods_list = list(periods)

        try:
            # 1. 前瞻收益 (PIT 截断, 验收2)
            return_df = compute_forward_returns(
                bars_df, periods=periods_list, realized_cutoff=realized_cutoff,
            )

            # 2. IC / IR (多周期 return_Nd 列)
            ic_by_period, ir_by_period = self._run_ic(factor_df, return_df, periods_list, method)

            # decay / layering 用单 "return" 列 (return_1d 重命名)
            return_single = return_df.rename(columns={"return_1d": "return"})

            # 3. decay
            decay_dict = self._run_decay(factor_df, return_single, max_lag)

            # 4. layering
            spread, layering_dict = self._run_layering(factor_df, return_single, n_groups)

            # 5. turnover (内联算, LayeringStatistics.turnover 休眠未填充)
            turnover = self._compute_turnover(factor_df, n_groups=n_groups)

            primary = periods_list[0] if periods_list else None
            result.success = True
            result.set_data("ic", ic_by_period.get(primary))
            result.set_data("ic_by_period", {str(k): v for k, v in ic_by_period.items()})
            result.set_data("ir", ir_by_period.get(primary))
            result.set_data("ir_by_period", {str(k): v for k, v in ir_by_period.items()})
            result.set_data("decay", decay_dict)
            result.set_data("turnover", float(turnover))
            result.set_data("layering_spread", spread)
            result.set_data("layering", layering_dict)
        except Exception as e:
            result.error = f"analyze failed: {e}"
            GLOG.ERROR(result.error)

        return result

    def _run_ic(
        self, factor_df: pd.DataFrame, return_df: pd.DataFrame,
        periods: List[int], method: str,
    ) -> Tuple[Dict[int, float], Dict[int, float]]:
        """IC / IR 分析 (多周期)。失败 graceful skip 返回空 dict。"""
        ic_by_period: Dict[int, float] = {}
        ir_by_period: Dict[int, float] = {}
        try:
            analyzer = ICAnalyzer(factor_df, return_df)
            ic_result = analyzer.analyze(periods=periods, method=method)
            for p in periods:
                stats = ic_result.statistics.get(p)
                if stats is not None:
                    ic_by_period[p] = float(stats.mean)
                    ir_by_period[p] = float(stats.icir)
        except Exception as e:
            GLOG.WARN(f"IC 分析失败 (graceful skip): {e}")
        return ic_by_period, ir_by_period

    def _run_decay(
        self, factor_df: pd.DataFrame, return_single: pd.DataFrame, max_lag: int,
    ) -> Dict[str, Any]:
        """Decay 分析 (单 return 列)。失败 graceful skip 返回空 dict。"""
        try:
            analyzer = FactorDecayAnalyzer(factor_df, return_single)
            decay_result = analyzer.analyze(max_lag=max_lag)
            return decay_result.to_dict()
        except Exception as e:
            GLOG.WARN(f"Decay 分析失败 (graceful skip): {e}")
            return {}

    def _run_layering(
        self, factor_df: pd.DataFrame, return_single: pd.DataFrame, n_groups: int,
    ) -> Tuple[Optional[float], Dict[str, Any]]:
        """分层分析 (单 return 列)。失败 graceful skip 返回 (None, {})。"""
        try:
            layering = FactorLayering(factor_df, return_single)
            layer_result = layering.run(n_groups=n_groups)
            spread = float(layer_result.spread) if layer_result.spread is not None else None
            layering_dict = (
                layer_result.statistics.to_dict() if layer_result.statistics is not None else {}
            )
            return spread, layering_dict
        except Exception as e:
            GLOG.WARN(f"Layering 分析失败 (graceful skip): {e}")
            return None, {}

    def _compute_turnover(
        self, factor_df: pd.DataFrame, n_groups: int = 5,
    ) -> float:
        """跨日分组成员变化率均值 (Jaccard 距离)。

        LayeringStatistics.turnover 字段休眠未填充 (#6794 验收5), 此处内联算:
        每日按因子值 qcut 分 n_groups, 相邻调仓日同组成员集合的对称差/并集均值。
        factor rank 日间稳定时为 0 (代码仍真实计算, 非硬编码桩)。
        """
        date_col, code_col, factor_col = "date", "code", "factor_value"
        if date_col not in factor_df.columns or factor_col not in factor_df.columns:
            return 0.0

        dates = sorted(factor_df[date_col].unique())
        if len(dates) < 2:
            return 0.0

        prev_members: Optional[Dict[Any, set]] = None
        turnovers: List[float] = []

        for date in dates:
            day = factor_df[factor_df[date_col] == date]
            if len(day) < n_groups:
                continue
            try:
                buckets = pd.qcut(
                    day[factor_col], q=n_groups, labels=False, duplicates="drop",
                )
            except (ValueError, KeyError):
                continue

            curr_members: Dict[Any, set] = {
                int(g): set(sub[code_col])
                for g, sub in day.groupby(buckets)
                if not pd.isna(g)
            }

            if prev_members and curr_members:
                diffs = []
                for g in prev_members.keys() & curr_members.keys():
                    union = prev_members[g] | curr_members[g]
                    if union:
                        diffs.append(len(prev_members[g] ^ curr_members[g]) / len(union))
                if diffs:
                    turnovers.append(sum(diffs) / len(diffs))

            prev_members = curr_members

        if not turnovers:
            return 0.0
        return float(sum(turnovers) / len(turnovers))

    def analyze_factor(
        self,
        factor_name: str,
        entity_ids: List[str],
        start_date: str,
        end_date: str,
        factor_crud: Any,
        bar_service: Any,
        entity_type: Any = None,
        periods: List[int] = (1, 5, 10, 20),
        n_groups: int = 5,
        method: str = "spearman",
        max_lag: int = 20,
    ) -> ServiceResult:
        """数据获取层: 读 PIT 因子 (factor_crud) + bars (bar_service) → analyze_from_dataframes。

        PIT: 因子按 [start, end] 窗口取 (crud timestamp__gte/lte); 前瞻收益按 end 截断。

        Args:
            factor_name: 因子名 (MFactor.factor_name)
            entity_ids: 实体代码列表
            start_date/end_date: YYYY-MM-DD (end 作 PIT realized_cutoff)
            factor_crud: FactorCRUD (get_factors_by_entity, 参数 factor_names/entity_type/start_time/end_time)
            bar_service: BarService (get_bars_df, 返回 DataFrame 列 timestamp/code/close)
            entity_type: 实体类型 (ENTITY_TYPES, CRUD 必填第一参数)
            periods/n_groups/method/max_lag: 透传 analyze_from_dataframes
        """
        result = ServiceResult(data={})
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")

            # 1. 读因子 PIT (factor_crud.get_factors_by_entity: factor_names List, entity_type 必填)
            factor_rows = []
            for eid in entity_ids:
                factors = factor_crud.get_factors_by_entity(
                    entity_type=entity_type,
                    entity_id=eid,
                    factor_names=[factor_name],
                    start_time=start_dt,
                    end_time=end_dt,
                ) or []
                for f in factors:
                    factor_rows.append({
                        "date": f.timestamp,
                        "code": f.entity_id,
                        "factor_value": float(f.factor_value),
                    })
            if not factor_rows:
                result.error = (
                    f"无因子数据: factor={factor_name}, entities={entity_ids}, "
                    f"{start_date}~{end_date}"
                )
                GLOG.WARN(result.error)
                return result
            factor_df = pd.DataFrame(factor_rows)

            # 2. 读 bars (bar_service.get_bars_df per code)
            bar_frames = []
            for eid in entity_ids:
                r = bar_service.get_bars_df(code=eid, start_date=start_date, end_date=end_date)
                if r.success and r.data is not None and not r.data.empty:
                    bar_frames.append(_normalize_bars_df(r.data))
            if not bar_frames:
                result.error = (
                    f"无 bars 数据: entities={entity_ids}, {start_date}~{end_date}"
                )
                GLOG.WARN(result.error)
                return result
            bars_df = pd.concat(bar_frames, ignore_index=True)

            # 3. 调 analyze_from_dataframes (end 作 PIT cutoff)
            return self.analyze_from_dataframes(
                factor_df, bars_df,
                periods=periods, n_groups=n_groups,
                realized_cutoff=end_dt,
                method=method, max_lag=max_lag,
            )
        except Exception as e:
            result.error = f"analyze_factor failed: {e}"
            GLOG.ERROR(result.error)
            return result
