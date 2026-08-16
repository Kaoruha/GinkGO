# Upstream: 前端因子研究页（research/ic·layering·decay；前端模块零引用，契约按库语义定）
# Downstream: FactorAnalysisService.analyze_factor（现场计算，不入库）
# Role: 因子分析路由——IC/分层/衰减三视图，共用一次全量分析再裁剪响应。

"""
Factor Research API

- POST /research/ic        因子 IC 分析（IC/ICIR/多期 IC）
- POST /research/layering  因子分层回测（分组统计与多空 spread）
- POST /research/decay     因子衰减分析（半衰期/lag IC）

库内语义（factor_analysis_service.analyze_factor）：现场 pandas 计算，
不落库。请求以 factor_name + 日期区间 + entity_ids 表达，与
client/factor_cli.py 的装配方式一致（factor_crud/bar_service 取自容器）。
"""

from typing import List, Literal, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field, field_validator

from core.exceptions import BusinessError, ValidationError
from core.logging import logger
from core.response import ok

router = APIRouter()

MAX_ENTITIES = 50  # analyze_factor 是 sync pandas 循环，阻塞事件循环；上限缓解


class FactorAnalysisRequest(BaseModel):
    factor_name: str = Field(..., min_length=1, max_length=100, description="MFactor.factor_name")
    start_date: str = Field(..., description="开始日期 YYYY-MM-DD（含）")
    end_date: str = Field(..., description="结束日期 YYYY-MM-DD（含）")
    entity_ids: Optional[List[str]] = None
    codes: Optional[List[str]] = None  # 前端别名；与 entity_ids 合并去重
    entity_type: str = Field("stock", description="stock | futures | fund ...")
    n_groups: int = Field(5, ge=2, le=20, description="分层组数")
    periods: List[int] = Field(default_factory=lambda: [1, 5, 10, 20], description="持有期（交易日）")
    method: Literal["spearman", "pearson"] = Field("spearman", description="相关系数方法")
    max_lag: int = Field(20, ge=1, le=100, description="衰减最大滞后天数")

    @field_validator("start_date", "end_date")
    @classmethod
    def _valid_date(cls, v: str) -> str:
        from datetime import datetime

        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"日期须为 YYYY-MM-DD: {v}")
        return v

    @field_validator("codes", "entity_ids")
    @classmethod
    def _strip_and_drop_empty(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return None
        return [item.strip() for item in v if item and item.strip()]

    def merged_entity_ids(self) -> List[str]:
        ids = list(filter(None, [*(self.entity_ids or []), *(self.codes or [])]))
        return list(dict.fromkeys(ids))  # 保序去重


def _run_analysis(req: FactorAnalysisRequest) -> dict:
    """共用装配：容器取 factor_crud/bar_service → analyze_factor 合并报告。

    报告键（ServiceResult.data 真实输出）：
    ic / ir / ic_by_period / ir_by_period / decay / turnover /
    layering_spread / layering。analyze_factor 失败不抛（success=False +
    error），此处统一转 BusinessError。graceful skip 的段用 .get() 取
    None，不伪造前端契约里库内没有的字段。
    """
    from datetime import datetime

    from ginkgo.enums import ENTITY_TYPES
    from ginkgo.data.containers import container
    from ginkgo.features.services.factor_analysis_service import FactorAnalysisService

    if datetime.strptime(req.start_date, "%Y-%m-%d") > datetime.strptime(req.end_date, "%Y-%m-%d"):
        raise ValidationError(f"start_date 不能晚于 end_date: {req.start_date} > {req.end_date}")

    entity_ids = req.merged_entity_ids()
    if not entity_ids:
        raise ValidationError("entity_ids 与 codes 至少提供一个有效标的")
    if len(entity_ids) > MAX_ENTITIES:
        raise ValidationError(f"标的数超上限 {MAX_ENTITIES}（当前 {len(entity_ids)}）")

    try:
        entity_type = ENTITY_TYPES.enum_convert(req.entity_type)
    except Exception:
        raise ValidationError(f"Unknown entity_type: {req.entity_type}")

    service = FactorAnalysisService()
    report = service.analyze_factor(
        factor_name=req.factor_name,
        entity_ids=entity_ids,
        start_date=req.start_date,
        end_date=req.end_date,
        factor_crud=container.factor_crud(),
        bar_service=container.bar_service(),
        entity_type=entity_type,
        periods=tuple(req.periods),
        n_groups=req.n_groups,
        method=req.method,
        max_lag=req.max_lag,
    )
    if not report.success or not report.data:
        raise BusinessError(report.error or f"Factor analysis produced no result: {req.factor_name}")
    return report.data


@router.post("/ic")
async def analyze_ic(data: FactorAnalysisRequest):
    """因子 IC 分析：IC 均值 / ICIR / 多期 IC / 换手率"""
    try:
        d = _run_analysis(data)
        return ok(
            data={
                "factor_name": data.factor_name,
                "entity_type": data.entity_type,
                "ic_mean": d.get("ic"),
                "icir": d.get("ir"),
                "ic_by_period": d.get("ic_by_period"),
                "ir_by_period": d.get("ir_by_period"),
                "turnover": d.get("turnover"),
                "method": data.method,
                "periods": data.periods,
            },
            message=f"IC analysis for {data.factor_name} completed",
        )
    except (ValidationError, BusinessError):
        raise
    except Exception as e:
        logger.error(f"Error analyzing factor IC {data.factor_name}: {e}")
        raise BusinessError(f"Error analyzing factor IC: {e}")


@router.post("/layering")
async def analyze_layering(data: FactorAnalysisRequest):
    """因子分层回测：分组统计 + 多空 spread。

    statistics 值已是 str(Decimal)（JSON-safe）；库内无 per-group 明细，
   不虚构 layers 数组。
    """
    try:
        d = _run_analysis(data)
        return ok(
            data={
                "factor_name": data.factor_name,
                "n_groups": data.n_groups,
                "spread": d.get("layering_spread"),
                "statistics": d.get("layering"),
                "turnover": d.get("turnover"),
            },
            message=f"Layering analysis for {data.factor_name} completed",
        )
    except (ValidationError, BusinessError):
        raise
    except Exception as e:
        logger.error(f"Error analyzing factor layering {data.factor_name}: {e}")
        raise BusinessError(f"Error analyzing factor layering: {e}")


@router.post("/decay")
async def analyze_decay(data: FactorAnalysisRequest):
    """因子衰减分析：半衰期 / 衰减速率 / 最优滞后 / lag IC 序列。

    取自报告 decay 段，丢弃 created_at/metadata 等内部字段。
    """
    try:
        d = _run_analysis(data)
        decay = d.get("decay") or {}
        return ok(
            data={
                "factor_name": data.factor_name,
                "max_lag": data.max_lag,
                "half_life": decay.get("half_life"),
                "decay_rate": decay.get("decay_rate"),
                "optimal_lag": decay.get("optimal_lag"),
                "lag_ic": decay.get("lag_ic"),
            },
            message=f"Decay analysis for {data.factor_name} completed",
        )
    except (ValidationError, BusinessError):
        raise
    except Exception as e:
        logger.error(f"Error analyzing factor decay {data.factor_name}: {e}")
        raise BusinessError(f"Error analyzing factor decay: {e}")
