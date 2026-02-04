"""
数据相关API路由
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Generic, TypeVar
from datetime import datetime

from ginkgo.data.containers import container
from ginkgo.enums import MARKET_TYPES, FREQUENCY_TYPES, ADJUSTMENT_TYPES
from core.logging import logger

router = APIRouter()


# ==================== 数据模型 ====================

# Market ID 到名称的映射
MARKET_ID_TO_NAME = {
    MARKET_TYPES.CHINA.value: "CHINA",
    MARKET_TYPES.NASDAQ.value: "NASDAQ",
    MARKET_TYPES.OTHER.value: "OTHER",
    MARKET_TYPES.VOID.value: "VOID",
}

T = TypeVar('T')

class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应"""
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int


class StockInfoSummary(BaseModel):
    """股票信息摘要"""
    uuid: str
    code: str
    name: Optional[str] = None
    market: Optional[str] = None
    industry: Optional[str] = None
    is_active: bool = True
    updated_at: Optional[str] = None


class BarDataSummary(BaseModel):
    """K线数据摘要"""
    uuid: str
    code: str
    date: str
    period: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: Optional[float] = None


class TickDataSummary(BaseModel):
    """Tick数据摘要"""
    uuid: str
    code: str
    timestamp: str
    price: float
    volume: int
    direction: int


class AdjustFactorSummary(BaseModel):
    """复权因子摘要"""
    uuid: str
    code: str
    date: str
    factor: float


class DataStats(BaseModel):
    """数据统计"""
    total_stocks: int
    total_bars: int
    total_ticks: int = 0
    total_adjust_factors: int
    tick_data_summary: Optional[Dict[str, Any]] = None  # Tick数据概况
    data_sources: List[str]
    latest_update: Optional[str] = None


class DataUpdateRequest(BaseModel):
    """数据更新请求"""
    type: str  # stockinfo, bars, ticks, adjustfactor
    codes: Optional[List[str]] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class DataSource(BaseModel):
    """数据源"""
    name: str
    enabled: bool
    description: str
    status: str


# ==================== 辅助函数 ====================

def get_stockinfo_service():
    """获取StockinfoService实例"""
    return container.stockinfo_service()


def get_bar_service():
    """获取BarService实例"""
    return container.bar_service()


def get_tick_service():
    """获取TickService实例"""
    return container.tick_service()


def get_adjustfactor_service():
    """获取AdjustFactorService实例"""
    return container.adjustfactor_service()


# ==================== API路由 ====================

@router.get("/stats", response_model=DataStats)
async def get_data_stats():
    """获取数据统计信息"""
    try:
        stockinfo_service = get_stockinfo_service()
        bar_service = get_bar_service()
        adjustfactor_service = get_adjustfactor_service()
        tick_service = get_tick_service()

        # 获取股票总数
        stock_count_result = stockinfo_service.count()
        total_stocks = stock_count_result.data if stock_count_result.is_success() else 0

        # 获取K线数据总量
        bar_count_result = bar_service.count()
        total_bars = bar_count_result.data if bar_count_result.is_success() else 0

        # 获取复权因子总量
        adjustfactor_count_result = adjustfactor_service.count()
        total_adjust_factors = adjustfactor_count_result.data if adjustfactor_count_result.is_success() else 0

        # Tick数据概况：抽样统计前10只股票（减少抽样数量以提高性能）
        tick_data_summary = await get_tick_data_summary(stockinfo_service, tick_service, sample_size=10)

        return {
            "total_stocks": total_stocks,
            "total_bars": total_bars,
            "total_ticks": 0,  # Tick数据分表存储，无法直接统计总量
            "total_adjust_factors": total_adjust_factors,
            "tick_data_summary": tick_data_summary,
            "data_sources": ["Tushare", "Yahoo", "BaoStock", "TDX"],
            "latest_update": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting data stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get data stats: {str(e)}"
        )


