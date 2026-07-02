# Upstream: BacktestProcessor, CLI (ginkgo backtest run)
# Downstream: EngineAssemblyService, data_container services/cruds
# Role: 从 TaskProcessor 提取的通用回测逻辑，供 CLI 和 Worker 复用

"""
Backtest Task Helpers

从 TaskProcessor 提取的通用回测逻辑，供 CLI 和 Worker 复用。
"""

from typing import Dict, Any, List, Tuple

from ginkgo.data.containers import container as data_container
from ginkgo.enums import FILE_TYPES
from ginkgo.libs import GLOG
from ginkgo.libs.data.normalize import datetime_normalize


def build_engine_data(config, task_id: str = None) -> Dict[str, Any]:
    """
    将 BacktestConfig 转换为 EngineAssemblyService 需要的 engine_data dict。

    Args:
        config: BacktestConfig 实例
        task_id: 任务标识（用于 name 和 task_id 字段，可选）
    """
    name_prefix = f"BacktestEngine_{task_id[:8]}" if task_id else f"BacktestEngine_{config.start_date}_{config.end_date}"
    result = {
        "name": name_prefix,
        "backtest_start_date": config.start_date,
        "backtest_end_date": config.end_date,
        "initial_capital": config.initial_cash,
        "commission_rate": config.commission_rate,
        "slippage_rate": config.slippage_rate,
        "broker": "backtest",
        "frequency": config.frequency,
    }
    if task_id:
        result["task_id"] = task_id
    return result


def load_portfolio_components(portfolio_id: str, task_uuid: str = "cli") -> Dict[str, Any]:
    """
    从数据库获取 Portfolio 的组件配置。

    Returns:
        components dict，结构：{"strategies": [...], "sizers": [...], ...}

    Raises:
        ValueError: Portfolio 不存在或无组件
        数据库异常直接传播（如连接失败、查询错误等）
    """
    file_mapping_crud = data_container.cruds.portfolio_file_mapping()
    mappings = file_mapping_crud.find(
        filters={"portfolio_id": portfolio_id, "is_del": False}
    )
    if not mappings:
        raise ValueError(
            f"Portfolio {portfolio_id} has no component configured. "
            f"Please bind at least one strategy before running backtest."
        )

    components = {
        "strategies": [],
        "sizers": [],
        "selectors": [],
        "risk_managers": [],
        "analyzers": [],
    }

    type_mapping = {
        FILE_TYPES.STRATEGY.value: "strategies",
        FILE_TYPES.SIZER.value: "sizers",
        FILE_TYPES.SELECTOR.value: "selectors",
        FILE_TYPES.RISKMANAGER.value: "risk_managers",
        FILE_TYPES.ANALYZER.value: "analyzers",
    }

    file_crud = data_container.cruds.file()

    for mapping in mappings:
        component_type = mapping.type
        category = type_mapping.get(component_type)
        if category and category in components:
            component_name = ""
            try:
                file_records = file_crud.find(filters={"uuid": mapping.file_id})
                if file_records and len(file_records) > 0:
                    component_name = file_records[0].name
            except Exception as e:
                GLOG.ERROR(f"[{task_uuid[:8]}] Failed to get file name: {e}")

            components[category].append({
                "file_id": mapping.file_id,
                "mapping_uuid": mapping.uuid,
                "name": component_name,
                "type": component_type,
            })

    if not components.get("strategies"):
        raise ValueError(
            f"Portfolio {portfolio_id} has no strategy configured. "
            f"Please bind at least one strategy before running backtest."
        )

    strategy_names = [c["name"] for c in components["strategies"] if c.get("name")]
    selector_names = [c["name"] for c in components["selectors"] if c.get("name")]
    risk_names = [c["name"] for c in components["risk_managers"] if c.get("name")]
    sizer_names = [c["name"] for c in components["sizers"] if c.get("name")]
    GLOG.INFO(f"[{task_uuid[:8]}] Assembly: "
              f"selectors={selector_names}, "
              f"strategies={strategy_names}, "
              f"risk_managers={risk_names}, "
              f"sizers={sizer_names}")
    return components


# ---- #6282: 回测前数据预检 -------------------------------------------------
# 回测前预查 selector codes 的 day bar 覆盖，数据缺失/稀疏时前置阻断，
# 避免跑完整个回测才给模糊警告「selector may have returned empty symbols」。

# 股票代码 token 正则：6 位数字 + 可选 .SZ/.SH/.BJ 后缀（兼容逗号/空格/分号分隔）
_CODE_TOKEN_RE = __import__("re").compile(r"\b(\d{6}(?:\.(?:SZ|SH|BJ|sz|sh|bj))?)\b")


def check_data_coverage(
    codes: List[str],
    start_date: Any,
    end_date: Any,
    bar_crud: Any,
    min_bars: int = 10,
) -> Tuple[Dict[str, int], List[str]]:
    """预查 codes 在 [start_date, end_date] 窗口的 day bar 覆盖。

    Args:
        codes: 待预查的股票代码列表
        start_date / end_date: 窗口边界（str 或 datetime，内部 normalize）
        bar_crud: day bar CRUD（须支持 count(filters)）
        min_bars: 视为「数据充足」的最小 bar 条数阈值

    Returns:
        (coverage, sparse):
          coverage = {code: bar_count}
          sparse   = bar_count < min_bars 的 code 列表（按字典序）
    """
    start_dt = datetime_normalize(start_date)
    end_dt = datetime_normalize(end_date)
    coverage: Dict[str, int] = {}
    for code in codes:
        try:
            n = bar_crud.count(
                {"code": code, "timestamp__gte": start_dt, "timestamp__lte": end_dt}
            )
        except Exception as e:
            GLOG.WARNING(f"[preflight] count bar failed for {code}: {e}")
            n = 0
        coverage[code] = n or 0
    sparse = sorted(c for c, n in coverage.items() if n < min_bars)
    return coverage, sparse


