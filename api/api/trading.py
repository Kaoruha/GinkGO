"""
Paper Trading 相关 API 路由

模拟盘交易管理，包括账户创建、启停控制、持仓/订单查询、日报等。
"""

from fastapi import APIRouter, HTTPException, status, Query, Request
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum
import sys
from pathlib import Path

# 添加 Ginkgo 源码路径
ginkgo_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(ginkgo_path))

from core.logging import logger
from core.response import ok
from core.exceptions import NotFoundError, BusinessError

router = APIRouter()


# ============================================================
# Pydantic Models (匹配前端 trading.ts 类型定义)
# ============================================================

class OrderStatusFilter(str, Enum):
    pending = "pending"
    partial = "partial"
    filled = "filled"
    cancelled = "cancelled"
    rejected = "rejected"


class CreatePaperAccountRequest(BaseModel):
    """创建模拟盘账户请求（匹配前端 CreatePaperAccount）"""
    name: str = Field(..., description="账户名称")
    initial_capital: float = Field(100000.0, description="初始资金")
    slippage_model: str = Field("none", description="滑点模型: fixed/percentage/none")
    slippage_value: Optional[float] = Field(None, description="固定滑点值")
    slippage_pct: Optional[float] = Field(None, description="百分比滑点")
    commission_rate: float = Field(0.0003, description="手续费率")
    restrictions: List[str] = Field(default_factory=list, description="交易限制: t1/limit/time")
    data_source: str = Field("paper", description="数据源: replay/paper")
    replay_date: Optional[str] = Field(None, description="回放起始日期")


class StartPaperTradingRequest(BaseModel):
    """启动模拟盘请求"""
    strategy_ids: Optional[List[str]] = Field(None, description="策略ID列表")


# ============================================================
# Helper functions
# ============================================================

def _get_portfolio_service():
    """获取 PortfolioService 实例"""
    from ginkgo.data.containers import container
    return container.portfolio_service()


def _get_result_service():
    """获取 ResultService 实例"""
    from ginkgo.data.containers import container
    return container.result_service()


def _get_kafka_producer():
    """获取 Kafka Producer"""
    from ginkgo.data.drivers.ginkgo_kafka import GinkgoProducer
    return GinkgoProducer()


def _format_datetime(dt) -> Optional[str]:
    """安全格式化 datetime 对象为 ISO 字符串"""
    if dt is None:
        return None
    if isinstance(dt, datetime):
        return dt.isoformat()
    return str(dt)


def _map_order_status(status_value) -> str:
    """将 Ginkgo ORDERSTATUS_TYPES 枚举值映射为前端 OrderStatus 字符串"""
    # 前端期望: pending/partial/filled/cancelled/rejected
    from ginkgo.enums import ORDERSTATUS_TYPES
    if isinstance(status_value, int):
        mapping = {
            ORDERSTATUS_TYPES.NEW.value: "pending",
            ORDERSTATUS_TYPES.SUBMITTED.value: "pending",
            ORDERSTATUS_TYPES.PARTIAL_FILLED.value: "partial",
            ORDERSTATUS_TYPES.FILLED.value: "filled",
            ORDERSTATUS_TYPES.CANCELED.value: "cancelled",
            ORDERSTATUS_TYPES.REJECTED.value: "rejected",
        }
        return mapping.get(status_value, "pending")
    elif hasattr(status_value, 'value'):
        return _map_order_status(status_value.value)
    return "pending"


def _require_portfolio(portfolio_id: str):
    """验证 portfolio 存在，不存在则抛出 NotFoundError"""
    portfolio_service = _get_portfolio_service()
    result = portfolio_service.get(portfolio_id=portfolio_id)
    if not result.is_success() or not result.data:
        raise NotFoundError("Paper account", portfolio_id)
    return result.data


# ============================================================
# Endpoints
# ============================================================

@router.get("/accounts")
async def list_paper_accounts():
    """获取模拟盘账户列表（PAPER 模式的 Portfolio）"""
    try:
        from ginkgo.enums import PORTFOLIO_MODE_TYPES

        portfolio_service = _get_portfolio_service()
        result = portfolio_service.get(mode=PORTFOLIO_MODE_TYPES.PAPER)

        if not result.is_success():
            raise BusinessError(f"Error listing paper accounts: {result.error}")

        db_portfolios = result.data or []

        accounts = []
        for p in (db_portfolios or []):
            initial_capital = float(getattr(p, 'initial_capital', 100000) or 100000)
            cash = float(getattr(p, 'cash', initial_capital) or initial_capital)

            accounts.append({
                "uuid": p.uuid,
                "name": p.name,
                "initial_capital": initial_capital,
                "available_cash": cash,
                "position_value": 0,  # TODO: 从 position_record 计算
                "total_asset": cash,   # TODO: 现金 + 持仓市值
                "today_pnl": 0,
                "total_pnl": 0,
                "status": "stopped",  # TODO: 从 Redis/Worker 状态查询
                "created_at": _format_datetime(getattr(p, 'create_at', None)),
            })

        return ok(
            data=accounts,
            message="Paper accounts retrieved successfully"
        )

    except BusinessError:
        raise
    except Exception as e:
        logger.error(f"Error listing paper accounts: {str(e)}")
        raise BusinessError(f"Error listing paper accounts: {str(e)}")


