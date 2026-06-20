"""
Signal Execution Report API (#6150 半手动实盘核心).

用户收到交易信号通知 → 手动执行 → 通过本端点回报实际成交价/量。
端点职责仅限：翻译请求 → 调 signal_tracking_service.set_confirmed → 翻译响应
（API→Service 单向，端点零业务逻辑）。actual_* 写入与时间偏差由 service 层完成。
"""
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

# 添加 Ginkgo 源码路径（与 api/api/trading.py 一致）
ginkgo_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(ginkgo_path))

from core.response import ok
from ginkgo.libs import GLOG

router = APIRouter()


class SignalExecutionReport(BaseModel):
    """用户手动执行后的实际成交回报。"""

    actual_price: float = Field(..., description="实际成交价")
    actual_volume: int = Field(..., description="实际成交量")
    execution_timestamp: Optional[datetime] = Field(
        None, description="实际成交时间（业务时间），缺省由 service 用信号业务时间"
    )


def _get_signal_tracking_service():
    """获取 SignalTrackingService 实例（DI 工厂，便于测试注入）。"""
    from ginkgo.data.containers import container
    return container.signal_tracking_service()


def _compute_deviation(tracker) -> dict:
    """计算预期 − 实际的偏差（#6150 "轻" 对账替代，不回写仓位）。

    set_confirmed 已写入时间偏差(time_delay_seconds)；这里补价格/数量偏差，
    供用户对照排查。预期值缺失时返回 None，不抛异常（信号可能未带预期价/量）。
    """
    expected_price = getattr(tracker, "expected_price", None)
    actual_price = getattr(tracker, "actual_price", None)
    expected_volume = getattr(tracker, "expected_volume", None)
    actual_volume = getattr(tracker, "actual_volume", None)

    price_deviation = None
    if expected_price is not None and actual_price is not None:
        price_deviation = float(expected_price) - float(actual_price)

    volume_deviation = None
    if expected_volume is not None and actual_volume is not None:
        volume_deviation = int(expected_volume) - int(actual_volume)

    return {
        "price_deviation": price_deviation,
        "volume_deviation": volume_deviation,
    }


@router.post("/{signal_id}/report")
def report_signal_execution(
    signal_id: str,
    report: SignalExecutionReport,
    service=Depends(_get_signal_tracking_service),
):
    """回报信号的实际执行结果，触发 actual_* 写入与时间偏差计算。"""
    result = service.set_confirmed(
        signal_id=signal_id,
        actual_price=report.actual_price,
        actual_volume=report.actual_volume,
        execution_timestamp=report.execution_timestamp,
    )

    if not result.is_success():
        # 未找到 tracker / 已确认过 → 404（首版不细分 409）
        raise HTTPException(status_code=404, detail=result.error)

    tracker = result.data
    deviation = _compute_deviation(tracker)
    code = getattr(tracker, "expected_code", None) or signal_id
    # 偏差只记录不回写：半手动实盘由用户决定是否追单
    if deviation["price_deviation"] is not None or deviation["volume_deviation"] is not None:
        GLOG.INFO(
            f"Signal {code} execution deviation: "
            f"price={deviation['price_deviation']}, volume={deviation['volume_deviation']}"
        )

    return ok(
        data={
            "signal_id": signal_id,
            "tracking_status": getattr(tracker, "tracking_status", None),
            "deviation": deviation,
        },
        message="execution reported",
    )
