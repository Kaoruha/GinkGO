# Upstream: 无 (声明式定义，单一事实源)
# Downstream: FunnelEvaluator, ParityCalculator, CLI/API/前端 (三端共用阈值)
# Role: 四级漏斗 gate 定义 — 指标/阈值/方向/严重度/修复建议


"""
四级漏斗 gate 声明式定义

G0 回测可信 → G1 回测有效 → G2 模拟一致 → G3 实盘就绪。
阈值是单一事实源：CLI/API/前端都从这里读，防止三端口径漂移。
第一版阈值内置默认值，后续可接 settings 覆盖。
"""

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class GateDefinition:
    """单条 gate 定义

    Attributes:
        id: 唯一标识 (如 g2_daily_return_corr)
        level: 所属漏斗级 (G0/G1/G2/G3)
        name: 人类可读名
        threshold: 阈值
        direction: 判定方向 — "gte" (值≥阈值过) / "lte" (值≤阈值过)
        unit: 展示单位 (空串=无量纲)
        severity: 未过时严重度 — "blocker" (卡级) / "warning" (提示)
        remediation: 未过时的建议动作 (前端行动列表直接展示)
        requires: 依赖说明 — 依赖未就绪时该 gate 报 BLOCKED 而非 FAIL
    """

    id: str
    level: str
    name: str
    threshold: float
    direction: str
    unit: str = ""
    severity: str = "blocker"
    remediation: str = ""
    requires: str = ""


# ============================================================
# 四级 gate 全集 (M1 首版：数据可算的先上，其余如实报 BLOCKED/样本不足)
# ============================================================

ALL_GATES: Tuple[GateDefinition, ...] = (
    # --- G0 回测可信 ---
    GateDefinition(
        id="g0_sample_span",
        level="G0",
        name="样本跨度 ≥ 3 年",
        threshold=3.0,
        direction="gte",
        unit="年",
        remediation="延展回测区间至 3 年以上，覆盖至少一轮牛熊",
    ),
    GateDefinition(
        id="g0_trade_count",
        level="G0",
        name="成交笔数 ≥ 100",
        threshold=100.0,
        direction="gte",
        unit="笔",
        remediation="样本交易不足，统计指标不可靠；放宽入场条件或延长时间窗",
    ),
    # G0 数据质量 (M2 preflight_checker 求值; 阈值工程化说明见设计文档 §1)
    GateDefinition(
        id="g0_bar_gap",
        level="G0",
        name="bar 缺口率 ≤ 20%",
        threshold=20.0,
        direction="lte",
        unit="%",
        remediation="缺口率超阈值，先 `ginkgo data sync` 补数再回测 (5%~20% 见 warning 明细)",
    ),
    GateDefinition(
        id="g0_adjustfactor_consistency",
        level="G0",
        name="复权因子无回跳",
        threshold=0.0,
        direction="lte",
        unit="次",
        remediation="前复权因子出现回跳，疑似混入不同口径数据，重同步该 code 的 adjustfactor",
    ),
    # G0 数据底座 (M4 preflight probe; selector 无关的全市场密度画像, 动态 selector 盲区的兜底)
    GateDefinition(
        id="g0_universe_density",
        level="G0",
        name="数据底座密度 ≥ 1000 只/日",
        threshold=1000.0,
        direction="gte",
        unit="只/日",
        severity="warning",
        remediation="窗口内日均 distinct code 不足 (bar 底座不完整), 全量补数: `ginkgo data sync` 后复查",
    ),
    # --- G1 回测有效 ---
    GateDefinition(
        id="g1_sharpe_floor",
        level="G1",
        name="Sharpe ≥ 1.0",
        threshold=1.0,
        direction="gte",
        remediation="收益质量不达及格线，不建议投入模拟盘",
    ),
    GateDefinition(
        id="g1_mdd_tolerance",
        level="G1",
        name="最大回撤 ≥ -50%",
        threshold=-0.5,
        direction="gte",
        unit="回撤",
        remediation="回撤超过承受线，加风控 (止损/仓位约束) 后重测",
    ),
    GateDefinition(
        id="g1_rolling_stability",
        level="G1",
        name="净值滚动平稳度 ≥ 0.5",
        threshold=0.5,
        direction="gte",
        remediation="滚动窗口表现发散，查看 eval rolling --stability 定位不平稳的分析器",
    ),
    GateDefinition(
        id="g1_param_neighborhood",
        level="G1",
        name="参数邻域衰减 ≤ 30%",
        threshold=0.3,
        direction="lte",
        unit="衰减",
        remediation="邻域绩效暴跌(参数尖峰,疑似过拟合), 换参数更平稳的策略结构",
        requires="optimize 接线 (四优化器未接入回测链, 邻域数据不可得)",
    ),
    # --- G2 模拟一致 (parity 5 项) ---
    GateDefinition(
        id="g2_overlap_days",
        level="G2",
        name="同窗交易日 ≥ 20",
        threshold=20.0,
        direction="gte",
        unit="天",
        remediation="继续运行模拟盘积累重叠样本",
    ),
    GateDefinition(
        id="g2_daily_return_corr",
        level="G2",
        name="日收益相关性 ≥ 0.8",
        threshold=0.8,
        direction="gte",
        remediation="相关性不足，先查执行偏差 (滑点/成交假设) 再查数据口径",
    ),
    GateDefinition(
        id="g2_cum_return_band",
        level="G2",
        name="累计收益差在带宽内 (≤1.5×同窗波动)",
        threshold=1.5,
        direction="lte",
        unit="倍带宽",
        remediation="累计收益偏离回测同窗波动 1.5 倍，检查成交价与费用假设",
    ),
    GateDefinition(
        id="g2_turnover_deviation",
        level="G2",
        name="换手偏差 ≤ 20%",
        threshold=20.0,
        direction="lte",
        unit="%",
        remediation="交易频率偏离回测，检查信号触发条件与数据到达时序",
    ),
    GateDefinition(
        id="g2_drawdown_shape",
        level="G2",
        name="回撤形态相关性 ≥ 0.6",
        threshold=0.6,
        direction="gte",
        remediation="回撤形态不同构，回撤时点错位通常指向数据延迟或成交差异",
    ),
    # --- G3 实盘就绪 ---
    GateDefinition(
        id="g3_g2_consecutive_weeks",
        level="G3",
        name="G2 连续通过 ≥ 4 周",
        threshold=4.0,
        direction="gte",
        unit="周",
        remediation="保持模拟盘运行，持续通过 G2 后再评估",
    ),
    GateDefinition(
        id="g3_kill_switch",
        level="G3",
        name="风控熔断 (kill switch) 就位",
        threshold=1.0,
        direction="gte",
        remediation="补齐实盘熔断能力 (flatten/cancel-all/日损熔断) 后重评",
        requires="livecore kill switch (P1 未落地)",
    ),
)


def gates_by_level(level: str) -> Tuple[GateDefinition, ...]:
    """取指定级的全部 gate 定义"""
    return tuple(g for g in ALL_GATES if g.level == level)


def get_gate(gate_id: str) -> GateDefinition:
    """按 id 取单条 gate 定义"""
    for g in ALL_GATES:
        if g.id == gate_id:
            return g
    raise KeyError(f"未知 gate: {gate_id}")
