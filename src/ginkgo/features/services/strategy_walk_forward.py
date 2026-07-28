#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Upstream: backtest_func (调用方注入, 跑策略回测返回表现)
# Downstream: factor_cli / walk-forward CLI (#6796 验收2/4), 策略评估上层
# Role: 策略走步 OOS 验证 -- 切折 + train/test + 如实报告 (#6796)

"""策略走步 OOS 验证 (#6796 验收2 + 验收4)。

与 #6793 walk_forward_factor_evaluation 的区别:
  - 因子层走步: evaluator 拿 MFactor 行打 IC 分 (因子是否稳定)
  - 策略层走步 (本函数): backtest_func 跑策略回测拿净值/收益 (策略 OOS 是否赚钱)

backtest_func 契约: (params, start, end) -> {"return": float, ...}
  调用方负责把 FactorTopDecileStrategy 等包成此 callable (绑 factor_reader + 跑引擎);
  本函数只负责切折 + 调用 + 汇总, 不耦合引擎/数据层 (便于单测 mock)。

如实报告 (验收4): OOS mean_test_return <= 0 → effective=False (不强行声称有效)。
"""

from typing import Callable, Optional, Any
from datetime import datetime, timedelta

from ginkgo.libs import GLOG
from ginkgo.data.services.base_service import ServiceResult


def walk_forward_strategy_evaluation(
    backtest_func: Callable[..., Any],
    start_date: str,
    end_date: str,
    n_folds: int = 5,
    train_ratio: float = 0.7,
) -> ServiceResult:
    """策略走步 OOS 验证 (expanding window)。

    Args:
        backtest_func: (params, start, end) -> {"return": float}; params 透传 (None 占位)
        start_date/end_date: YYYY-MM-DD 总区间
        n_folds: 折数
        train_ratio: 接口对齐 #6793 (expanding 模式下 train 恒为历史全部, 此值保留)

    Returns:
        ServiceResult.data = {folds, mean_train_return, mean_test_return,
                              degradation, effective, n_folds}
        effective = mean_test_return > 0 (OOS 正才有效; 如实反映)
    """
    result = ServiceResult(data={})
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        total_days = (end - start).days
        if total_days <= 0 or n_folds < 1:
            result.error = f"非法区间或折数: {start_date}~{end_date}, n_folds={n_folds}"
            GLOG.WARN(result.error)
            return result

        fold_size = total_days / (n_folds + 1)  # expanding: 每段等长, train 累积
        folds = []
        for i in range(n_folds):
            train_end = start + timedelta(days=fold_size * (i + 1))
            test_end = start + timedelta(days=fold_size * (i + 2))
            if test_end > end:
                test_end = end

            train_r = backtest_func(None, start, train_end) or {}
            test_r = backtest_func(None, train_end, test_end) or {}
            folds.append({
                "fold": i,
                "train_start": str(start.date()),
                "train_end": str(train_end.date()),
                "test_start": str(train_end.date()),
                "test_end": str(test_end.date()),
                "train_return": train_r.get("return"),
                "test_return": test_r.get("return"),
            })

        def _mean_of(key: str) -> Optional[float]:
            vals = [f[key] for f in folds if f[key] is not None]
            return sum(vals) / len(vals) if vals else None

        mean_train = _mean_of("train_return")
        mean_test = _mean_of("test_return")
        degradation = (
            mean_train - mean_test
            if mean_train is not None and mean_test is not None else None
        )
        # 验收4: 如实报告 — OOS mean <= 0 即无效 (不强行声称有效)
        effective = mean_test is not None and mean_test > 0

        result.success = True
        result.set_data("folds", folds)
        result.set_data("mean_train_return", mean_train)
        result.set_data("mean_test_return", mean_test)
        result.set_data("degradation", degradation)
        result.set_data("effective", effective)
        result.set_data("n_folds", n_folds)
    except Exception as e:
        result.error = f"walk_forward_strategy_evaluation failed: {e}"
        GLOG.ERROR(result.error)
    return result
