# Upstream: BacktestProcessor, CLI (ginkgo backtest run)
# Downstream: EngineAssemblyService, data_container services/cruds
# Role: 从 TaskProcessor 提取的通用回测逻辑，供 CLI 和 Worker 复用

"""
Backtest Task Helpers

从 TaskProcessor 提取的通用回测逻辑，供 CLI 和 Worker 复用。
"""

from typing import Dict, Any

from ginkgo.data.containers import container as data_container
from ginkgo.enums import FILE_TYPES
from ginkgo.libs import GLOG


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
    risk_names = [c["name"] for c in components["risk_managers"] if c.get("name")]
    sizer_names = [c["name"] for c in components["sizers"] if c.get("name")]
    GLOG.INFO(f"[{task_uuid[:8]}] Assembly: "
              f"strategies={strategy_names}, "
              f"risk_managers={risk_names}, "
              f"sizers={sizer_names}")
    return components


def build_portfolio_config(portfolio_id: str, portfolio_data, initial_cash: float) -> Dict[str, Any]:
    """从数据库结果提取 Portfolio 配置。"""
    return {
        "uuid": portfolio_id,
        "name": portfolio_data.name if hasattr(portfolio_data, "name") else f"Portfolio_{portfolio_id[:8]}",
        "cash": float(portfolio_data.cash) if hasattr(portfolio_data, "cash") else initial_cash,
        "initial_capital": initial_cash,
    }
