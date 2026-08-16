# Upstream: 前端行情页 MarketData.vue（market/pairs·tickers·ticker·orderbook·subscriptions）
# Downstream: OKXMarketDataFeeder（行情直查）, MarketSubscriptionService（订阅 CRUD）
# Role: 行情查询 + 用户行情订阅路由。业务失败一律 BusinessError(400)，
#       禁用 404——前端以 404 为"后端 market 模块缺失"哨兵（会停轮询断 WS）。

"""
Market Data API

- GET  /market/pairs               可交易对列表（OKX instruments）
- GET  /market/tickers             全量 ticker（5s 轮询）
- GET  /market/ticker/{symbol}     单标的 ticker
- GET  /market/orderbook/{symbol}  盘口
- GET  /market/subscriptions       当前用户订阅列表
- POST /market/subscriptions       创建订阅
- PUT  /market/subscriptions/{uuid} 更新订阅（数据类型/激活态）
- DELETE /market/subscriptions/{uuid} 删除订阅

行情查询不涉库，直查 OKXMarketDataFeeder（进程级单例，按 environment 分实例）；
订阅 CRUD 走 MarketSubscriptionService（API → Service → CRUD）。
"""

import threading
from typing import List, Literal, Optional

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from core.exceptions import BusinessError, NotFoundError
from core.logging import logger
from core.response import ok

router = APIRouter()

# ---------------------------------------------------------------------------
# 依赖获取
# ---------------------------------------------------------------------------

_OKX_FEEDERS: dict = {}
_FEEDER_LOCK = threading.Lock()


def get_okx_feeder(environment: str = "production"):
    """OKX 行情 feeder 按 environment 分的进程级单例（double-checked lock）。

    feeder 持 requests.Session 且失败不抛（返回 {}/[]）；单例不 close，
    生命周期 = 进程。get_instruments 带 lru_cache，新上市币进程内不刷新。
    """
    from ginkgo.trading.feeders.okx_feeder import OKXMarketDataFeeder

    feeder = _OKX_FEEDERS.get(environment)
    if feeder is None:
        with _FEEDER_LOCK:
            feeder = _OKX_FEEDERS.get(environment)
            if feeder is None:
                feeder = OKXMarketDataFeeder(environment=environment)
                _OKX_FEEDERS[environment] = feeder
    return feeder


def get_market_subscription_service():
    """获取 MarketSubscriptionService 实例"""
    from ginkgo.data.containers import container

    return container.market_subscription_service()


def _get_user_id(request: Request) -> str:
    """从 request.state 获取 user_uuid（auth 中间件注入字段，同 accounts.py）"""
    user_uuid = getattr(request.state, "user_uuid", None)
    if not user_uuid:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user_uuid


# ---------------------------------------------------------------------------
# 请求模型
# ---------------------------------------------------------------------------

_DataType = Literal["ticker", "candlesticks", "trades", "orderbook"]


class CreateSubscriptionRequest(BaseModel):
    exchange: Literal["okx", "binance"]
    symbol: str = Field(..., min_length=1, max_length=50)
    data_types: Optional[List[_DataType]] = None
    # API 层默认 production（页面行情源是 production）；
    # CRUD 自身默认 testnet 不动，不影响既有调用方
    environment: Literal["production", "testnet"] = "production"


class UpdateSubscriptionRequest(BaseModel):
    data_types: Optional[List[_DataType]] = None
    is_active: Optional[bool] = None


# ---------------------------------------------------------------------------
# 行情查询（不涉库）
# ---------------------------------------------------------------------------


def _f(v) -> float:
    """OKX 数值均为字符串；解析失败回 0.0（页面过滤非数字显示 '-'）"""
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _map_ticker(t: dict) -> dict:
    """feeder snake_case 字符串 ticker → 页面终形（float + price/ts 别名）"""
    return {
        "symbol": t.get("symbol", ""),
        "price": _f(t.get("last_price")),
        "last_price": _f(t.get("last_price")),
        "bid_price": _f(t.get("bid_price")),
        "ask_price": _f(t.get("ask_price")),
        "open_24h": _f(t.get("open_24h")),
        "high_24h": _f(t.get("high_24h")),
        "low_24h": _f(t.get("low_24h")),
        "volume_24h": _f(t.get("volume_24h")),
        "volume_ccy_24h": _f(t.get("volume_ccy_24h")),
        "ts": t.get("timestamp", ""),
        "timestamp": t.get("timestamp", ""),
    }


