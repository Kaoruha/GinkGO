# Upstream: PortfolioService (投资组合业务服务)、Engine (创建和查询portfolio)
# Downstream: BaseCRUD (继承提供标准CRUD能力和装饰器@time_logger/@retry/@cache)、MPortfolio (MySQL投资组合模型)、PortfolioBase (业务投资组合实体)
# Role: PortfolioCRUD组合CRUD操作继承BaseCRUD提供组合管理和资金操作方法






from typing import List, Optional, Union, Any, Dict
import pandas as pd
from datetime import datetime

from ginkgo.data.crud.base_crud import BaseCRUD
from ginkgo.data.models import MPortfolio
from ginkgo.enums import SOURCE_TYPES, PORTFOLIO_MODE_TYPES, PORTFOLIO_RUNSTATE_TYPES
from ginkgo.libs import datetime_normalize, GLOG
from ginkgo.data.access_control import restrict_crud_access


@restrict_crud_access
class PortfolioCRUD(BaseCRUD[MPortfolio]):
    """
    Portfolio CRUD operations - Only overrides hook methods, never template methods.

    Features:
    - Inherits ALL decorators (@time_logger, @retry, @cache) from BaseCRUD template methods
    - Only provides Portfolio-specific conversion and creation logic via hook methods
    - Supports portfolio management and tracking
    - Maintains architectural purity of template method pattern
    """

    _model_class = MPortfolio

    def __init__(self):
        super().__init__(MPortfolio)

    def _get_field_config(self) -> dict:
        """
        定义 Portfolio 数据的字段配置

        Returns:
            dict: 字段配置字典
        """
        return {
            # 投资组合名称 - 非空字符串
            'name': {
                'type': 'string',
                'min': 1,
                'max': 64
            },

            # 投资组合描述 - 可选字符串
            'desc': {
                'type': 'string',
                'min': 0,
                'max': 255
            },

            # 运行模式 - 枚举值
            'mode': {
                'type': 'enum',
                'enum_class': PORTFOLIO_MODE_TYPES,
                'default': PORTFOLIO_MODE_TYPES.BACKTEST.value
            },

            # 运行状态 - 枚举值
            'state': {
                'type': 'enum',
                'enum_class': PORTFOLIO_RUNSTATE_TYPES,
                'default': PORTFOLIO_RUNSTATE_TYPES.INITIALIZED.value
            },
        }

    def _create_from_params(self, **kwargs) -> MPortfolio:
        """Hook method: Create MPortfolio from parameters."""
        return MPortfolio(
            name=kwargs.get("name", "test_portfolio"),
            desc=kwargs.get("desc"),
            mode=PORTFOLIO_MODE_TYPES.validate_input(kwargs.get("mode", PORTFOLIO_MODE_TYPES.BACKTEST)) or PORTFOLIO_MODE_TYPES.BACKTEST.value,
            state=PORTFOLIO_RUNSTATE_TYPES.validate_input(kwargs.get("state", PORTFOLIO_RUNSTATE_TYPES.INITIALIZED)) or PORTFOLIO_RUNSTATE_TYPES.INITIALIZED.value,
            source=SOURCE_TYPES.validate_input(kwargs.get("source", SOURCE_TYPES.SIM)),
            initial_capital=kwargs.get("initial_capital", 100000.0),
            current_capital=kwargs.get("current_capital", 100000.0),
            cash=kwargs.get("cash", 100000.0),
            frozen=kwargs.get("frozen", 0.0),
            total_fee=kwargs.get("total_fee", 0.0),
            total_profit=kwargs.get("total_profit", 0.0),
            risk_level=kwargs.get("risk_level", 0.1),
            max_drawdown=kwargs.get("max_drawdown", 0.0),
            sharpe_ratio=kwargs.get("sharpe_ratio", 0.0),
            win_rate=kwargs.get("win_rate", 0.0),
            total_trades=kwargs.get("total_trades", 0),
            winning_trades=kwargs.get("winning_trades", 0)
        )

    def _convert_input_item(self, item: Any) -> Optional[MPortfolio]:
        """Hook method: Convert portfolio objects to MPortfolio."""
        if hasattr(item, 'name'):
            return MPortfolio(
                name=getattr(item, 'name', 'test_portfolio'),
                desc=getattr(item, 'desc', None),
                mode=PORTFOLIO_MODE_TYPES.validate_input(getattr(item, 'mode', PORTFOLIO_MODE_TYPES.BACKTEST)) or PORTFOLIO_MODE_TYPES.BACKTEST.value,
                state=PORTFOLIO_RUNSTATE_TYPES.validate_input(getattr(item, 'state', PORTFOLIO_RUNSTATE_TYPES.INITIALIZED)) or PORTFOLIO_RUNSTATE_TYPES.INITIALIZED.value,
                source=SOURCE_TYPES.validate_input(getattr(item, 'source', SOURCE_TYPES.SIM)),
                initial_capital=getattr(item, 'initial_capital', 100000.0),
                current_capital=getattr(item, 'current_capital', 100000.0),
                cash=getattr(item, 'cash', 100000.0),
                frozen=getattr(item, 'frozen', 0.0),
                total_fee=getattr(item, 'total_fee', 0.0),
                total_profit=getattr(item, 'total_profit', 0.0),
                risk_level=getattr(item, 'risk_level', 0.1),
                max_drawdown=getattr(item, 'max_drawdown', 0.0),
                sharpe_ratio=getattr(item, 'sharpe_ratio', 0.0),
                win_rate=getattr(item, 'win_rate', 0.0),
                total_trades=getattr(item, 'total_trades', 0),
                winning_trades=getattr(item, 'winning_trades', 0)
            )
        return None

    def _get_enum_mappings(self) -> Dict[str, Any]:
        """
        🎯 Define field-to-enum mappings for Portfolio.

        Returns:
            Dictionary mapping field names to enum classes
        """
        return {
            'source': SOURCE_TYPES,
            'mode': PORTFOLIO_MODE_TYPES,
            'state': PORTFOLIO_RUNSTATE_TYPES
        }

    def _convert_models_to_business_objects(self, models: List[MPortfolio]) -> List[Any]:
        """
        🎯 Convert MPortfolio models to business objects.

        Args:
            models: List of MPortfolio models with enum fields already fixed

        Returns:
            List of PortfolioBase business objects
        """
        from ginkgo.trading.bases.portfolio_base import PortfolioBase

        business_objects = []
        for model in models:
            try:
                # Create PortfolioBase from MPortfolio model
                portfolio = PortfolioBase(
                    name=model.name,
                    timestamp=model.create_at
                )
                # Set the portfolio properties from the model
                portfolio._uuid = model.uuid
                portfolio._name = model.name
                portfolio._mode = PORTFOLIO_MODE_TYPES.from_int(model.mode) or PORTFOLIO_MODE_TYPES.BACKTEST
                portfolio._state = PORTFOLIO_RUNSTATE_TYPES.from_int(model.state) or PORTFOLIO_RUNSTATE_TYPES.INITIALIZED
                portfolio._create_at = model.create_at
                portfolio._update_at = model.update_at

                business_objects.append(portfolio)
            except Exception as e:
                GLOG.ERROR(f"Failed to convert MPortfolio to PortfolioBase: {e}")
                # Fallback: return original model
                business_objects.append(model)

        return business_objects

    def _convert_output_items(self, items: List[MPortfolio], output_type: str = "model") -> List[Any]:
        """Hook method: Convert MPortfolio objects for business layer."""
        return items

    # Business Helper Methods
    def find_by_uuid(self, uuid: str) -> List[MPortfolio]:
        """Find portfolio by UUID."""
        return self.find(filters={"uuid": uuid}, page_size=1)

    def find_by_name_pattern(self, name_pattern: str) -> List[MPortfolio]:
        """Find portfolios by name pattern."""
        return self.find(filters={"name__like": name_pattern}, order_by="update_at", desc_order=True)

    def find_by_mode(self, mode: PORTFOLIO_MODE_TYPES) -> List[MPortfolio]:
        """Find portfolios by mode (BACKTEST/PAPER/LIVE)."""
        mode_value = PORTFOLIO_MODE_TYPES.validate_input(mode)
        return self.find(filters={"mode": mode_value}, order_by="update_at", desc_order=True)

    def find_by_state(self, state: PORTFOLIO_RUNSTATE_TYPES) -> List[MPortfolio]:
        """Find portfolios by state (INITIALIZED/RUNNING/PAUSED/...)."""
        state_value = PORTFOLIO_RUNSTATE_TYPES.validate_input(state)
        return self.find(filters={"state": state_value}, order_by="update_at", desc_order=True)

    def find_paper_portfolios(self) -> List[MPortfolio]:
        """Find all PAPER mode portfolios."""
        return self.find_by_mode(PORTFOLIO_MODE_TYPES.PAPER)

    def find_live_portfolios(self) -> List[MPortfolio]:
        """Find all LIVE mode portfolios."""
        return self.find_by_mode(PORTFOLIO_MODE_TYPES.LIVE)

    def find_running_portfolios(self) -> List[MPortfolio]:
        """Find all RUNNING state portfolios."""
        return self.find_by_state(PORTFOLIO_RUNSTATE_TYPES.RUNNING)

    def get_all_uuids(self) -> List[str]:
        """
        Business helper: Get all distinct portfolio UUIDs.
        Uses base CRUD's DISTINCT support for consistent null byte handling.
        """
        try:
            portfolio_uuids = self.find(distinct_field="uuid")
            return [puid for puid in portfolio_uuids if puid]
        except Exception as e:
            GLOG.ERROR(f"Failed to get portfolio uuids: {e}")
            return []

    def delete_by_uuid(self, uuid: str) -> None:
        """Delete portfolio by UUID."""
        if not uuid:
            raise ValueError("uuid不能为空")

        GLOG.WARN(f"删除组合 {uuid}")
        return self.remove({"uuid": uuid})

    def update_mode(self, uuid: str, mode: PORTFOLIO_MODE_TYPES) -> None:
        """Update portfolio mode.

        .. deprecated::
            mode 只能通过 DeploymentService.deploy() 或 PortfolioService.add() 设置。
            直接修改 mode 已废弃。
        """
        raise DeprecationWarning(
            "update_mode is deprecated. "
            "Use DeploymentService.deploy() to create deployed portfolios, "
            "or PortfolioService.add() for new portfolios."
        )

    def update_state(self, uuid: str, state: PORTFOLIO_RUNSTATE_TYPES) -> None:
        """Update portfolio state."""
        state_value = PORTFOLIO_RUNSTATE_TYPES.validate_input(state)
        return self.modify({"uuid": uuid}, {"state": state_value})

    # 别名方法，保持与测试期望的一致性
    def delete(self, uuid: str) -> None:
        """删除投资组合的别名方法，映射到delete_by_uuid"""
        return self.delete_by_uuid(uuid)

    def update(self, uuid: str, **kwargs) -> None:
        """更新投资组合的通用方法"""
        if not uuid:
            raise ValueError("uuid不能为空")

        if not kwargs:
            raise ValueError("至少需要提供一个更新字段")

        # 处理枚举字段
        if 'mode' in kwargs:
            kwargs['mode'] = PORTFOLIO_MODE_TYPES.validate_input(kwargs['mode'])
        if 'state' in kwargs:
            kwargs['state'] = PORTFOLIO_RUNSTATE_TYPES.validate_input(kwargs['state'])

        return self.modify({"uuid": uuid}, kwargs)

    # ==================== 废弃方法（向后兼容） ====================

    def find_by_live_status(self, is_live: bool) -> List[MPortfolio]:
        """
        [已废弃] 按实盘状态查询投资组合

        .. deprecated::
            此方法已废弃，请使用 find_by_mode() 替代。

            迁移示例:
                旧: find_by_live_status(is_live=True)
                新: find_by_mode(PORTFOLIO_MODE_TYPES.LIVE)

        Args:
            is_live: True=实盘, False=回测

        Returns:
            符合条件的投资组合列表
        """
        GLOG.WARN("find_by_live_status is deprecated, use find_by_mode instead")
        mode = PORTFOLIO_MODE_TYPES.LIVE if is_live else PORTFOLIO_MODE_TYPES.BACKTEST
        return self.find_by_mode(mode)

    def update_live_status(self, uuid: str, is_live: bool) -> None:
        """
        [已废弃] 更新投资组合实盘状态

        .. deprecated::
            此方法已废弃，请使用 update_mode() 替代。

            迁移示例:
                旧: update_live_status(uuid, is_live=True)
                新: update_mode(uuid, PORTFOLIO_MODE_TYPES.LIVE)

        Args:
            uuid: 投资组合UUID
            is_live: True=实盘, False=回测
        """
        GLOG.WARN("update_live_status is deprecated, use update_mode instead")
        mode = PORTFOLIO_MODE_TYPES.LIVE if is_live else PORTFOLIO_MODE_TYPES.BACKTEST
        return self.update_mode(uuid, mode)

