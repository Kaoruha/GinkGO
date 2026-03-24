"""
市场数据API路由

提供前端交易对订阅管理接口：
- GET /api/v1/market/pairs - 获取交易对列表
- GET /api/v1/market/subscriptions - 获取订阅列表
- POST /api/v1/market/subscriptions - 创建订阅
- DELETE /api/v1/market/subscriptions/{uuid} - 删除订阅
- PUT /api/v1/market/subscriptions/{uuid} - 更新订阅
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/market",
    tags=["market"]
)


# ============================================================================
# 交易对接口
# ============================================================================

@router.get("/pairs")
async def get_trading_pairs(
    exchange: str = Query("okx", description="交易所 (okx/binance)"),
    environment: str = Query("production", description="环境 (production/testnet)"),
    quote_ccy: Optional[str] = Query(None, description="计价货币过滤 (如 USDT)"),
    search: Optional[str] = Query(None, description="搜索关键词")
) -> Dict:
    """
    获取交易对列表

    Returns:
        Dict: 交易对列表
        {
            "code": 0,
            "message": "success",
            "data": {
                "pairs": [
                    {
                        "symbol": "BTC-USDT",
                        "base_currency": "BTC",
                        "quote_currency": "USDT",
                        "state": "live",
                        "list_time": "2021-01-01T00:00:00Z"
                    },
                    ...
                ],
                "total": 1114
            }
        }
    """
    try:
        if exchange.lower() == "okx":
            from ginkgo.trading.feeders.okx_feeder import OKXMarketDataFeeder

            feeder = OKXMarketDataFeeder(environment=environment)

            # 获取现货交易对
            instruments = feeder.get_instruments(inst_type="SPOT")

            # 转换为标准格式
            pairs = []
            for inst in instruments:
                # 只返回状态为 live 的交易对
                if inst.get("state") != "live":
                    continue

                inst_id = inst.get("instId", "")

                # 过滤计价货币
                if quote_ccy and not inst_id.endswith(f"-{quote_ccy}"):
                    continue

                # 搜索过滤
                if search and search.upper() not in inst_id:
                    continue

                pairs.append({
                    "symbol": inst_id,
                    "base_currency": inst.get("baseCcy", ""),
                    "quote_currency": inst.get("quoteCcy", ""),
                    "state": inst.get("state", ""),
                    "list_time": inst.get("listTime", ""),
                    "tick_size": inst.get("tickSz", ""),
                    "lot_size": inst.get("lotSz", ""),
                    "min_size": inst.get("minSz", "")
                })

            return {
                "code": 0,
                "message": "success",
                "data": {
                    "pairs": pairs,
                    "total": len(pairs),
                    "exchange": exchange,
                    "environment": environment
                }
            }

        else:
            raise HTTPException(status_code=400, detail=f"Unsupported exchange: {exchange}")

    except Exception as e:
        logger.error(f"Failed to get trading pairs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 订阅管理接口
# ============================================================================

@router.get("/subscriptions")
async def get_subscriptions(
    exchange: Optional[str] = Query(None, description="过滤交易所"),
    environment: Optional[str] = Query(None, description="过滤环境"),
    active_only: bool = Query(True, description="只返回活跃订阅")
) -> Dict:
    """
    获取用户的订阅列表

    Returns:
        Dict: 订阅列表
    """
    try:
        from ginkgo.data.containers import container

        # TODO: 从认证中获取user_id
        user_id = "default_user"

        subscription_crud = container.market_subscription_crud()

        subscriptions = subscription_crud.get_user_subscriptions(
            user_id=user_id,
            exchange=exchange,
            environment=environment,
            active_only=active_only
        )

        # 转换为字典格式
        subscription_list = []
        for sub in subscriptions:
            subscription_list.append({
                "uuid": sub.uuid,
                "exchange": sub.exchange,
                "environment": sub.environment,
                "symbol": sub.symbol,
                "data_types": sub.get_data_types(),
                "is_active": sub.is_active,
                "create_at": sub.create_at.isoformat() if sub.create_at else None,
                "update_at": sub.update_at.isoformat() if sub.update_at else None
            })

        return {
            "code": 0,
            "message": "success",
            "data": {
                "subscriptions": subscription_list,
                "total": len(subscription_list)
            }
        }

    except Exception as e:
        logger.error(f"Failed to get subscriptions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/subscriptions")
async def create_subscription(subscription_data: Dict) -> Dict:
    """
    创建订阅

    Request Body:
        {
            "exchange": str (okx/binance),
            "symbol": str,
            "data_types": list[str] (可选，默认 ["ticker"]),
            "environment": str (可选，默认 testnet)
        }

    Returns:
        Dict: 创建的订阅信息
    """
    try:
        from ginkgo.data.containers import container

        # TODO: 从认证中获取user_id
        user_id = "default_user"

        subscription_crud = container.market_subscription_crud()

        # 验证参数
        exchange = subscription_data.get("exchange")
        symbol = subscription_data.get("symbol")
        data_types = subscription_data.get("data_types", ["ticker"])
        environment = subscription_data.get("environment", "testnet")

        if not exchange or not symbol:
            raise HTTPException(status_code=400, detail="exchange and symbol are required")

        # 创建订阅
        subscription = subscription_crud.add_subscription(
            user_id=user_id,
            exchange=exchange,
            symbol=symbol,
            data_types=data_types,
            environment=environment
        )

        # 通知 DataManager 订阅新交易对
        try:
            from ginkgo.livecore.data_manager import get_data_manager
            dm = get_data_manager()
            dm.subscribe_live_data([symbol], source=exchange)
        except Exception as dm_error:
            logger.warning(f"Failed to notify DataManager: {dm_error}")

        return {
            "code": 0,
            "message": "Subscription created successfully",
            "data": {
                "uuid": subscription.uuid,
                "exchange": subscription.exchange,
                "symbol": subscription.symbol,
                "data_types": subscription.get_data_types(),
                "environment": subscription.environment
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create subscription: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/subscriptions/{subscription_uuid}")
async def update_subscription(
    subscription_uuid: str,
    subscription_data: Dict
) -> Dict:
    """
    更新订阅

    Args:
        subscription_uuid: 订阅UUID

    Request Body:
        {
            "data_types": list[str] (可选),
            "is_active": bool (可选)
        }

    Returns:
        Dict: 更新后的订阅信息
    """
    try:
        from ginkgo.data.containers import container

        subscription_crud = container.market_subscription_crud()

        data_types = subscription_data.get("data_types")
        is_active = subscription_data.get("is_active")

        subscription = subscription_crud.update_subscription(
            uuid=subscription_uuid,
            data_types=data_types,
            is_active=is_active
        )

        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")

        return {
            "code": 0,
            "message": "Subscription updated successfully",
            "data": {
                "uuid": subscription.uuid,
                "exchange": subscription.exchange,
                "symbol": subscription.symbol,
                "data_types": subscription.get_data_types(),
                "is_active": subscription.is_active
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update subscription {subscription_uuid}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/subscriptions/{subscription_uuid}")
async def delete_subscription(subscription_uuid: str) -> Dict:
    """
    删除订阅

    Args:
        subscription_uuid: 订阅UUID

    Returns:
        Dict: 删除结果
    """
    try:
        from ginkgo.data.containers import container

        subscription_crud = container.market_subscription_crud()

        # 先获取订阅信息
        subscription = subscription_crud.get_subscription_by_uuid(subscription_uuid)
        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")

        # 通知 DataManager 取消订阅
        try:
            from ginkgo.livecore.data_manager import get_data_manager
            dm = get_data_manager()
            dm.unsubscribe_live_data([subscription.symbol])
        except Exception as dm_error:
            logger.warning(f"Failed to notify DataManager: {dm_error}")

        # 删除订阅
        success = subscription_crud.remove_subscription(subscription_uuid)

        if success:
            return {
                "code": 0,
                "message": "Subscription deleted successfully"
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to delete subscription")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete subscription {subscription_uuid}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 行情数据接口
# ============================================================================

@router.get("/ticker/{symbol}")
async def get_ticker(
    symbol: str,
    exchange: str = Query("okx", description="交易所"),
    environment: str = Query("production", description="环境")
) -> Dict:
    """
    获取交易对行情

    Args:
        symbol: 交易对代码 (如 BTC-USDT)

    Returns:
        Dict: 行情数据
    """
    try:
        if exchange.lower() == "okx":
            from ginkgo.trading.feeders.okx_feeder import OKXMarketDataFeeder

            feeder = OKXMarketDataFeeder(environment=environment)
            ticker_data = feeder.get_ticker(symbol)

            if not ticker_data:
                raise HTTPException(status_code=404, detail=f"Ticker not found for {symbol}")

            return {
                "code": 0,
                "message": "success",
                "data": ticker_data
            }

        else:
            raise HTTPException(status_code=400, detail=f"Unsupported exchange: {exchange}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get ticker for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tickers")
async def get_all_tickers(
    exchange: str = Query("okx", description="交易所"),
    environment: str = Query("production", description="环境"),
    inst_type: str = Query("SPOT", description="产品类型")
) -> Dict:
    """
    获取所有交易对行情

    Returns:
        Dict: 所有交易对行情数据
    """
    try:
        if exchange.lower() == "okx":
            from ginkgo.trading.feeders.okx_feeder import OKXMarketDataFeeder

            feeder = OKXMarketDataFeeder(environment=environment)
            tickers_data = feeder.get_all_tickers(inst_type=inst_type)

            return {
                "code": 0,
                "message": "success",
                "data": {
                    "tickers": tickers_data,
                    "total": len(tickers_data)
                }
            }

        else:
            raise HTTPException(status_code=400, detail=f"Unsupported exchange: {exchange}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get all tickers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orderbook/{symbol}")
async def get_orderbook(
    symbol: str,
    exchange: str = Query("okx", description="交易所"),
    depth: int = Query(20, description="深度")
) -> Dict:
    """
    获取订单簿深度

    Args:
        symbol: 交易对代码
        depth: 深度 (最大400)

    Returns:
        Dict: 订单簿数据
    """
    try:
        if exchange.lower() == "okx":
            from ginkgo.trading.feeders.okx_feeder import OKXMarketDataFeeder

            feeder = OKXMarketDataFeeder()
            orderbook = feeder.get_orderbook(symbol, depth=depth)

            if not orderbook:
                raise HTTPException(status_code=404, detail=f"Orderbook not found for {symbol}")

            return {
                "code": 0,
                "message": "success",
                "data": orderbook
            }

        else:
            raise HTTPException(status_code=400, detail=f"Unsupported exchange: {exchange}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get orderbook for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