@router.get("/pairs")
async def get_trading_pairs(
    exchange: str = Query("okx", description="交易所（当前仅 okx）"),
    environment: str = Query("production", description="production | testnet"),
    quote_ccy: Optional[str] = Query(None, description="计价货币过滤（如 USDT）"),
    search: Optional[str] = Query(None, description="symbol 子串过滤"),
):
    """获取可交易对列表（OKX SPOT instruments → snake_case）"""
    try:
        if exchange != "okx":
            raise BusinessError(f"Unsupported exchange: {exchange}")

        instruments = get_okx_feeder(environment).get_instruments(inst_type="SPOT")
        if not instruments:
            raise BusinessError("Failed to fetch trading pairs from OKX")

        pairs = []
        for inst in instruments:
            symbol = inst.get("instId", "")
            if inst.get("state") != "live":
                continue
            if quote_ccy and not symbol.endswith(f"-{quote_ccy.upper()}"):
                continue
            if search and search.upper() not in symbol.upper():
                continue
            pairs.append({
                "symbol": symbol,
                "base_currency": inst.get("baseCcy", ""),
                "quote_currency": inst.get("quoteCcy", ""),
                "state": inst.get("state", ""),
                "list_time": str(inst.get("listTime", "")),
                "tick_size": inst.get("tickSz", ""),
                "lot_size": inst.get("lotSz", ""),
                "min_size": inst.get("minSz", ""),
            })

        return ok(
            data={"pairs": pairs, "total": len(pairs), "exchange": exchange, "environment": environment},
            message=f"Found {len(pairs)} trading pairs",
        )
    except BusinessError:
        raise
    except Exception as e:
        logger.error(f"Error getting trading pairs: {e}")
        raise BusinessError(f"Error getting trading pairs: {e}")


@router.get("/tickers")
async def get_all_tickers(
    exchange: str = Query("okx", description="交易所（当前仅 okx）"),
    environment: str = Query("production", description="production | testnet"),
    inst_type: str = Query("SPOT", description="产品类型"),
):
    """获取全量 ticker（symbol → ticker 映射，前端 5s 轮询）"""
    try:
        if exchange != "okx":
            raise BusinessError(f"Unsupported exchange: {exchange}")

        raw = get_okx_feeder(environment).get_all_tickers(inst_type=inst_type)
        if not raw:
            raise BusinessError("Failed to fetch tickers from OKX")

        tickers = {symbol: _map_ticker(t) for symbol, t in raw.items()}
        return ok(
            data={"tickers": tickers, "total": len(tickers)},
            message=f"Found {len(tickers)} tickers",
        )
    except BusinessError:
        raise
    except Exception as e:
        logger.error(f"Error getting tickers: {e}")
        raise BusinessError(f"Error getting tickers: {e}")


@router.get("/ticker/{symbol}")
async def get_ticker(
    symbol: str,
    exchange: str = Query("okx", description="交易所（当前仅 okx）"),
    environment: str = Query("production", description="production | testnet"),
):
    """获取单标的 ticker。不可得 → BusinessError（不用 404，避免触发前端降级哨兵）"""
    try:
        if exchange != "okx":
            raise BusinessError(f"Unsupported exchange: {exchange}")

        raw = get_okx_feeder(environment).get_ticker(symbol)
        if not raw:
            raise BusinessError(f"Ticker not available: {symbol}")

        return ok(data=_map_ticker(raw), message=f"Ticker for {symbol}")
    except BusinessError:
        raise
    except Exception as e:
        logger.error(f"Error getting ticker {symbol}: {e}")
        raise BusinessError(f"Error getting ticker: {e}")


