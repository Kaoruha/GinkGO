"""
Paper Trading 相关 API 路由

模拟盘交易管理，包括账户创建、启停控制、持仓/订单查询、日报等。
"""

from fastapi import APIRouter, HTTPException, status, Query, Request
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timedelta
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
    portfolio_uuid: Optional[str] = Field(
        None,
        description="#5648: 关联已有 Portfolio（含策略/选股/仓位/风控组件）作为模拟盘账户；"
                    "提供时校验存在并复用，不新建。未提供则新建空 PAPER 模式 Portfolio（现行行为）",
    )


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


def _map_pt_status(portfolio) -> str:
    """根据 DB portfolio.state 返回前端账户状态字符串。

    Paper account 即 mode=PAPER 的 Portfolio，运行状态由 Worker 在
    deploy/unload 时写入 portfolio.state（RUNNING/STOPPED/...）。

    #5392 #5401: 早期实现 _get_pt_status 读 Redis key pt:status:{id}，但该
    key 从无生产者写入，导致状态永远 fallback 为 "stopped"。改为直接读已持有的
    portfolio.state（list/detail 端点均已持有 portfolio 对象，无需额外查询）。
    """
    from ginkgo.enums import PORTFOLIO_RUNSTATE_TYPES
    state = getattr(portfolio, "state", None)

    # 规范化：DB 枚举字段可能以裸 int 返回（参考 _map_order_status）
    if isinstance(state, int) and not hasattr(state, 'value'):
        try:
            state = PORTFOLIO_RUNSTATE_TYPES(state)
        except ValueError:
            return "error"

    return {
        # 运行中（含过渡态：暂停/停止中/重载/迁移，账户仍在 worker 内）
        PORTFOLIO_RUNSTATE_TYPES.RUNNING: "running",
        PORTFOLIO_RUNSTATE_TYPES.PAUSED: "running",
        PORTFOLIO_RUNSTATE_TYPES.STOPPING: "running",
        PORTFOLIO_RUNSTATE_TYPES.RELOADING: "running",
        PORTFOLIO_RUNSTATE_TYPES.MIGRATING: "running",
        # 未运行
        PORTFOLIO_RUNSTATE_TYPES.VOID: "stopped",
        PORTFOLIO_RUNSTATE_TYPES.INITIALIZED: "stopped",
        PORTFOLIO_RUNSTATE_TYPES.STOPPED: "stopped",
        PORTFOLIO_RUNSTATE_TYPES.OFFLINE: "stopped",
    }.get(state, "error")


def _get_result_service():
    """获取 ResultService 实例"""
    from ginkgo.data.containers import container
    return container.result_service()


def _get_kafka_producer():
    """获取 Kafka Producer"""
    from ginkgo.data.drivers.ginkgo_kafka import GinkgoProducer
    return GinkgoProducer()


def _get_stockinfo_service():
    """获取 StockinfoService 实例（#6048: 查询股票名称）。"""
    from ginkgo.data.containers import container
    return container.stockinfo_service()


def _get_analyzer_service():
    """获取 AnalyzerService 实例（#6048: 查询上一日净资产，走 Service 分层非直访 CRUD）。"""
    from ginkgo.data.containers import container
    return container.analyzer_service()


def _resolve_stock_names(codes: list) -> dict:
    """批量查询股票名称，返回 {code: name}（#6048）。

    去重后逐 code 查询，避免 N+1（同类陷阱见 #5675 settings user-groups）。
    未查到的 code 不进 dict，消费方用 ``names.get(code, "")`` 降级为空。
    """
    unique_codes = {c for c in codes if c}
    if not unique_codes:
        return {}
    svc = _get_stockinfo_service()
    names = {}
    for code in unique_codes:
        result = svc.get_stockinfos(code=code)
        if result.success and result.data:
            # StockInfo Entity 中文字段是 code_name（非 name，arch_stockinfo_entity_code_name_field）。
            # 出口 API key 仍为 "name"（前端契约），值从 code_name 取。
            name = getattr(result.data[0], 'code_name', '') or ''
            if name:
                names[code] = name
    return names


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