@router.post("/accounts", status_code=status.HTTP_201_CREATED)
async def create_paper_account(data: CreatePaperAccountRequest):
    """创建模拟盘账户

    创建 PAPER 模式的 Portfolio，并通过 Kafka 通知 Worker。
    """
    try:
        from ginkgo.enums import PORTFOLIO_MODE_TYPES
        from ginkgo.interfaces.kafka_topics import KafkaTopics

        portfolio_service = _get_portfolio_service()

        result = portfolio_service.add(
            name=data.name,
            mode=PORTFOLIO_MODE_TYPES.PAPER,
            description=f"Paper trading account, initial_capital={data.initial_capital}",
        )

        if not result.is_success():
            raise BusinessError(f"Failed to create paper account: {result.error}")

        # 获取新创建的 portfolio ID
        portfolio_id = None
        result_data = result.data
        if isinstance(result_data, dict):
            portfolio_id = result_data.get('uuid')
        elif isinstance(result_data, list) and result_data:
            portfolio_id = getattr(result_data[0], 'uuid', None)
        elif hasattr(result_data, 'uuid'):
            portfolio_id = result_data.uuid

        if not portfolio_id:
            raise BusinessError("Failed to get portfolio ID after creation")

        logger.info(f"Paper account created: {portfolio_id} ({data.name})")

        return ok(
            data={"account_id": portfolio_id},
            message="Paper account created successfully"
        )

    except BusinessError:
        raise
    except Exception as e:
        logger.error(f"Error creating paper account: {str(e)}")
        raise BusinessError(f"Error creating paper account: {str(e)}")


@router.get("/accounts/{account_id}")
async def get_paper_account(account_id: str):
    """获取模拟盘账户详情（含持仓和活跃订单）"""
    try:
        db_portfolios = _require_portfolio(account_id)

        p = db_portfolios[0] if isinstance(db_portfolios, list) else db_portfolios
        initial_capital = float(getattr(p, 'initial_capital', 100000) or 100000)
        cash = float(getattr(p, 'cash', initial_capital) or initial_capital)

        # 查询当前持仓
        positions = _query_positions(account_id)

        # 查询活跃订单（pending 状态）
        orders = _query_orders(account_id, status_filter=["pending"])

        return ok(
            data={
                "uuid": p.uuid,
                "name": p.name,
                "initial_capital": initial_capital,
                "available_cash": cash,
                "position_value": 0,
                "total_asset": cash,
                "today_pnl": 0,
                "total_pnl": 0,
                "status": "stopped",
                "created_at": _format_datetime(getattr(p, 'create_at', None)),
                "positions": positions,
                "active_orders": orders,
                "today_trades": [],  # TODO: 从 order_record 查询当日成交
            },
            message="Paper account retrieved successfully"
        )

    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error getting paper account {account_id}: {str(e)}")
        raise BusinessError(f"Error getting paper account: {str(e)}")


@router.post("/{account_id}/start", deprecated=True)
async def start_paper_trading(account_id: str, data: StartPaperTradingRequest = None):
    """[DEPRECATED] Use POST /api/v1/portfolios/{uuid}/start instead"""
    try:
        from ginkgo.messages.control_command import ControlCommand
        from ginkgo.interfaces.kafka_topics import KafkaTopics

        # 验证 portfolio 存在
        _require_portfolio(account_id)

        # 发送 Kafka deploy 命令
        producer = _get_kafka_producer()
        cmd = ControlCommand.deploy(account_id)
        success = producer.send(KafkaTopics.CONTROL_COMMANDS, cmd.to_dict())

        if not success:
            raise BusinessError("Failed to send deploy command via Kafka")

        logger.info(f"Start paper trading command sent for {account_id}")

        return ok(
            data={"success": True},
            message="Paper trading start command sent"
        )

    except NotFoundError:
        raise
    except BusinessError:
        raise
    except Exception as e:
        logger.error(f"Error starting paper trading {account_id}: {str(e)}")
        raise BusinessError(f"Error starting paper trading: {str(e)}")


