"""
数据相关API路由
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, model_validator
from typing import List, Optional, Dict, Any
from datetime import datetime
import time as _time

from ginkgo.data.containers import container
from ginkgo.enums import MARKET_TYPES, FREQUENCY_TYPES, ADJUSTMENT_TYPES
from core.logging import logger
from core.response import ok, paginated

router = APIRouter()


# ==================== 数据模型 ====================

# Market ID 到名称的映射
MARKET_ID_TO_NAME = {
    MARKET_TYPES.CHINA.value: "CHINA",
    MARKET_TYPES.NASDAQ.value: "NASDAQ",
    MARKET_TYPES.OTHER.value: "OTHER",
    MARKET_TYPES.VOID.value: "VOID",
}


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
    timestamp: str
    foreadjustfactor: float
    backadjustfactor: float
    adjustfactor: float


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
    """数据更新请求

    #5784: 同时接受单数 code (str) 与复数 codes (list)。
    单数 code 归一化为 codes=[code]，三种 sync 分支统一消费 codes。
    """
    type: str  # stockinfo, bars, ticks, adjustfactor
    code: Optional[str] = None
    codes: Optional[List[str]] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None

    @model_validator(mode="after")
    def _normalize_code_to_codes(self) -> "DataUpdateRequest":
        """单数 code 归一化进 codes（仅当 codes 未提供时填充，不覆盖显式传入的 codes）"""
        if self.code and not self.codes:
            self.codes = [self.code]
        return self


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


def get_sync_record_service():
    """获取DataSyncRecordService实例"""
    return container.data_sync_record_service()


# ==================== API路由 ====================

@router.get("/stats")
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

        return ok(data={
            "total_stocks": total_stocks,
            "total_bars": total_bars,
            "total_ticks": 0,  # Tick数据分表存储，无法直接统计总量
            "total_adjust_factors": total_adjust_factors,
            "tick_data_summary": tick_data_summary,
            "data_sources": ["Tushare", "Yahoo", "BaoStock", "TDX"],
            "latest_update": datetime.utcnow().isoformat()
        })

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


@router.get("/stockinfo")
async def get_stockinfo(
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = Query(default=50, ge=1, le=500)
):
    """获取股票信息列表（分页，搜索下推到DB层）"""
    try:
        stockinfo_service = get_stockinfo_service()

        if search:
            # 搜索：下推到 DB 层 OR 条件查询
            result = stockinfo_service.search(
                keyword=search,
                page=page - 1,
                page_size=page_size,
            )
            if not result.is_success() or not result.data:
                return paginated(items=[], total=0, page=page, page_size=page_size)

            result_data = result.data
            total_count = result_data.get("total", 0) if isinstance(result_data, dict) else 0
            items = result_data.get("data", []) if isinstance(result_data, dict) else []
        else:
            # 无搜索：标准分页查询
            count_result = stockinfo_service.count()
            total_count = count_result.data if count_result.is_success() else 0

            result = stockinfo_service.get(
                limit=page_size,
                offset=(page - 1) * page_size,
                order_by="code"
            )

            if not result.is_success() or not result.data:
                return paginated(items=[], total=total_count, page=page, page_size=page_size)

            items = result.data

        stock_summaries = []
        for stock in items:
            code = stock.code if hasattr(stock, 'code') else ""
            code_name = stock.code_name if hasattr(stock, 'code_name') else ""
            market_value = stock.market if hasattr(stock, 'market') else None
            is_del = stock.is_del if hasattr(stock, 'is_del') else False
            industry = stock.industry if hasattr(stock, 'industry') else None
            uuid_val = stock.uuid if hasattr(stock, 'uuid') else ""
            update_at = stock.update_at if hasattr(stock, 'update_at') else None

            code_str = str(code) if code is not None else ""
            name_str = str(code_name) if code_name is not None else ""
            market_str = MARKET_ID_TO_NAME.get(market_value) if market_value is not None else None

            stock_summaries.append({
                "uuid": uuid_val,
                "code": code_str,
                "name": name_str if name_str else None,
                "market": market_str,
                "industry": industry,
                "is_active": not is_del,
                "updated_at": update_at.isoformat() if update_at else None
            })

        return paginated(items=stock_summaries, total=total_count, page=page, page_size=page_size)

    except Exception as e:
        logger.error(f"Error getting stockinfo: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get stock info: {str(e)}"
        )


@router.get("/bars")
async def get_bars(
    code: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page: int = 1,
    page_size: int = Query(default=100, ge=1, le=500)
):
    """获取K线数据列表（分页）"""
    try:
        bar_service = get_bar_service()

        # 将字符串日期转换为datetime
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None

        # 未提供日期范围时，默认查询最近1年数据
        if not start_dt and not end_dt:
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
            desc_order=True
        )

        if not result.is_success() or not result.data:
            return paginated(items=[], total=0, page=page, page_size=page_size)

        # 处理返回的数据
        # bar_service.get() 返回裸 list[MBar]（无 to_entities）；
        # ModelList 容器走 to_entities()，裸 list 本身即 entities 列表
        bars_data = result.data
        bars_list = bars_data.to_entities() if hasattr(bars_data, 'to_entities') else bars_data

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

        return paginated(
            items=bar_summaries,
            # 裸 list 的 .count() 需要参数（#5599/#5610 500 根因）；
            # 直接用 len(bar_summaries)，total 与返回 items 数一致
            total=len(bar_summaries),
            page=page,
            page_size=page_size
        )

    except Exception as e:
        logger.error(f"Error getting bars: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get bars: {str(e)}"
        )


@router.get("/ticks")
async def get_ticks(
    code: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page: int = 1,
    page_size: int = Query(default=100, ge=1, le=500)
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

        # 使用TickService.get方法（支持分页）
        result = tick_service.get(
            code=code,
            start_date=start_dt,
            end_date=end_dt,
            adjustment_type=ADJUSTMENT_TYPES.NONE,
            page=page - 1,
            page_size=page_size,
        )

        if not result.is_success() or not result.data:
            return paginated(items=[], total=0, page=page, page_size=page_size)

        # 处理返回的数据（已是分页后的结果）
        result_data = result.data
        total_count = 0
        if isinstance(result_data, dict):
            total_count = result_data.get("total", 0) or 0
            ticks_data = result_data.get("data", [])
        else:
            ticks_data = result_data

        ticks_list = ticks_data.to_entities() if hasattr(ticks_data, 'to_entities') else []

        tick_summaries = []
        for tick in ticks_list:
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

        return paginated(
            items=tick_summaries,
            total=total_count,
            page=page,
            page_size=page_size
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting ticks: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get ticks: {str(e)}"
        )


@router.get("/adjustfactors")
async def get_adjust_factors(
    code: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page: int = 1,
    page_size: int = Query(default=100, ge=1, le=500)
):
    """获取复权因子列表（分页）"""
    try:
        adjustfactor_service = get_adjustfactor_service()

        # 将日期字符串转换为datetime对象
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None

        # 获取数据（支持服务端分页）
        result = adjustfactor_service.get(
            code=code,
            start_date=start_dt,
            end_date=end_dt,
            page=page - 1,
            page_size=page_size,
        )

        if not result.is_success() or not result.data:
            return paginated(items=[], total=0, page=page, page_size=page_size)

        # 获取因子数据（已是分页后的结果）
        result_data = result.data
        total_count = 0
        if isinstance(result_data, dict):
            total_count = result_data.get("total", 0) or 0
            factors_data = result_data.get("data", [])
        else:
            factors_data = result_data

        if hasattr(factors_data, 'to_entities'):
            factors_list = factors_data.to_entities()
        else:
            factors_list = list(factors_data) if factors_data else []

        factor_summaries = []
        for factor in factors_list:
            factor_summaries.append({
                "uuid": factor.uuid if hasattr(factor, 'uuid') else "",
                "code": str(factor.code) if hasattr(factor, 'code') else "",
                "timestamp": factor.timestamp.isoformat() if hasattr(factor, 'timestamp') and factor.timestamp else "",
                "foreadjustfactor": float(factor.foreadjustfactor) if hasattr(factor, 'foreadjustfactor') else 1.0,
                "backadjustfactor": float(factor.backadjustfactor) if hasattr(factor, 'backadjustfactor') else 1.0,
                "adjustfactor": float(factor.adjustfactor) if hasattr(factor, 'adjustfactor') else 1.0,
            })

        return paginated(
            items=factor_summaries,
            total=total_count,
            page=page,
            page_size=page_size
        )

    except Exception as e:
        logger.error(f"Error getting adjust factors: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get adjust factors: {str(e)}"
        )


def _aggregate_dsr_list(dsrs):
    """聚合 List[DataSyncResult] 为单一 DataSyncResult（批量同步统计）

    adjustfactor_service.sync_batch 返回 data=List[DataSyncResult]，按各 DSR 的
    records_* 求和并合并 errors，复用 DataSyncResult.is_successful() 走统一四态决策，
    避免批量真实成功落入 else 被误降 partial，同时补齐 master 既有的统计丢失。
    """
    from ginkgo.libs.data.results.data_sync_result import DataSyncResult
    aggregated_errors = []
    for d in dsrs:
        aggregated_errors.extend(getattr(d, 'errors', None) or [])
    return DataSyncResult(
        entity_type="batch",
        entity_identifier=f"multiple({len(dsrs)})",
        sync_range=(None, None),
        records_processed=sum(getattr(d, 'records_processed', 0) for d in dsrs),
        records_added=sum(getattr(d, 'records_added', 0) for d in dsrs),
        records_updated=sum(getattr(d, 'records_updated', 0) for d in dsrs),
        records_skipped=sum(getattr(d, 'records_skipped', 0) for d in dsrs),
        records_failed=sum(getattr(d, 'records_failed', 0) for d in dsrs),
        sync_duration=0.0,
        is_idempotent=True,
        sync_strategy="batch",
        errors=aggregated_errors,
    )


def _record_sync_result(service, record_uuid: str, result, started_at: float):
    """从 ServiceResult/DataSyncResult 提取统计并更新同步记录"""
    duration_ms = int((_time.time() - started_at) * 1000)
    if result is None:
        service.record_fail(uuid=record_uuid, error_message="sync method returned None")
        return
    if hasattr(result, 'is_success') and result.is_success() and result.data:
        dsr = result.data
        # #6217: sync_batch 返回 List[DataSyncResult]（adjustfactor 批量），聚合为
        # 单一统计视图后走统一四态决策，避免 list 落入 else 被误降 partial。
        if isinstance(dsr, list):
            dsr = _aggregate_dsr_list(dsr)
        if hasattr(dsr, 'records_processed'):
            # #5893: success 仅当无错误且有产出（processed>0）或幂等跳过（skipped>0）；
            # 否则报 partial——含"0 条可疑空"和"有 records_failed/errors"。
            # DataSyncResult.is_successful() 只判 has_errors 不看 processed=0，故需此处显式区分。
            has_meaningful_output = dsr.records_processed > 0 or dsr.records_skipped > 0
            status = "success" if (dsr.is_successful() and has_meaningful_output) else "partial"
            service.record_complete(
                uuid=record_uuid,
                status=status,
                duration_ms=duration_ms,
                records_processed=dsr.records_processed,
                records_added=dsr.records_added,
                records_updated=dsr.records_updated,
                records_failed=dsr.records_failed,
                sync_strategy=getattr(dsr, 'sync_strategy', ''),
            )
        else:
            # #5893: 成功但无 records_processed 统计，无法判断产出，报 partial
            service.record_complete(uuid=record_uuid, status="partial", duration_ms=duration_ms)
    elif hasattr(result, 'is_success') and not result.is_success():
        service.record_fail(uuid=record_uuid, error_message=getattr(result, 'message', 'Unknown error'))
    else:
        # #5893: result 无 is_success 方法，无法判断成败，报 partial
        service.record_complete(uuid=record_uuid, status="partial", duration_ms=duration_ms)


@router.post("/sync")
async def sync_data(request: DataUpdateRequest):
    """触发数据同步"""
    sync_svc = get_sync_record_service()

    try:
        if request.type == "stockinfo":
            # 更新股票信息
            rec = sync_svc.record_start(sync_type="stockinfo", code="ALL")
            started_at = _time.time()
            try:
                stockinfo_service = get_stockinfo_service()
                result = stockinfo_service.sync()
                if rec.is_success():
                    _record_sync_result(sync_svc, rec.data["uuid"], result, started_at)

                if not result.is_success():
                    raise HTTPException(status_code=500, detail=result.message)
                return ok(data={"type": "stockinfo"}, message="Stock info update completed")
            except Exception as e:
                if rec.is_success():
                    sync_svc.record_fail(uuid=rec.data["uuid"], error_message=str(e))
                raise

        elif request.type == "bars":
            codes = request.codes or []
            if not codes:
                raise HTTPException(status_code=400, detail="codes (list of stock codes) is required for bars update")

            bar_service = get_bar_service()
            for code in codes:
                rec = sync_svc.record_start(sync_type="bars", code=code)
                started_at = _time.time()
                try:
                    result = bar_service.sync_smart(code)
                    if rec.is_success():
                        _record_sync_result(sync_svc, rec.data["uuid"], result, started_at)
                except Exception as e:
                    if rec.is_success():
                        sync_svc.record_fail(uuid=rec.data["uuid"], error_message=str(e))

            return ok(
                data={"type": "bars", "codes": codes},
                message=f"Bars update completed for {len(codes)} codes"
            )

        elif request.type == "ticks":
            codes = request.codes or []
            if not codes:
                raise HTTPException(status_code=400, detail="codes (list of stock codes) is required for ticks update")

            tick_service = get_tick_service()
            start_dt = datetime.fromisoformat(request.start_date) if request.start_date else None
            end_dt = datetime.fromisoformat(request.end_date) if request.end_date else None

            for code in codes:
                rec = sync_svc.record_start(sync_type="ticks", code=code)
                started_at = _time.time()
                try:
                    result = tick_service.sync_smart(code, start_date=start_dt, end_date=end_dt)
                    if rec.is_success():
                        _record_sync_result(sync_svc, rec.data["uuid"], result, started_at)
                except Exception as e:
                    if rec.is_success():
                        sync_svc.record_fail(uuid=rec.data["uuid"], error_message=str(e))

            return ok(
                data={"type": "ticks", "codes": codes},
                message=f"Ticks update completed for {len(codes)} codes"
            )

        elif request.type in ("adjustfactor", "adjustfactors"):
            # #5868: GET 端点用复数 /adjustfactors，sync type 接受单复数双别名，归一化为单数
            sync_type = "adjustfactor"
            codes = request.codes or []
            if not codes:
                raise HTTPException(status_code=400, detail="codes (list of stock codes) is required for adjust factors update")

            adjustfactor_service = get_adjustfactor_service()
            # 批量同步复权因子，整体记录
            rec = sync_svc.record_start(sync_type=sync_type, code=",".join(codes))
            started_at = _time.time()
            try:
                result = adjustfactor_service.sync_batch(codes)
                if rec.is_success():
                    _record_sync_result(sync_svc, rec.data["uuid"], result, started_at)
                if not result.is_success():
                    raise HTTPException(status_code=500, detail=result.message)
            except HTTPException:
                raise
            except Exception as e:
                if rec.is_success():
                    sync_svc.record_fail(uuid=rec.data["uuid"], error_message=str(e))
                raise

            # 同步成功后衔接 calculate（与 task_timer/worker 主力路径对齐）：
            # sync 只落原始 adjustfactor，fore/back 占位 1.0，需 calculate 推导覆盖。
            # 单 code 计算失败不阻断整体响应（原始因子已落库，可后续补算）。
            for code in codes:
                try:
                    calc_result = adjustfactor_service.calculate(code)
                    if not calc_result.is_success():
                        logger.warning(f"Adjustfactor calculate failed for {code}: {calc_result.message}")
                except Exception as e:
                    logger.warning(f"Adjustfactor calculate exception for {code}: {e}")

            return ok(
                data={"type": "adjustfactor", "codes": codes},
                message=f"Adjust factors update completed for {len(codes)} codes"
            )

        else:
            raise HTTPException(status_code=400, detail=f"Unsupported data type: {request.type}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update data: {str(e)}")


@router.get("/sync/history")
async def get_sync_history(
    sync_type: Optional[str] = None,
    page: int = 1,
    page_size: int = Query(default=20, ge=1, le=500),
):
    """获取同步历史记录"""
    try:
        sync_record_service = get_sync_record_service()
        result = sync_record_service.get_history(
            sync_type=sync_type,
            page=page - 1,
            page_size=page_size,
        )

        if not result.is_success() or not result.data:
            return paginated(items=[], total=0, page=page, page_size=page_size)

        items = result.data.get("items", [])
        total = result.data.get("total", 0)

        return paginated(items=items, total=total, page=page, page_size=page_size)
    except Exception as e:
        logger.error(f"Error getting sync history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get sync history: {str(e)}")


@router.get("/sources")
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

        return ok(data=sources)

    except Exception as e:
        logger.error(f"Error getting data sources: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get data sources: {str(e)}"
        )