@router.get("")
async def list_paper_accounts_root():
    """[兼容旧路由] GET / → 等价于 GET /accounts"""
    return await list_paper_accounts()


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
            position_value = _compute_position_value(_query_positions(p.uuid))
            total_asset = cash + position_value
            today_pnl = _compute_today_pnl(total_asset, _query_previous_net_asset(p.uuid))

            accounts.append({
                "uuid": p.uuid,
                "name": p.name,
                "initial_capital": initial_capital,
                "available_cash": cash,
                "position_value": position_value,
                "total_asset": total_asset,
                "today_pnl": today_pnl,
                "total_pnl": _compute_total_pnl(total_asset, initial_capital),
                "status": _map_pt_status(p),
                "created_at": _format_datetime(getattr(p, 'create_at', None)),
            })

        return ok(
            data=accounts,
            message="Paper accounts retrieved successfully"
        )

    except BusinessError:
        raise
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing paper accounts: {str(e)}")
        raise BusinessError(f"Error listing paper accounts: {str(e)}")


@router.post("/accounts", status_code=status.HTTP_201_CREATED)
async def create_paper_account(data: CreatePaperAccountRequest):
    """创建模拟盘账户

    创建 PAPER 模式的 Portfolio，并通过 Kafka 通知 Worker。
    #5648: 若提供 portfolio_uuid，则关联已有 Portfolio（复用其策略组件），不新建。
    """
    try:
        # #5648: 关联已有 Portfolio（复用已绑定策略/选股/仓位/风控组件），不新建
        if data.portfolio_uuid:
            _require_portfolio(data.portfolio_uuid)  # 不存在则 raise NotFoundError
            # #5648 review: 关联时设 mode=PAPER，使 list_paper_accounts 按 mode 过滤能查到
            # （与新建路径 add(mode=PAPER) 对称；已部署冻结的 update 被拒则穿透 BusinessError）
            from ginkgo.enums import PORTFOLIO_MODE_TYPES
            portfolio_service = _get_portfolio_service()
            upd = portfolio_service.update(data.portfolio_uuid, mode=PORTFOLIO_MODE_TYPES.PAPER)
            if not upd.is_success():
                raise BusinessError(f"Failed to link paper account: {upd.error}")
            logger.info(f"Paper account linked to existing portfolio: {data.portfolio_uuid}")
            return ok(
                data={"account_id": data.portfolio_uuid},
                message="Paper account linked to existing portfolio",
            )

        from ginkgo.enums import PORTFOLIO_MODE_TYPES
        from ginkgo.interfaces.kafka_topics import KafkaTopics

        portfolio_service = _get_portfolio_service()

        result = portfolio_service.add(
            name=data.name,
            mode=PORTFOLIO_MODE_TYPES.PAPER,
            description=f"Paper trading account, initial_capital={data.initial_capital}",
            initial_capital=data.initial_capital,
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
            data={"uuid": portfolio_id},
            message="Paper account created successfully"
        )

    except BusinessError:
        raise
    except NotFoundError:
        # #5648: _require_portfolio 校验 portfolio_uuid 不存在时穿透为 404，
        # 不被下方 except Exception 包装成模糊 BusinessError
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
        position_value = _compute_position_value(positions)
        total_asset = cash + position_value
        today_pnl = _compute_today_pnl(total_asset, _query_previous_net_asset(account_id))

        # 查询活跃订单（pending 状态）
        orders = _query_orders(account_id, status_filter=["pending"])

        return ok(
            data={
                "uuid": p.uuid,
                "name": p.name,
                "initial_capital": initial_capital,
                "available_cash": cash,
                "position_value": position_value,
                "total_asset": total_asset,
                "today_pnl": today_pnl,
                "total_pnl": _compute_total_pnl(total_asset, initial_capital),
                "status": _map_pt_status(p),
                "created_at": _format_datetime(getattr(p, 'create_at', None)),
                "positions": positions,
                "active_orders": orders,
                "today_trades": [],  # TODO: 从 order_record 查询当日成交
            },
            message="Paper account retrieved successfully"
        )

    except NotFoundError:
        raise
    except HTTPException:
        # 透传 helper 的 HTTPException(500)，避免被下方 except Exception 吞成 BusinessError(400)。
        # HTTPException 继承 Exception，须显式前置 except，否则 AC1 生产路径返 400 非 500。
        raise
    except Exception as e:
        logger.error(f"Error getting paper account {account_id}: {str(e)}")
        raise BusinessError(f"Error getting paper account: {str(e)}")


