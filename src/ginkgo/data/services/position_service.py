# Upstream: PortfolioLive (构造函数注入的 position_writer)
# Downstream: PositionCRUD (持仓持久化)、GLOG (日志)
# Role: 持仓业务服务，提供 save_positions / get_positions 等接口


from typing import List, Optional, Any

import pandas as pd

from ginkgo.data.services.base_service import BaseService, ServiceResult
from ginkgo.libs import GLOG, to_decimal


class PositionService(BaseService):
    """
    持仓业务服务层。

    编排 PositionCRUD 的数据访问操作，提供业务语义化的接口。
    作为 PortfolioLive 的 position_writer 注入。
    """

    def __init__(self, crud_repo=None, **kwargs):
        super().__init__(crud_repo=crud_repo, **kwargs)

    def save_positions(self, positions: list) -> ServiceResult:
        """
        持久化持仓列表（逐条写入）。

        Args:
            positions: 持仓实体列表（Position 或 duck-typed 对象）

        Returns:
            ServiceResult
        """
        try:
            for pos in positions:
                self._crud_repo.add(pos)
            GLOG.DEBUG(f"Saved {len(positions)} positions")
            return ServiceResult.success(data={"count": len(positions)})
        except Exception as e:
            GLOG.ERROR(f"save_positions failed: {e}")
            return ServiceResult.error(str(e))

    def get_positions(self, portfolio_id: str) -> ServiceResult:
        """
        查询指定 portfolio 的持仓。
        """
        try:
            result = self._crud_repo.find_by_portfolio(portfolio_id)
            return ServiceResult.success(data=result)
        except Exception as e:
            GLOG.ERROR(f"get_positions failed: {e}")
            return ServiceResult.error(str(e))

    def get_all_positions(
        self,
        portfolio_id: Optional[str] = None,
        page_size: int = 50,
    ) -> ServiceResult:
        """
        查询持仓记录（支持可选 portfolio 过滤）。

        Args:
            portfolio_id: 组合 ID（可选，为空则返回全部）
            page_size: 返回数量限制，0 表示全部

        Returns:
            ServiceResult.data: ModelList
        """
        try:
            filters = {"is_del": False}
            if portfolio_id:
                filters["portfolio_id"] = portfolio_id

            results = self._crud_repo.find(
                filters=filters,
                page_size=page_size if page_size > 0 else None,
            )
            return ServiceResult.success(data=results)
        except Exception as e:
            GLOG.ERROR(f"查询持仓失败: {e}")
            return ServiceResult.error(str(e))

    def _build_position_filters(self, portfolio_id: Optional[str] = None) -> dict:
        """从业务参数构造 Position CRUD filters。get_positions_df 独立使用（DRY）。

        filter 域与现有 get_all_positions() 一致（portfolio_id），
        固定排除 is_del=True。未抽改 get_all_positions()，保持纯增量。
        """
        filters = {"is_del": False}
        if portfolio_id:
            filters["portfolio_id"] = portfolio_id
        return filters

    def get_positions_df(
        self,
        portfolio_id: Optional[str] = None,
        page_size: int = 50,
    ) -> ServiceResult:
        """出口①：data 是 pandas.DataFrame（类型即契约）。

        ADR-010：API/CLI 消费 DataFrame 语义时走此出口，不接触 ORM ModelList、
        不再绕 ``result.data.to_dataframe()``。内部 find 返 ModelList 后调
        ``to_dataframe()``；空结果返空 ``pd.DataFrame()``。
        """
        try:
            filters = self._build_position_filters(portfolio_id=portfolio_id)
            model_list = self._crud_repo.find(
                filters=filters,
                page_size=page_size if page_size > 0 else None,
            )
            df = model_list.to_dataframe() if model_list else pd.DataFrame()
            return ServiceResult.success(
                data=df,
                message=f"Retrieved {len(df)} position records (DataFrame)",
            )
        except Exception as e:
            GLOG.ERROR(f"查询持仓(df)失败: {str(e)}")
            return ServiceResult.error(f"查询持仓(df)失败: {str(e)}")

    def get_portfolio_value(self, portfolio_id: str) -> ServiceResult:
        """
        获取 portfolio 持仓总市值。
        """
        try:
            result = self._crud_repo.get_portfolio_value(portfolio_id)
            return ServiceResult.success(data=result)
        except Exception as e:
            GLOG.ERROR(f"get_portfolio_value failed: {e}")
            return ServiceResult.error(str(e))

    def upsert_position(self, position) -> ServiceResult:
        """
        创建或更新持仓（upsert 语义）。

        按 portfolio_id + code 查找已存在记录，存在则更新，不存在则创建。

        Args:
            position: Position 或 duck-typed 对象，需包含 portfolio_id, code 等属性

        Returns:
            ServiceResult
        """
        try:
            existing = self._crud_repo.get_position(
                portfolio_id=position.portfolio_id,
                code=position.code,
            )

            if existing:
                self._crud_repo.update_position(
                    portfolio_id=position.portfolio_id,
                    code=position.code,
                    cost=position.cost,
                    volume=position.volume,
                    frozen_volume=position.frozen_volume,
                    frozen_money=position.frozen_money,
                    price=position.price,
                    fee=position.fee,
                )
                GLOG.DEBUG(f"Updated position: {position.code}")
            else:
                self._crud_repo.add(position)
                GLOG.DEBUG(f"Created position: {position.code}")

            return ServiceResult.success(
                data={"updated": existing is not None, "created": existing is None},
                message="Position upserted successfully",
            )
        except Exception as e:
            GLOG.ERROR(f"upsert_position failed: {e}")
            return ServiceResult.error(str(e))