@router.get("/orderbook/{symbol}")
async def get_orderbook(
    symbol: str,
    exchange: str = Query("okx", description="交易所（当前仅 okx）"),
    depth: int = Query(20, ge=1, le=400, description="档位深度"),
):
    """获取盘口（OKX 条目 [price, size, ...] 截取前两列）"""
    try:
        if exchange != "okx":
            raise BusinessError(f"Unsupported exchange: {exchange}")

        raw = get_okx_feeder("production").get_orderbook(symbol, depth)
        if not raw:
            raise BusinessError(f"Orderbook not available: {symbol}")

        bids = [level[:2] for level in raw.get("bids", [])]
        asks = [level[:2] for level in raw.get("asks", [])]
        return ok(
            data={"symbol": symbol, "bids": bids, "asks": asks, "timestamp": str(raw.get("ts", ""))},
            message=f"Orderbook for {symbol}",
        )
    except BusinessError:
        raise
    except Exception as e:
        logger.error(f"Error getting orderbook {symbol}: {e}")
        raise BusinessError(f"Error getting orderbook: {e}")


# ---------------------------------------------------------------------------
# 用户订阅（走 Service）
# ---------------------------------------------------------------------------


@router.get("/subscriptions")
async def list_subscriptions(
    request: Request,
    exchange: Optional[str] = Query(None, description="过滤交易所"),
    environment: Optional[str] = Query(None, description="过滤环境"),
    active_only: bool = Query(True, description="仅激活订阅"),
):
    """获取当前用户行情订阅列表"""
    try:
        user_id = _get_user_id(request)
        service = get_market_subscription_service()
        result = service.list_subscriptions(
            user_id=user_id,
            exchange=exchange,
            environment=environment,
            active_only=active_only,
        )
        if not result.is_success():
            raise BusinessError(result.error or "Failed to list subscriptions")
        return ok(data=result.data, message="Subscriptions retrieved successfully")
    except BusinessError:
        raise
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing subscriptions: {e}")
        raise BusinessError(f"Error listing subscriptions: {e}")


@router.post("/subscriptions", status_code=status.HTTP_201_CREATED)
async def create_subscription(data: CreateSubscriptionRequest, request: Request):
    """创建行情订阅（已存在时更新数据类型并激活）"""
    try:
        user_id = _get_user_id(request)
        service = get_market_subscription_service()
        result = service.create_subscription(
            user_id=user_id,
            exchange=data.exchange,
            symbol=data.symbol,
            data_types=data.data_types,
            environment=data.environment,
        )
        if not result.is_success():
            raise BusinessError(result.error or "Failed to create subscription")
        return ok(data=result.data, message="Subscription created successfully")
    except BusinessError:
        raise
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating subscription: {e}")
        raise BusinessError(f"Error creating subscription: {e}")


@router.put("/subscriptions/{uuid}")
async def update_subscription(data: UpdateSubscriptionRequest, uuid: str, request: Request):
    """更新行情订阅（数据类型/激活态）"""
    try:
        user_id = _get_user_id(request)
        service = get_market_subscription_service()
        result = service.update_subscription(
            uuid=uuid,
            user_id=user_id,
            data_types=data.data_types,
            is_active=data.is_active,
        )
        if not result.is_success():
            error = result.error or "Failed to update subscription"
            if "not found" in error.lower():
                raise NotFoundError("Subscription", uuid)
            if "无权" in error:
                raise BusinessError(error, code=403)
            raise BusinessError(error)
        return ok(data=result.data, message="Subscription updated successfully")
    except (NotFoundError, BusinessError):
        raise
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating subscription {uuid}: {e}")
        raise BusinessError(f"Error updating subscription: {e}")


@router.delete("/subscriptions/{uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subscription(uuid: str, request: Request):
    """删除行情订阅（软删除，204 空 body）"""
    try:
        user_id = _get_user_id(request)
        service = get_market_subscription_service()
        result = service.delete_subscription(uuid=uuid, user_id=user_id)
        if not result.is_success():
            error = result.error or "Failed to delete subscription"
            if "not found" in error.lower():
                raise NotFoundError("Subscription", uuid)
            if "无权" in error:
                raise BusinessError(error, code=403)
            raise BusinessError(error)
        return None
    except (NotFoundError, BusinessError):
        raise
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting subscription {uuid}: {e}")
        raise BusinessError(f"Error deleting subscription: {e}")