@router.post("/{account_id}/start", deprecated=True, status_code=410)
async def start_paper_trading(account_id: str, data: StartPaperTradingRequest = None):
    """[DEPRECATED] 此端点已废弃，请使用 POST /api/v1/portfolios/{uuid}/start

    原 Kafka ControlCommand.deploy 投递到 CONTROL_COMMANDS topic，但 worker 只消费
    DATA_COMMANDS（worker.py:31 数据采集专用），topic 不匹配无消费者，命令发出后无人
    处理，账户状态永不变。改返回 410 Gone + 迁移指引（#5860 A 方案）。「真启动引擎」
    需 worker 改消费 CONTROL_COMMANDS，属基础设施改造，新旧端点同受影响，超本端点范围。
    """
    raise BusinessError(
        "POST /api/v1/paper-trading/{account_id}/start is deprecated and no longer functional. "
        "Use POST /api/v1/portfolios/{uuid}/start instead.",
        code=410,
    )


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
    except HTTPException:
        # 透传 helper 的 HTTPException(500)，避免被 except Exception 吞成 BusinessError(400)（AC1）。
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
    except HTTPException:
        # 透传 helper 的 HTTPException(500)，避免被 except Exception 吞成 BusinessError(400)（AC1）。
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
        position_value = _compute_position_records_value(positions)
        total_asset = cash + position_value

        total_return = _compute_return_rate(total_asset, initial_capital)
        previous_net_asset = _query_previous_net_asset(account_id, target_date)
        daily_return = _compute_daily_return(total_asset, previous_net_asset)

        return ok(
            data={
                "date": target_date,
                "total_return": total_return,
                "daily_return": daily_return,
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
    result_service = _get_result_service()
    positions_result = result_service.get_current_positions(account_id, min_volume=1)
    if not positions_result.success:
        # DB 故障：propagate 为 500（global_error_handler 加 trace_id），不吞为空列表 (#5479)
        raise HTTPException(status_code=500, detail=f"查询持仓失败: {positions_result.error}")
    records = positions_result.data

    # #6048: 批量查股票名称（去重避免 N+1）
    names = _resolve_stock_names([getattr(r, 'code', '') for r in (records or [])])

    positions = []
    for r in (records or []):
        code = getattr(r, 'code', '')
        cost = float(getattr(r, 'cost', 0) or 0)
        price = float(getattr(r, 'price', 0) or 0)
        volume = int(getattr(r, 'volume', 0) or 0)
        market_value = price * volume

        pnl = market_value - cost if cost > 0 else 0
        pnl_ratio = (pnl / cost * 100) if cost > 0 else 0

        positions.append({
            "code": code,
            "name": names.get(code, ""),  # #6048: 从 stock_info 查询
            "shares": volume,
            "cost": round(cost, 4),
            "current": round(price, 4),
            "market_value": round(market_value, 2),
            "pnl": round(pnl, 2),
            "pnl_ratio": round(pnl_ratio, 2),
            "updated_at": _format_datetime(getattr(r, 'timestamp', None)),
        })

    return positions


def _compute_position_value(positions: list) -> float:
    """从持仓列表计算总市值（Σ market_value）。

    用于 ``list_paper_accounts`` / ``get_paper_account`` 的 ``position_value``
    字段（#6048：替代硬编码 0）。``positions`` 来自 ``_query_positions``，每个
    dict 含 ``market_value``（price * volume，``_query_positions``）。缺键按 0
    容错（不崩），非数值安全降级为 0。
    """
    try:
        return round(
            sum(float(p.get("market_value", 0) or 0) for p in (positions or [])),
            2,
        )
    except (TypeError, ValueError):
        return 0.0


def _compute_position_records_value(positions: list) -> float:
    """从持仓记录对象计算总市值（price * volume）。"""
    try:
        return round(
            sum(
                float(getattr(p, "price", 0) or 0) * int(getattr(p, "volume", 0) or 0)
                for p in (positions or [])
            ),
            2,
        )
    except (TypeError, ValueError):
        return 0.0


def _compute_total_pnl(total_asset: float, initial_capital: float) -> float:
    """计算总盈亏 = 当前净资产 − 初始资金（#6048）。

    含已实现盈亏（体现在 cash 变化）+ 未实现盈亏（体现在持仓市值）。
    用于 ``list_paper_accounts`` / ``get_paper_account`` 的 ``total_pnl``
    字段（替代硬编码 0）。非数值入参安全降级为 0.0（不崩）。
    """
    try:
        return round(float(total_asset) - float(initial_capital), 2)
    except (TypeError, ValueError):
        return 0.0


def _compute_return_rate(total_asset: float, initial_capital: float) -> float:
    """计算累计收益率百分比。"""
    try:
        initial = float(initial_capital)
        if initial <= 0:
            return 0.0
        return round((float(total_asset) / initial - 1) * 100, 4)
    except (TypeError, ValueError):
        return 0.0


def _compute_today_pnl(total_asset: float, previous_net_asset: Optional[float]) -> float:
    """计算今日盈亏；缺少上一日净资产时降级为 0。"""
    try:
        if previous_net_asset is None or float(previous_net_asset) <= 0:
            return 0.0
        return round(float(total_asset) - float(previous_net_asset), 2)
    except (TypeError, ValueError):
        return 0.0


def _compute_daily_return(total_asset: float, previous_net_asset: Optional[float]) -> float:
    """计算日收益率百分比；缺少上一日净资产时降级为 0。"""
    try:
        previous = float(previous_net_asset)
        if previous <= 0:
            return 0.0
        return round((float(total_asset) / previous - 1) * 100, 4)
    except (TypeError, ValueError):
        return 0.0


def _target_day_start(target_date: Optional[str] = None) -> Optional[datetime]:
    """返回目标日期 00:00；非法日期返回 None。"""
    if target_date:
        try:
            return datetime.strptime(str(target_date), "%Y-%m-%d")
        except (TypeError, ValueError):
            return None
    now = datetime.now()
    return datetime(now.year, now.month, now.day)


def _record_value(records) -> Optional[float]:
    """提取查询结果第一条 analyzer value。"""
    items = records if isinstance(records, list) else getattr(records, "data", [])
    if not items:
        return None
    try:
        value = float(getattr(items[0], "value", 0) or 0)
        return value if value > 0 else None
    except (TypeError, ValueError):
        return None


def _query_previous_net_asset(account_id: str, target_date: Optional[str] = None) -> Optional[float]:
    """查询目标日前最近一条 net_value 分析器记录。

    NetValue analyzer 记录的是组合总资产（worth），不是归一化净值；因此可直接作为
    ``today_pnl`` / ``daily_return`` 的上一期净资产基准。没有记录时返回 None。
    """
    day_start = _target_day_start(target_date)
    if day_start is None:
        return None

    end_time = day_start - timedelta(microseconds=1)
    analyzer_service = _get_analyzer_service()
    for use_business_time in (True, False):
        result = analyzer_service.find_latest_before(
            portfolio_id=account_id,
            end_time=end_time,
            analyzer_name="net_value",
            use_business_time=use_business_time,
        )
        if not result.success:
            # DB 故障：propagate 为 500（对齐 _query_positions, #5479 / 544c851c），
            # 不吞为 None 让 today_pnl/daily_return 静默归 0。
            raise HTTPException(
                status_code=500,
                detail=f"查询上一日净资产失败: {result.error}",
            )
        value = _record_value(result.data)
        if value is not None:
            return value
    return None


def _expand_status_enums(status_filter: Optional[List[str]]) -> list:
    """将状态过滤字符串列表展开为 ORDERSTATUS_TYPES enum 列表（去重、保序）。

    #6047: 多状态查询须展开所有匹配 enum（如 pending → NEW + SUBMITTED），
    不再只取首个状态组或同组首个 enum。返回空列表表示无过滤（查全部）。
    """
    from ginkgo.enums import ORDERSTATUS_TYPES

    if not status_filter:
        return []

    status_mapping = {
        "pending": [ORDERSTATUS_TYPES.NEW, ORDERSTATUS_TYPES.SUBMITTED],
        "partial": [ORDERSTATUS_TYPES.PARTIAL_FILLED],
        "filled": [ORDERSTATUS_TYPES.FILLED],
        "cancelled": [ORDERSTATUS_TYPES.CANCELED],
        "rejected": [ORDERSTATUS_TYPES.REJECTED],
    }

    expanded: list = []
    seen = set()
    for s in status_filter:
        for enum in status_mapping.get(s, []):
            if enum not in seen:
                seen.add(enum)
                expanded.append(enum)
    return expanded


def _query_orders(account_id: str, status_filter: Optional[List[str]] = None) -> list:
    """查询指定账户的订单列表"""
    result_service = _get_result_service()

    # #6047: 展开多状态过滤为 enum 集合，每个 enum 各查一次合并去重（IN 语义）。
    status_enums = _expand_status_enums(status_filter)

    # service 仅支持单 status int：逐 enum 查询并合并去重，等价于 SQL IN (#5479)
    if status_enums:
        records = []
        seen_ids = set()
        for e in status_enums:
            r = result_service.get_orders_by_portfolio(
                account_id, status=e.value, page_size=100,
            )
            if not r.success:
                # DB 故障：propagate 为 500（global_error_handler 加 trace_id），不吞为空列表 (#5479)
                raise HTTPException(status_code=500, detail=f"查询订单失败: {r.error}")
            for rec in ((r.data or {}).get("data", []) or []):
                oid = getattr(rec, 'uuid', '') or getattr(rec, 'order_id', '')
                if oid and oid in seen_ids:
                    continue
                if oid:
                    seen_ids.add(oid)
                records.append(rec)
    else:
        orders_result = result_service.get_orders_by_portfolio(
            account_id, status=None, page_size=100,
        )
        if not orders_result.success:
            raise HTTPException(status_code=500, detail=f"查询订单失败: {orders_result.error}")
        records = (orders_result.data or {}).get("data", [])

    # #6048: 批量查股票名称（去重避免 N+1）
    names = _resolve_stock_names([getattr(r, 'code', '') for r in (records or [])])

    orders = []
    for r in (records or []):
        direction = getattr(r, 'direction', 0)
        direction_value = direction.value if hasattr(direction, 'value') else int(direction)
        side = "buy" if direction_value == 1 else "sell"

        order_id = getattr(r, 'uuid', '') or getattr(r, 'order_id', '')
        code = getattr(r, 'code', '')

        orders.append({
            "order_id": order_id,
            "strategy_id": "",
            "account_id": account_id,
            "code": code,
            "name": names.get(code, ""),  # #6048: 从 stock_info 查询
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