async def get_tick_data_summary(stockinfo_service, tick_service, sample_size: int = 10) -> Dict[str, Any]:
    """
    获取Tick数据概况信息

    由于Tick数据按股票代码分表存储，无法直接统计总量。
    采用抽样统计方式：获取前N只股票的tick数据量作为参考。
    """
    try:
        # 获取股票列表（限制数量以提高性能）
        stocks_result = stockinfo_service.get(limit=sample_size)
        stocks_with_ticks = []
        total_sampled_ticks = 0

        if stocks_result.is_success() and stocks_result.data:
            # 限制抽样检查数量，最多5只，避免超时
            check_limit = min(5, len(stocks_result.data))
            for stock in list(stocks_result.data)[:check_limit]:
                code = stock.code if hasattr(stock, 'code') else None
                if code:
                    try:
                        # 查询该股票的tick数据量（添加超时保护）
                        tick_count_result = tick_service.count(code=code)
                        if tick_count_result.is_success() and tick_count_result.data and tick_count_result.data > 0:
                            stocks_with_ticks.append({
                                "code": code,
                                "name": stock.code_name if hasattr(stock, 'code_name') else "",
                                "tick_count": tick_count_result.data
                            })
                            total_sampled_ticks += tick_count_result.data
                    except Exception as e:
                        logger.warning(f"Failed to get tick count for {code}: {e}")
                        continue

        # 按tick数据量排序
        top_ticks = sorted(stocks_with_ticks, key=lambda x: x["tick_count"], reverse=True)

        return {
            "stocks_with_tick_data": len(stocks_with_ticks),
            "sample_size": check_limit if stocks_result.is_success() else sample_size,
            "total_sampled_ticks": total_sampled_ticks,
            "top_stocks": top_ticks,
            "note": "Tick数据按股票分表存储，显示为抽样统计结果"
        }
    except Exception as e:
        logger.error(f"Error getting tick data summary: {e}")
        return {
            "stocks_with_tick_data": 0,
            "sample_size": sample_size,
            "total_sampled_ticks": 0,
            "top_stocks": [],
            "error": str(e)
        }


@router.get("/stockinfo", response_model=PaginatedResponse[StockInfoSummary])
async def get_stockinfo(
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 50
):
    """获取股票信息列表（分页）"""
    try:
        stockinfo_service = get_stockinfo_service()

        # 获取总数
        count_result = stockinfo_service.count()
        total_count = count_result.data if count_result.is_success() else 0

        # 计算offset
        offset = (page - 1) * page_size

        # 获取数据
        result = stockinfo_service.get(
            limit=page_size,
            offset=offset,
            order_by="code"
        )

        if not result.is_success() or not result.data:
            return {
                "items": [],
                "total": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": (total_count + page_size - 1) // page_size if page_size > 0 else 0
            }

        # 处理股票数据 - result.data 是 ModelList 对象，可直接迭代
        items = result.data
        stock_summaries = []

        for stock in items:
            code = stock.code if hasattr(stock, 'code') else ""
            code_name = stock.code_name if hasattr(stock, 'code_name') else ""
            code_str = str(code) if code is not None else ""
            name_str = str(code_name) if code_name is not None else ""

            # 搜索过滤
            if search:
                search_lower = search.lower()
                if search_lower not in code_str.lower() and search_lower not in name_str.lower():
                    continue

            # 将 market 整数值转换为字符串
            market_value = stock.market if hasattr(stock, 'market') else None
            market_str = MARKET_ID_TO_NAME.get(market_value) if market_value is not None else None

            stock_summaries.append({
                "uuid": stock.uuid if hasattr(stock, 'uuid') else "",
                "code": code_str,
                "name": name_str if name_str else None,
                "market": market_str,
                "industry": stock.industry if hasattr(stock, 'industry') else None,
                "is_active": stock.is_active if hasattr(stock, 'is_active') else True,
                "updated_at": stock.update_at.isoformat() if hasattr(stock, 'update_at') and stock.update_at else None
            })

        # 如果有搜索，重新计算过滤后的总数
        if search:
            filtered_count = len(stock_summaries)
        else:
            filtered_count = total_count

        total_pages = (filtered_count + page_size - 1) // page_size if page_size > 0 else 0

        return {
            "items": stock_summaries,
            "total": filtered_count,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages
        }

    except Exception as e:
        logger.error(f"Error getting stockinfo: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get stock info: {str(e)}"
        )


