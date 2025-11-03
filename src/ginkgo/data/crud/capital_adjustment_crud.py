from ginkgo.data.access_control import restrict_crud_access

from typing import List, Optional, Union, Any, Dict
import pandas as pd
from datetime import datetime

from ginkgo.data.crud.base_crud import BaseCRUD
from ginkgo.data.models import MCapitalAdjustment
from ginkgo.trading.entities import CapitalAdjustment
from ginkgo.enums import SOURCE_TYPES
from ginkgo.libs import datetime_normalize, GLOG, Number, to_decimal


@restrict_crud_access
class CapitalAdjustmentCRUD(BaseCRUD[MCapitalAdjustment]):
    """
    CapitalAdjustment CRUD operations.
    """

    # 类级别声明，支持自动注册

    _model_class = MCapitalAdjustment

    def __init__(self):
        super().__init__(MCapitalAdjustment)

    def _get_field_config(self) -> dict:
        """
        定义 CapitalAdjustment 数据的字段配置

        Returns:
            dict: 字段配置字典
        """
        return {
            # 投资组合ID - 非空字符串
            "portfolio_id": {"type": "string", "min": 1},
            # 时间戳 - datetime 或字符串
            "timestamp": {"type": ["datetime", "string"]},
            # 调整金额 - 可为正负数
            "amount": {"type": ["decimal", "float", "int"]},
            # 调整原因 - 字符串
            "reason": {"type": "string", "max": 200},
            # 数据源 - 枚举值
            "source": {
                "type": "enum",
                "choices": [SOURCE_TYPES.SIM, SOURCE_TYPES.LIVE, SOURCE_TYPES.BACKTEST, SOURCE_TYPES.OTHER],
            },
        }

    def _create_from_params(self, **kwargs) -> MCapitalAdjustment:
        """
        Hook method: Create MCapitalAdjustment from parameters.
        """
        return MCapitalAdjustment(
            portfolio_id=kwargs.get("portfolio_id"),
            timestamp=datetime_normalize(kwargs.get("timestamp")),
            amount=to_decimal(kwargs.get("amount", 0)),
            reason=kwargs.get("reason", ""),
            source=SOURCE_TYPES.validate_input(kwargs.get("source", SOURCE_TYPES.SIM)),
        )

    def _convert_input_item(self, item: Any) -> Optional[MCapitalAdjustment]:
        """
        Hook method: Convert capital adjustment objects to MCapitalAdjustment.
        """
        # 处理字典类型输入
        if isinstance(item, dict):
            if "portfolio_id" in item and "amount" in item:
                return MCapitalAdjustment(
                    portfolio_id=item.get("portfolio_id"),
                    timestamp=datetime_normalize(item.get("timestamp", datetime.now())),
                    amount=to_decimal(item.get("amount", 0)),
                    reason=item.get("reason", ""),
                    source=SOURCE_TYPES.validate_input(item.get("source", SOURCE_TYPES.SIM)),
                )
        # 处理对象类型输入
        elif hasattr(item, "portfolio_id") and hasattr(item, "amount"):
            return MCapitalAdjustment(
                portfolio_id=getattr(item, "portfolio_id"),
                timestamp=datetime_normalize(getattr(item, "timestamp", datetime.now())),
                amount=to_decimal(getattr(item, "amount", 0)),
                reason=getattr(item, "reason", ""),
                source=SOURCE_TYPES.validate_input(getattr(item, "source", SOURCE_TYPES.SIM)),
            )
        return None

    def _get_enum_mappings(self) -> Dict[str, Any]:
        """
        🎯 Define field-to-enum mappings for CapitalAdjustment.

        Returns:
            Dictionary mapping field names to enum classes
        """
        return {
            'source': SOURCE_TYPES  # 数据源字段映射
        }

    def _convert_models_to_business_objects(self, models: List[MCapitalAdjustment]) -> List[CapitalAdjustment]:
        """
        🎯 Convert MCapitalAdjustment models to CapitalAdjustment business objects.

        Args:
            models: List of MCapitalAdjustment models with enum fields already fixed

        Returns:
            List of CapitalAdjustment business objects
        """
        business_objects = []
        for model in models:
            try:
                # 转换source字段为枚举类型
                source_enum = SOURCE_TYPES.from_int(model.source) if isinstance(model.source, int) else model.source

                # 直接构造CapitalAdjustment业务对象
                capital_adjustment = CapitalAdjustment(
                    portfolio_id=model.portfolio_id,
                    amount=model.amount,
                    timestamp=model.timestamp,
                    reason=model.reason,
                    source=source_enum
                )
                business_objects.append(capital_adjustment)
            except Exception as e:
                GLOG.ERROR(f"Failed to convert MCapitalAdjustment to CapitalAdjustment: {e}")
                # 如果转换失败，继续处理其他对象
                continue

        return business_objects

    def _convert_output_items(self, items: List[MCapitalAdjustment], output_type: str = "model") -> List[Any]:
        """
        Hook method: Convert MCapitalAdjustment objects for business layer.
        """
        return items

    # Business Helper Methods
    def find_by_portfolio(
        self,
        portfolio_id: str,
        start_date: Optional[Any] = None,
        end_date: Optional[Any] = None,
        as_dataframe: bool = False,
    ) -> Union[List[MCapitalAdjustment], pd.DataFrame]:
        """
        Business helper: Find capital adjustments by portfolio.
        """
        filters = {"portfolio_id": portfolio_id}

        if start_date:
            filters["timestamp__gte"] = datetime_normalize(start_date)
        if end_date:
            filters["timestamp__lte"] = datetime_normalize(end_date)

        return self.find(
            filters=filters, order_by="timestamp", desc_order=True, as_dataframe=as_dataframe, output_type="model"
        )

    def get_total_adjustment(
        self, portfolio_id: str, start_date: Optional[Any] = None, end_date: Optional[Any] = None
    ) -> float:
        """
        Business helper: Get total capital adjustment amount for a portfolio.
        """
        adjustments = self.find_by_portfolio(portfolio_id, start_date, end_date, as_dataframe=False)
        return sum(float(adj.amount) for adj in adjustments if adj.amount)

    def find_by_reason(self, reason: str, as_dataframe: bool = False) -> Union[List[MCapitalAdjustment], pd.DataFrame]:
        """
        Business helper: Find capital adjustments by reason.
        """
        return self.find(
            filters={"reason__like": reason},
            order_by="timestamp",
            desc_order=True,
            as_dataframe=as_dataframe,
            output_type="model",
        )