def _extract_codes_from_value(value: Any) -> List[str]:
    """从单个 param 值中提取股票代码 token（兼容 str/list/json 序列化）。"""
    import json as _json

    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        tokens = []
        for item in value:
            tokens.extend(_extract_codes_from_value(item))
        return tokens
    if not isinstance(value, str):
        value = str(value)
    # 尝试 json 反序列化（param 可能存了 '["000001.SZ","000002.SZ"]'）
    stripped = value.strip()
    if stripped.startswith("[") or stripped.startswith("{"):
        try:
            decoded = _json.loads(stripped)
            if decoded:
                return _extract_codes_from_value(decoded)
        except Exception:
            GLOG.DEBUG("json parse failed, regex fallback", exc_info=True)
    return _CODE_TOKEN_RE.findall(value)


def resolve_selector_codes(
    portfolio_id: str,
    mapping_crud: Any = None,
    param_crud: Any = None,
) -> List[str]:
    """解析 portfolio 的 FixedSelector 显式 codes（供数据预检）。

    动态 selector（cn_all/momentum/popularity）无显式 codes → 返回空列表，
    调用方应跳过预检（无法按 code 预查）。

    Args:
        portfolio_id: 组合 UUID
        mapping_crud: portfolio_file_mapping CRUD（默认 data_container）
        param_crud: param CRUD（默认 data_container）

    Returns:
        去重后的 codes 列表（仅含 SELECTOR 类型 mapping 的 param 中识别到的代码）
    """
    if mapping_crud is None:
        mapping_crud = data_container.cruds.portfolio_file_mapping()
    if param_crud is None:
        param_crud = data_container.cruds.param()

    try:
        mappings = mapping_crud.find(
            filters={"portfolio_id": portfolio_id, "is_del": False}
        )
    except Exception as e:
        GLOG.WARNING(f"[preflight] load mappings failed: {e}")
        return []

    codes: List[str] = []
    for mapping in mappings:
        if getattr(mapping, "type", None) != FILE_TYPES.SELECTOR.value:
            continue
        mapping_uuid = getattr(mapping, "uuid", None)
        if not mapping_uuid:
            continue
        try:
            params = param_crud.find_by_mapping_id(mapping_uuid)
        except Exception as e:
            GLOG.WARNING(f"[preflight] load params for {mapping_uuid} failed: {e}")
            continue
        for p in params:
            codes.extend(_extract_codes_from_value(getattr(p, "value", None)))

    # 去重保序
    seen = set()
    unique: List[str] = []
    for c in codes:
        if c not in seen:
            seen.add(c)
            unique.append(c)
    return unique


def preflight_data_coverage(
    portfolio_id: str,
    start_date: Any,
    end_date: Any,
    bar_crud: Any = None,
    mapping_crud: Any = None,
    param_crud: Any = None,
    min_bars: int = 10,
) -> Dict[str, Any]:
    """回测前数据预检：解析 selector codes → 按窗口计数 bar → 返回覆盖报告。

    Returns:
        {
            "codes": List[str],          # 预查的 codes（空=动态 selector，无法预查）
            "coverage": {code: count},
            "sparse": List[str],         # bar_count < min_bars 的 code
            "ok": bool,                  # 无稀疏（或无可预查 codes）时 True
        }
    """
    codes = resolve_selector_codes(portfolio_id, mapping_crud, param_crud)
    if not codes:
        # 动态 selector（cn_all/momentum 等）无显式 codes → 无法按 code 预查，放行
        return {"codes": [], "coverage": {}, "sparse": [], "ok": True}

    if bar_crud is None:
        bar_crud = data_container.cruds.bar()
    coverage, sparse = check_data_coverage(
        codes, start_date, end_date, bar_crud, min_bars=min_bars
    )
    return {"codes": codes, "coverage": coverage, "sparse": sparse, "ok": not sparse}


def build_preflight_warning(report: Dict[str, Any], start_date: Any, end_date: Any) -> Any:
    """将 preflight 报告转为人可读的阻断消息。

    Returns:
        str: sparse 非空时的人可读消息（含 code + 窗口 + bar 条数 + 建议）
        None: 无稀疏（或动态 selector 无可预查 codes）→ 调用方应放行
    """
    sparse = report.get("sparse") or []
    if not sparse:
        return None
    coverage = report.get("coverage", {}) or {}
    lines = [
        f":warning: Data preflight failed: {len(sparse)} symbol(s) have insufficient bars",
        f"   Window: {start_date} ~ {end_date}",
    ]
    for code in sparse:
        n = coverage.get(code, 0)
        lines.append(f"   - {code}: {n} bar(s)")
    lines.append(
        ":bulb: Tip: sync day bars first — "
        "`ginkgo data sync --code <CODE>` or widen the backtest window."
    )
    return "\n".join(lines)


def build_portfolio_config(portfolio_id: str, portfolio_data, initial_cash: float) -> Dict[str, Any]:
    """从数据库结果提取 Portfolio 配置。"""
    return {
        "uuid": portfolio_id,
        "name": portfolio_data.name if hasattr(portfolio_data, "name") else f"Portfolio_{portfolio_id[:8]}",
        "cash": float(portfolio_data.cash) if hasattr(portfolio_data, "cash") else initial_cash,
        "initial_capital": initial_cash,
    }