@router.post("/{account_id}/stop", deprecated=True)
async def stop_paper_trading(account_id: str):
    """[DEPRECATED] Use POST /api/v1/portfolios/{uuid}/stop instead"""
    try:
        from ginkgo.messages.control_command import ControlCommand
        from ginkgo.interfaces.kafka_topics import KafkaTopics

        # 验证 portfolio 存在
        _require_portfolio(account_id)

        # 发送 Kafka unload 命令
        producer = _get_kafka_producer()
        cmd = ControlCommand.unload(account_id)
        success = producer.send(KafkaTopics.CONTROL_COMMANDS, cmd.to_dict())

        if not success:
            raise BusinessError("Failed to send unload command via Kafka")

        logger.info(f"Stop paper trading command sent for {account_id}")

        return ok(
            data={"success": True},
            message="Paper trading stop command sent"
        )

    except NotFoundError:
        raise
    except BusinessError:
        raise
    except Exception as e:
        logger.error(f"Error stopping paper trading {account_id}: {str(e)}")
        raise BusinessError(f"Error stopping paper trading: {str(e)}")


@router.get("/{account_id}/positions")
async def get_paper_positions(account_id: str):
    """获取模拟盘持仓"""
    try:
        # 验证 portfolio 存在
        _require_portfolio(account_id)

        positions = _query_positions(account_id)

        return ok(
            data=positions,
            message="Paper positions retrieved successfully"
        )

    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error getting paper positions {account_id}: {str(e)}")
        raise BusinessError(f"Error getting paper positions: {str(e)}")


@router.get("/{account_id}/orders")
async def get_paper_orders(
    account_id: str,
    status: Optional[List[str]] = Query(None, description="订单状态筛选: pending/partial/filled/cancelled/rejected"),
):
    """获取模拟盘订单（可选状态筛选）"""
    try:
        # 验证 portfolio 存在
        _require_portfolio(account_id)

        orders = _query_orders(account_id, status_filter=status)

        return ok(
            data=orders,
            message="Paper orders retrieved successfully"
        )

    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error getting paper orders {account_id}: {str(e)}")
        raise BusinessError(f"Error getting paper orders: {str(e)}")


@router.delete("/{account_id}/orders/{order_id}")
async def cancel_paper_order(account_id: str, order_id: str):
    """撤销模拟盘订单

    模拟盘的订单撤销通过将订单状态更新为 CANCELED 实现。
    """
    try:
        from ginkgo.enums import ORDERSTATUS_TYPES

        result_service = _get_result_service()
        order_records = result_service.get_orders_by_portfolio(account_id)
        if not order_records.success:
            raise BusinessError(order_records.error)

        # 在结果中查找对应 order_id 的记录
        matching = [o for o in order_records.data.get("data", []) if hasattr(o, 'order_id') and o.order_id == order_id]

        if not matching:
            raise NotFoundError("Order", order_id)

        order = matching[0]

        # 只能撤销 pending 状态的订单
        order_status = order.status
        if isinstance(order_status, int):
            is_pending = order_status in (
                ORDERSTATUS_TYPES.NEW.value,
                ORDERSTATUS_TYPES.SUBMITTED.value,
            )
        elif hasattr(order_status, 'value'):
            is_pending = order_status.value in (
                ORDERSTATUS_TYPES.NEW.value,
                ORDERSTATUS_TYPES.SUBMITTED.value,
            )
        else:
            is_pending = False

        if not is_pending:
            raise BusinessError("Cannot cancel order: order is not in pending status")

        result_service.cancel_order(order_id)

        logger.info(f"Paper order canceled: {order_id} in account {account_id}")

        return ok(
            data={"success": True},
            message="Paper order canceled successfully"
        )

    except NotFoundError:
        raise
    except BusinessError:
        raise
    except Exception as e:
        logger.error(f"Error canceling paper order {order_id}: {str(e)}")
        raise BusinessError(f"Error canceling paper order: {str(e)}")


