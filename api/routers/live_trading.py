"""
API Gateway - Live Trading Router

提供实盘交易API接口:
- 实盘账号CRUD操作
- API凭证验证
- 账号余额查询

使用FastAPI实现RESTful API接口
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/accounts",
    tags=["accounts"]
)


# ============================================================================
# 实盘账号CRUD接口
# ============================================================================

@router.get("/")
async def list_accounts(
    exchange: Optional[str] = Query(None, description="过滤交易所"),
    environment: Optional[str] = Query(None, description="过滤环境"),
    status: Optional[str] = Query(None, description="过滤状态")
) -> Dict:
    """
    获取实盘账号列表

    Returns:
        Dict: 账号列表
    """
    try:
        from ginkgo.data.containers import container

        # TODO: 从认证中获取user_id
        user_id = "default_user"  # 需要从JWT中提取

        service = container.live_account_service()
        result = service.get_user_accounts(
            user_id=user_id,
            page=1,
            page_size=100,
            exchange=exchange,
            environment=environment,
            status=status
        )

        if result["success"]:
            return {
                "code": 0,
                "message": "success",
                "data": result["data"]["accounts"]
            }
        else:
            raise HTTPException(status_code=400, detail=result["message"])

    except Exception as e:
        logger.error(f"Failed to list accounts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/")
async def create_account(account_data: Dict) -> Dict:
    """
    创建实盘账号

    Request Body:
        {
            "name": str,
            "exchange": str (okx/binance),
            "environment": str (production/testnet),
            "api_key": str,
            "api_secret": str,
            "passphrase": str (OKX需要),
            "description": str (可选),
            "auto_validate": bool (默认false)
        }

    Returns:
        Dict: 创建的账号信息
    """
    try:
        from ginkgo.data.containers import container

        # TODO: 从认证中获取user_id
        user_id = "default_user"  # 需要从JWT中提取

        service = container.live_account_service()
        result = service.create_account(
            user_id=user_id,
            exchange=account_data.get("exchange"),
            name=account_data.get("name"),
            api_key=account_data.get("api_key"),
            api_secret=account_data.get("api_secret"),
            passphrase=account_data.get("passphrase"),
            environment=account_data.get("environment", "testnet"),
            description=account_data.get("description"),
            auto_validate=account_data.get("auto_validate", False)
        )

        if result["success"]:
            return {
                "code": 0,
                "message": "Account created successfully",
                "data": result["data"]
            }
        else:
            raise HTTPException(status_code=400, detail=result["message"])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create account: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{account_id}")
async def get_account(account_id: str) -> Dict:
    """
    获取实盘账号详情

    Args:
        account_id: 账号UUID

    Returns:
        Dict: 账号详情
    """
    try:
        from ginkgo.data.containers import container

        service = container.live_account_service()
        result = service.get_account_by_uuid(account_id)

        if result["success"]:
            return {
                "code": 0,
                "message": "success",
                "data": result["data"]
            }
        else:
            raise HTTPException(status_code=404, detail=result.get("message", "Account not found"))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get account {account_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{account_id}")
async def update_account(account_id: str, account_data: Dict) -> Dict:
    """
    更新实盘账号信息

    Args:
        account_id: 账号UUID

    Request Body:
        {
            "name": str (可选),
            "api_key": str (可选),
            "api_secret": str (可选),
            "passphrase": str (可选),
            "description": str (可选)
        }

    Returns:
        Dict: 更新后的账号信息
    """
    try:
        from ginkgo.data.containers import container

        service = container.live_account_service()
        result = service.update_account(
            account_uuid=account_id,
            name=account_data.get("name"),
            api_key=account_data.get("api_key"),
            api_secret=account_data.get("api_secret"),
            passphrase=account_data.get("passphrase"),
            description=account_data.get("description")
        )

        if result["success"]:
            return {
                "code": 0,
                "message": "Account updated successfully",
                "data": result["data"]
            }
        else:
            raise HTTPException(status_code=400, detail=result["message"])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update account {account_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{account_id}")
async def delete_account(account_id: str) -> Dict:
    """
    删除实盘账号（软删除）

    Args:
        account_id: 账号UUID

    Returns:
        Dict: 删除结果
    """
    try:
        from ginkgo.data.containers import container

        service = container.live_account_service()
        result = service.delete_account(account_id)

        if result["success"]:
            return {
                "code": 0,
                "message": "Account deleted successfully"
            }
        else:
            raise HTTPException(status_code=404, detail=result.get("message", "Account not found"))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete account {account_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{account_id}/validate")
async def validate_account(account_id: str) -> Dict:
    """
    验证实盘账号API凭证

    Args:
        account_id: 账号UUID

    Returns:
        Dict: 验证结果
        {
            "valid": bool,
            "message": str,
            "account_info": dict
        }
    """
    try:
        from ginkgo.data.containers import container

        service = container.live_account_service()
        result = service.validate_account(account_id)

        if result["success"]:
            return {
                "code": 0,
                "message": "Validation successful",
                "data": {
                    "valid": result.get("valid", False),
                    "message": result.get("message", ""),
                    "account_info": result.get("account_info")
                }
            }
        else:
            # 验证失败也返回200，但valid=false
            return {
                "code": 0,
                "message": result.get("message", "Validation failed"),
                "data": {
                    "valid": False,
                    "error": result.get("message", "")
                }
            }

    except Exception as e:
        logger.error(f"Failed to validate account {account_id}: {e}")
        return {
            "code": 0,
            "message": "Validation error",
            "data": {
                "valid": False,
                "error": str(e)
            }
        }


@router.get("/{account_id}/balance")
async def get_account_balance(account_id: str) -> Dict:
    """
    获取账户余额信息

    Args:
        account_id: 账号UUID

    Returns:
        Dict: 余额信息
        {
            "total_equity": str,
            "available_balance": str,
            "frozen_balance": str,
            "currency_balances": list
        }
    """
    try:
        from ginkgo.data.containers import container

        service = container.live_account_service()
        result = service.get_account_balance(account_id)

        if result["success"]:
            return {
                "code": 0,
                "message": "Balance retrieved successfully",
                "data": result["data"]
            }
        else:
            raise HTTPException(status_code=400, detail=result["message"])

    except Exception as e:
        logger.error(f"Failed to get account balance {account_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{account_id}/status")
async def update_account_status(account_id: str, status_data: Dict) -> Dict:
    """
    更新账号状态

    Args:
        account_id: 账号UUID

    Request Body:
        {
            "status": str (enabled/disabled)
        }

    Returns:
        Dict: 更新结果
    """
    try:
        from ginkgo.data.containers import container

        status = status_data.get("status")
        if not status:
            raise HTTPException(status_code=400, detail="status is required")

        service = container.live_account_service()
        result = service.update_account_status(account_id, status)

        if result["success"]:
            return {
                "code": 0,
                "message": "Account status updated successfully",
                "data": result["data"]
            }
        else:
            raise HTTPException(status_code=400, detail=result["message"])

    except Exception as e:
        logger.error(f"Failed to update account status {account_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Broker管理端点
# ============================================================================

@router.get("/brokers")
async def list_brokers(
    portfolio_id: Optional[str] = None,
    state: Optional[str] = None
) -> Dict:
    """
    获取Broker实例列表

    Args:
        portfolio_id: 过滤Portfolio ID
        state: 过滤状态

    Returns:
        Dict: Broker实例列表
    """
    try:
        from ginkgo.data.containers import container

        broker_crud = container.broker_instance()

        filters = {"is_del": False}
        if portfolio_id:
            filters["portfolio_id"] = portfolio_id
        if state:
            filters["state"] = state

        brokers = broker_crud.find(filters=filters)

        # 为每个Broker加载实盘账号信息
        live_account_crud = container.live_account()
        for broker in brokers:
            try:
                live_account = live_account_crud.get(broker.live_account_id)
                if live_account:
                    broker.live_account = {
                        "uuid": live_account.uuid,
                        "name": live_account.name,
                        "exchange": live_account.exchange,
                        "environment": live_account.environment
                    }
            except:
                pass

        return {
            "code": 0,
            "message": "success",
            "data": brokers
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list brokers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/brokers/{broker_uuid}/start")
async def start_broker(broker_uuid: str) -> Dict:
    """
    启动Broker实例

    Args:
        broker_uuid: Broker实例UUID

    Returns:
        Dict: 启动结果
    """
    try:
        from ginkgo.trading.brokers.broker_manager import get_broker_manager

        broker_manager = get_broker_manager()

        # 获取Broker信息
        broker_crud = container.broker_instance()
        broker = broker_crud.get_broker_by_uuid(broker_uuid)
        if not broker:
            raise HTTPException(status_code=404, detail="Broker not found")

        # 启动Broker
        success = broker_manager.start_broker(broker.portfolio_id)

        if success:
            return {
                "code": 0,
                "message": "Broker started successfully",
                "data": {"broker_uuid": broker_uuid, "state": "running"}
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to start broker")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start broker {broker_uuid}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/brokers/{broker_uuid}/pause")
async def pause_broker(broker_uuid: str) -> Dict:
    """
    暂停Broker实例

    Args:
        broker_uuid: Broker实例UUID

    Returns:
        Dict: 暂停结果
    """
    try:
        from ginkgo.trading.brokers.broker_manager import get_broker_manager

        broker_manager = get_broker_manager()

        # 获取Broker信息
        broker_crud = container.broker_instance()
        broker = broker_crud.get_broker_by_uuid(broker_uuid)
        if not broker:
            raise HTTPException(status_code=404, detail="Broker not found")

        # 暂停Broker
        success = broker_manager.pause_broker(broker.portfolio_id)

        if success:
            return {
                "code": 0,
                "message": "Broker paused successfully",
                "data": {"broker_uuid": broker_uuid, "state": "paused"}
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to pause broker")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to pause broker {broker_uuid}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/brokers/{broker_uuid}/resume")
async def resume_broker(broker_uuid: str) -> Dict:
    """
    恢复Broker实例

    Args:
        broker_uuid: Broker实例UUID

    Returns:
        Dict: 恢复结果
    """
    try:
        from ginkgo.trading.brokers.broker_manager import get_broker_manager

        broker_manager = get_broker_manager()

        # 获取Broker信息
        broker_crud = container.broker_instance()
        broker = broker_crud.get_broker_by_uuid(broker_uuid)
        if not broker:
            raise HTTPException(status_code=404, detail="Broker not found")

        # 恢复Broker
        success = broker_manager.resume_broker(broker.portfolio_id)

        if success:
            return {
                "code": 0,
                "message": "Broker resumed successfully",
                "data": {"broker_uuid": broker_uuid, "state": "running"}
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to resume broker")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resume broker {broker_uuid}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/brokers/{broker_uuid}/stop")
async def stop_broker(broker_uuid: str) -> Dict:
    """
    停止Broker实例

    Args:
        broker_uuid: Broker实例UUID

    Returns:
        Dict: 停止结果
    """
    try:
        from ginkgo.trading.brokers.broker_manager import get_broker_manager

        broker_manager = get_broker_manager()

        # 获取Broker信息
        broker_crud = container.broker_instance()
        broker = broker_crud.get_broker_by_uuid(broker_uuid)
        if not broker:
            raise HTTPException(status_code=404, detail="Broker not found")

        # 停止Broker
        success = broker_manager.stop_broker(broker.portfolio_id)

        if success:
            return {
                "code": 0,
                "message": "Broker stopped successfully",
                "data": {"broker_uuid": broker_uuid, "state": "stopped"}
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to stop broker")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to stop broker {broker_uuid}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/brokers/emergency-stop")
async def emergency_stop_all() -> Dict:
    """
    紧急停止所有Broker实例

    Returns:
        Dict: 停止结果
    """
    try:
        from ginkgo.trading.brokers.broker_manager import get_broker_manager

        broker_manager = get_broker_manager()

        # 紧急停止所有Broker
        stopped_count = broker_manager.emergency_stop_all()

        return {
            "code": 0,
            "message": f"Emergency stop completed: {stopped_count} brokers stopped",
            "data": {"stopped_count": stopped_count}
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to emergency stop brokers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Trade History Endpoints
# ============================================================================

@router.get("/accounts/{account_id}/trades")
async def get_account_trades(
    account_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    symbol: Optional[str] = None,
    limit: int = 1000
) -> Dict:
    """
    获取实盘账号的交易历史

    Args:
        account_id: 实盘账号ID
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)
        symbol: 过滤交易标的
        limit: 返回记录数限制

    Returns:
        Dict: 交易记录列表
    """
    try:
        from ginkgo.data.containers import container
        from datetime import datetime

        trade_crud = container.trade_record()

        # 转换日期字符串
        start_dt = datetime.strptime(start_date, "%Y-%m-%d") if start_date else None
        end_dt = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None

        trades = trade_crud.get_trades_by_account(
            live_account_id=account_id,
            start_date=start_dt,
            end_date=end_dt,
            symbol=symbol,
            limit=limit
        )

        # 转换为字典格式
        trade_list = []
        for trade in trades:
            trade_list.append({
                "uuid": trade.uuid,
                "symbol": trade.symbol,
                "side": trade.side,
                "price": float(trade.price),
                "quantity": float(trade.quantity),
                "quote_quantity": float(trade.quote_quantity) if trade.quote_quantity else None,
                "fee": float(trade.fee) if trade.fee else None,
                "fee_currency": trade.fee_currency,
                "exchange_order_id": trade.exchange_order_id,
                "exchange_trade_id": trade.exchange_trade_id,
                "order_type": trade.order_type,
                "trade_time": trade.trade_time.isoformat()
            })

        return {
            "code": 0,
            "message": "success",
            "data": trade_list
        }

    except Exception as e:
        logger.error(f"Failed to get trades for account {account_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/accounts/{account_id}/trades/statistics")
async def get_trade_statistics(
    account_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Dict:
    """
    获取交易统计数据

    Args:
        account_id: 实盘账号ID
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)

    Returns:
        Dict: 统计数据
    """
    try:
        from ginkgo.data.containers import container
        from datetime import datetime

        trade_crud = container.trade_record()

        start_dt = datetime.strptime(start_date, "%Y-%m-%d") if start_date else None
        end_dt = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None

        stats = trade_crud.get_trade_statistics(
            live_account_id=account_id,
            start_date=start_dt,
            end_date=end_dt
        )

        return {
            "code": 0,
            "message": "success",
            "data": stats
        }

    except Exception as e:
        logger.error(f"Failed to get trade statistics for account {account_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/accounts/{account_id}/trades/daily-summary")
async def get_daily_trade_summary(
    account_id: str,
    days: int = 30
) -> Dict:
    """
    获取每日交易汇总

    Args:
        account_id: 实盘账号ID
        days: 查询天数

    Returns:
        Dict: 每日汇总数据
    """
    try:
        from ginkgo.data.containers import container

        trade_crud = container.trade_record()

        summary = trade_crud.get_daily_trade_summary(
            live_account_id=account_id,
            days=days
        )

        # 转换日期为字符串
        for day_data in summary:
            day_data["date"] = day_data["date"].isoformat()

        return {
            "code": 0,
            "message": "success",
            "data": summary
        }

    except Exception as e:
        logger.error(f"Failed to get daily summary for account {account_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/accounts/{account_id}/trades/export")
async def export_trades_csv(
    account_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Dict:
    """
    导出交易记录为CSV

    Args:
        account_id: 实盘账号ID
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)

    Returns:
        Dict: 包含CSV数据的响应
    """
    try:
        from ginkgo.data.containers import container
        from datetime import datetime

        trade_crud = container.trade_record()

        start_dt = datetime.strptime(start_date, "%Y-%m-%d") if start_date else None
        end_dt = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None

        csv_data = trade_crud.export_to_csv(
            live_account_id=account_id,
            start_date=start_dt,
            end_date=end_dt
        )

        return {
            "code": 0,
            "message": "success",
            "data": {
                "filename": f"trades_{account_id}_{datetime.now().strftime('%Y%m%d')}.csv",
                "content": csv_data
            }
        }

    except Exception as e:
        logger.error(f"Failed to export trades for account {account_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