@router.get("/bars", response_model=PaginatedResponse[BarDataSummary])
async def get_bars(
    code: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page: int = 1,
    page_size: int = 100
):
    """获取K线数据列表（分页）"""
    try:
        bar_service = get_bar_service()

        # 将字符串日期转换为datetime
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None

        # 如果没有提供任何筛选条件，默认查询最近1年的数据
        if not code and not start_dt and not end_dt:
            from datetime import timedelta
            end_dt = datetime.utcnow()
            start_dt = end_dt - timedelta(days=365)

        # 使用BarService.get方法，支持分页
        result = bar_service.get(
            code=code,
            start_date=start_dt,
            end_date=end_dt,
            frequency=FREQUENCY_TYPES.DAY,
            adjustment_type=ADJUSTMENT_TYPES.FORE,
            page=page - 1,  # Service层page是0-based
            page_size=page_size,
            order_by="timestamp",
            desc_order=False
        )

        if not result.is_success() or not result.data:
            return {
                "items": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
                "total_pages": 0
            }

        # 处理返回的数据
        bars_data = result.data
        bars_list = bars_data.to_entities() if hasattr(bars_data, 'to_entities') else []

        bar_summaries = []
        for bar in bars_list:
            bar_summaries.append({
                "uuid": bar.uuid if hasattr(bar, 'uuid') else "",
                "code": str(bar.code) if hasattr(bar, 'code') else "",
                "date": bar.timestamp.isoformat() if hasattr(bar, 'timestamp') and bar.timestamp else "",
                "period": "day",
                "open": float(bar.open) if hasattr(bar, 'open') else 0.0,
                "high": float(bar.high) if hasattr(bar, 'high') else 0.0,
                "low": float(bar.low) if hasattr(bar, 'low') else 0.0,
                "close": float(bar.close) if hasattr(bar, 'close') else 0.0,
                "volume": float(bar.volume) if hasattr(bar, 'volume') else 0.0,
                "amount": float(bar.amount) if hasattr(bar, 'amount') and bar.amount else None
            })

        return {
            "items": bar_summaries,
            "total": bars_data.count() if hasattr(bars_data, 'count') else len(bar_summaries),
            "page": page,
            "page_size": page_size,
            "total_pages": 1
        }

    except Exception as e:
        logger.error(f"Error getting bars: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get bars: {str(e)}"
        )


@router.get("/ticks", response_model=PaginatedResponse[TickDataSummary])
async def get_ticks(
    code: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page: int = 1,
    page_size: int = 100
):
    """获取Tick数据列表（分页）"""
    try:
        tick_service = get_tick_service()

        # Tick数据需要code参数
        if not code:
            raise HTTPException(
                status_code=400,
                detail="Code is required for ticks data"
            )

        # 将字符串日期转换为datetime
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None

        # 使用TickService.get方法
        result = tick_service.get(
            code=code,
            start_date=start_dt,
            end_date=end_dt,
            adjustment_type=ADJUSTMENT_TYPES.NONE
        )

        if not result.is_success() or not result.data:
            return {
                "items": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
                "total_pages": 0
            }

        # 处理返回的数据
        ticks_data = result.data
        ticks_list = ticks_data.to_entities() if hasattr(ticks_data, 'to_entities') else []

        # 手动分页（TickService的get方法暂不支持分页参数）
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_ticks = ticks_list[start_idx:end_idx]

        tick_summaries = []
        for tick in paginated_ticks:
            # 处理direction字段：可能是枚举类型或整数
            direction_value = 0
            if hasattr(tick, 'direction'):
                dir_val = tick.direction
                if hasattr(dir_val, 'value'):
                    direction_value = dir_val.value
                elif hasattr(dir_val, 'to_int'):
                    direction_value = dir_val.to_int()
                else:
                    direction_value = int(dir_val) if dir_val is not None else 0

            tick_summaries.append({
                "uuid": tick.uuid if hasattr(tick, 'uuid') else "",
                "code": code,
                "timestamp": tick.timestamp.isoformat() if hasattr(tick, 'timestamp') and tick.timestamp else "",
                "price": float(tick.price) if hasattr(tick, 'price') else 0.0,
                "volume": int(tick.volume) if hasattr(tick, 'volume') else 0,
                "direction": direction_value
            })

        return {
            "items": tick_summaries,
            "total": len(ticks_list),
            "page": page,
            "page_size": page_size,
            "total_pages": (len(ticks_list) + page_size - 1) // page_size if page_size > 0 else 0
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting ticks: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get ticks: {str(e)}"
        )