@router.get("/{account_id}/report/daily")
async def get_paper_report(
    account_id: str,
    date: Optional[str] = Query(None, description="报告日期 (YYYY-MM-DD)"),
):
    """获取模拟盘日报"""
    try:
        target_date = date or datetime.now().strftime("%Y-%m-%d")

        db_portfolios = _require_portfolio(account_id)

        p = db_portfolios[0] if isinstance(db_portfolios, list) else db_portfolios
        initial_capital = float(getattr(p, 'initial_capital', 100000) or 100000)
        cash = float(getattr(p, 'cash', initial_capital) or initial_capital)

        # 查询当日订单记录
        from ginkgo.enums import ORDERSTATUS_TYPES
        result_service = _get_result_service()
        orders_result = result_service.get_orders_by_portfolio_date(
            portfolio_id=account_id,
            start_date=target_date,
            end_date=target_date,
            page_size=1000,
        )
        orders = orders_result.data if orders_result.success else []

        trades_count = 0
        if orders:
            for o in orders:
                o_status = o.status
                if isinstance(o_status, int):
                    if o_status == ORDERSTATUS_TYPES.FILLED.value:
                        trades_count += 1
                elif hasattr(o_status, 'value'):
                    if o_status.value == ORDERSTATUS_TYPES.FILLED.value:
                        trades_count += 1

        # 查询当前持仓数量
        positions_result = result_service.get_current_positions(account_id, min_volume=1)
        positions = positions_result.data if positions_result.success else []
        positions_count = len(positions) if positions else 0

        total_return = (cash / initial_capital - 1) * 100 if initial_capital > 0 else 0

        return ok(
            data={
                "date": target_date,
                "total_return": round(total_return, 4),
                "daily_return": 0,  # TODO: 需要前一日数据对比
                "trades_count": trades_count,
                "positions_count": positions_count,
            },
            message="Daily report retrieved successfully"
        )

    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error getting paper report {account_id}: {str(e)}")
        raise BusinessError(f"Error getting paper report: {str(e)}")


# ============================================================
# Internal helper functions
# ============================================================

def _query_positions(account_id: str) -> list:
    """查询指定账户的当前持仓列表"""
    try:
        result_service = _get_result_service()
        positions_result = result_service.get_current_positions(account_id, min_volume=1)
        records = positions_result.data if positions_result.success else []

        positions = []
        for r in (records or []):
            cost = float(getattr(r, 'cost', 0) or 0)
            price = float(getattr(r, 'price', 0) or 0)
            volume = int(getattr(r, 'volume', 0) or 0)
            market_value = price * volume

            pnl = market_value - cost if cost > 0 else 0
            pnl_ratio = (pnl / cost * 100) if cost > 0 else 0

            positions.append({
                "code": getattr(r, 'code', ''),
                "name": "",  # TODO: 从 stock_info 查询股票名称
                "shares": volume,
                "cost": round(cost, 4),
                "current": round(price, 4),
                "market_value": round(market_value, 2),
                "pnl": round(pnl, 2),
                "pnl_ratio": round(pnl_ratio, 2),
                "updated_at": _format_datetime(getattr(r, 'timestamp', None)),
            })

        return positions

    except Exception as e:
        logger.error(f"Error querying positions for {account_id}: {str(e)}")
        return []


def _query_orders(account_id: str, status_filter: Optional[List[str]] = None) -> list:
    """查询指定账户的订单列表"""
    try:
        from ginkgo.enums import ORDERSTATUS_TYPES

        result_service = _get_result_service()

        # 构建状态筛选
        status_enum = None
        if status_filter:
            status_mapping = {
                "pending": [ORDERSTATUS_TYPES.NEW, ORDERSTATUS_TYPES.SUBMITTED],
                "partial": [ORDERSTATUS_TYPES.PARTIAL_FILLED],
                "filled": [ORDERSTATUS_TYPES.FILLED],
                "cancelled": [ORDERSTATUS_TYPES.CANCELED],
                "rejected": [ORDERSTATUS_TYPES.REJECTED],
            }
            first_status = status_filter[0]
            enums = status_mapping.get(first_status, [])
            if enums:
                status_enum = enums[0]

        orders_result = result_service.get_orders_by_portfolio(
            account_id, status=status_enum.value if status_enum else None, page_size=100,
        )
        records = orders_result.data.get("data", []) if orders_result.success else []

        orders = []
        for r in (records or []):
            direction = getattr(r, 'direction', 0)
            direction_value = direction.value if hasattr(direction, 'value') else int(direction)
            side = "buy" if direction_value == 1 else "sell"

            order_id = getattr(r, 'uuid', '') or getattr(r, 'order_id', '')

            orders.append({
                "order_id": order_id,
                "strategy_id": "",
                "account_id": account_id,
                "code": getattr(r, 'code', ''),
                "name": "",  # TODO: 从 stock_info 查询
                "side": side,
                "price": float(getattr(r, 'limit_price', 0) or 0),
                "volume": int(getattr(r, 'volume', 0) or 0),
                "filled": int(getattr(r, 'transaction_volume', 0) or 0),
                "avg_price": float(getattr(r, 'transaction_price', 0) or 0),
                "status": _map_order_status(getattr(r, 'status', 0)),
                "time": _format_datetime(getattr(r, 'business_timestamp', None)
                    or getattr(r, 'timestamp', None)),
                "updated_at": _format_datetime(getattr(r, 'timestamp', None)),
            })

        return orders

    except Exception as e:
        logger.error(f"Error querying orders for {account_id}: {str(e)}")
        return []
