#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Upstream: BaseStrategy.bind_factor_reader / 回测引擎装配
# Downstream: FactorCRUD.get_latest_factors_by_entity (data 层, PIT 能力)
# Role: PITFactorReader — 因子读取入口, 强制 point-in-time 防前瞻泄漏 (#6793)

"""
PITFactorReader — 因子 point-in-time 读取器 (#6793).

策略通过 BaseStrategy.get_factor_value(code, factor_name, at_time) 读因子,
底层委托此 reader。reader 是 PIT 硬约束层:

1. at_time 必传 (None 直接 raise, 不可绕过) — 回测事件时间
2. at_time 下推到 crud (SQL 层 timestamp__lte, 只取 <= at_time 的因子)
3. 防御性双保险: 即使底层漏过滤返回了未来值 (ts > at_time), reader 仍拦截返回 None

分层: crud 提供 PIT *能力* (at_time 可选, 向后兼容运维全量查询);
      reader 强制 PIT *约束* (at_time 必传, 回测专用入口)。
"""

from typing import Optional
from datetime import datetime

from ginkgo.enums import ENTITY_TYPES


class PITFactorReader:
    """因子 PIT 读取器。

    Args:
        factor_crud: FactorCRUD 实例 (data 层, 提供 get_latest_factors_by_entity)
        entity_type: 实体类型 (默认 STOCK; 个股因子)
    """

    def __init__(self, factor_crud, entity_type: ENTITY_TYPES = ENTITY_TYPES.STOCK):
        self.factor_crud = factor_crud
        self.entity_type = entity_type

    def get_factor_value(
        self,
        code: str,
        factor_name: str,
        at_time: Optional[datetime] = None,
    ) -> Optional[float]:
        """读取 code 在 at_time 时刻的因子值 (PIT: 只用 <= at_time 的数据)。

        Args:
            code: 实体标识 (如 "000001.SZ")
            factor_name: 因子名称 (如 "ROC")
            at_time: 回测事件时间 (必传, PIT 硬约束)

        Returns:
            因子值 (float); at_time 前无此因子或被防御层拦截时返回 None

        Raises:
            ValueError: at_time=None (PIT 不可绕过)
        """
        if at_time is None:
            raise ValueError(
                "PITFactorReader requires at_time (point-in-time guard, #6793); "
                "pass the event/backtest timestamp to prevent lookahead bias."
            )

        factors = self.factor_crud.get_latest_factors_by_entity(
            entity_type=self.entity_type,
            entity_id=code,
            factor_names=[factor_name],
            at_time=at_time,
        )

        if not factors:
            return None

        # 取 timestamp 最大者 (= at_time 前的最新), 再做防御性 PIT 校验 (双保险)
        latest = max(factors, key=lambda x: x.timestamp)
        if latest.timestamp > at_time:
            # 底层漏过滤返回了未来值 — 拦截, 不让前瞻泄漏进回测
            return None

        return float(latest.factor_value)