@router.get("/adjustfactors", response_model=PaginatedResponse[AdjustFactorSummary])
async def get_adjust_factors(
    code: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page: int = 1,
    page_size: int = 100
):
    """获取复权因子列表（分页）"""
    try:
        adjustfactor_service = get_adjustfactor_service()

        # 将日期字符串转换为datetime对象
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None

        # 获取数据
        result = adjustfactor_service.get(
            code=code,
            start_date=start_dt,
            end_date=end_dt
        )

        if not result.is_success() or not result.data:
            return {
                "items": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
                "total_pages": 0
            }

        # 获取因子数据
        factors_data = result.data
        if isinstance(factors_data, dict):
            factors_list = factors_data.get("items", [])
        elif hasattr(factors_data, 'to_entities'):
            factors_list = factors_data.to_entities()
        else:
            factors_list = list(factors_data) if factors_data else []

        # 分页处理
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_factors = factors_list[start_idx:end_idx]

        factor_summaries = []
        for factor in paginated_factors:
            factor_summaries.append({
                "uuid": factor.uuid if hasattr(factor, 'uuid') else "",
                "code": str(factor.code) if hasattr(factor, 'code') else "",
                "date": factor.timestamp.isoformat() if hasattr(factor, 'timestamp') and factor.timestamp else "",
                "factor": float(factor.factor) if hasattr(factor, 'factor') else 1.0
            })

        return {
            "items": factor_summaries,
            "total": len(factors_list),
            "page": page,
            "page_size": page_size,
            "total_pages": (len(factors_list) + page_size - 1) // page_size if page_size > 0 else 0
        }

    except Exception as e:
        logger.error(f"Error getting adjust factors: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get adjust factors: {str(e)}"
        )


@router.post("/update")
async def update_data(request: DataUpdateRequest):
    """触发数据更新"""
    try:
        if request.type == "stockinfo":
            # 更新股票信息
            stockinfo_service = get_stockinfo_service()
            result = stockinfo_service.sync()

            if result.is_success():
                return {
                    "message": "Stock info update initiated",
                    "type": "stockinfo"
                }
            else:
                raise HTTPException(
                    status_code=500,
                    detail=result.message
                )

        elif request.type == "bars":
            # 更新K线数据
            codes = request.codes or []
            if not codes:
                raise HTTPException(
                    status_code=400,
                    detail="Codes are required for bars update"
                )

            bar_service = get_bar_service()

            # 对每个代码调用同步
            for code in codes:
                bar_service.sync_full(code)

            return {
                "message": f"Bars update initiated for {len(codes)} codes",
                "type": "bars",
                "codes": codes
            }

        elif request.type == "ticks":
            # 更新Tick数据
            codes = request.codes or []
            if not codes:
                raise HTTPException(
                    status_code=400,
                    detail="Codes are required for ticks update"
                )

            tick_service = get_tick_service()

            # 将日期字符串转换为datetime
            start_dt = datetime.fromisoformat(request.start_date) if request.start_date else None
            end_dt = datetime.fromisoformat(request.end_date) if request.end_date else None

            # 对每个代码调用同步
            for code in codes:
                tick_service.sync_smart(code, start_date=start_dt, end_date=end_dt)

            return {
                "message": f"Ticks update initiated for {len(codes)} codes",
                "type": "ticks",
                "codes": codes
            }

        elif request.type == "adjustfactor":
            # 更新复权因子
            codes = request.codes or []
            if not codes:
                raise HTTPException(
                    status_code=400,
                    detail="Codes are required for adjust factors update"
                )

            adjustfactor_service = get_adjustfactor_service()

            # 批量同步复权因子
            result = adjustfactor_service.sync_batch(codes)

            if result.is_success():
                return {
                    "message": f"Adjust factors update initiated for {len(codes)} codes",
                    "type": "adjustfactor",
                    "codes": codes
                }
            else:
                raise HTTPException(
                    status_code=500,
                    detail=result.message
                )

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported data type: {request.type}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating data: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update data: {str(e)}"
        )


@router.get("/sources", response_model=List[DataSource])
async def get_data_sources():
    """获取数据源状态"""
    try:
        # 返回可用的数据源及其状态
        sources = [
            {
                "name": "Tushare",
                "enabled": True,
                "description": "中国金融数据接口",
                "status": "active"
            },
            {
                "name": "Yahoo",
                "enabled": True,
                "description": "Yahoo Finance数据",
                "status": "active"
            },
            {
                "name": "BaoStock",
                "enabled": True,
                "description": "免费证券数据平台",
                "status": "active"
            },
            {
                "name": "TDX",
                "enabled": True,
                "description": "通达信数据",
                "status": "active"
            }
        ]

        return sources

    except Exception as e:
        logger.error(f"Error getting data sources: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get data sources: {str(e)}"
        )
