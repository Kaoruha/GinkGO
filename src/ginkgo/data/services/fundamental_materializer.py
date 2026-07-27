# Upstream: GinkgoTushare.fetch_cn_fundancial_indicator(财报 DataFrame) + FactorService.add_factor_batch(存储)
# Downstream: CLI/API 基本面物化命令 (#6795 L2)
# Role: tushare fina_indicator 财报字段 → 因子存储行(category=fundamental, entity=STOCK, ts=公告日 ann_date)

import pandas as pd

from ginkgo.enums import ENTITY_TYPES
from ginkgo.data.services.base_service import ServiceResult


class FundamentalFactorMaterializer:
    """
    基本面财报 → 因子物化器 (#6795)

    把数据源(tushare fina_indicator)返回的财报 DataFrame 转成因子存储行
    (entity_type=STOCK, factor_category=fundamental, timestamp=公告日 ann_date),
    批量写入因子存储。timestamp 取公告日而非报告期——报告期 end_date 早于实际公告日,
    forward-fill 后会构成 PIT 前瞻(详见 factor_assembly 的 ffill 契约),故必须用 ann_date。

    非幂等:因子存储(MFactor 为 ClickHouse MergeTree,无唯一约束)的 add_factor_batch
    是纯 append,重复物化同一 (code, period) 会追加重复行。新财报季补数即增量更新、
    不重算历史;但同季重跑会累积重复行——读侧 factor_assembly 按 timestamp 去重
    (duplicated keep="last")兜底,财报重述需覆盖旧值时调用方应先
    delete_factors_by_entity 清掉旧 timestamp 行再物化。
    """

    # tushare fina_indicator 字段 → 因子名
    FIELD_MAP = {
        "eps": "EPS",
        "bps": "BPS",
        "roe": "ROE",
        "dt_roe": "DILUTED_ROE",
        "profit_to_gr": "NET_MARGIN",
        "debt_to_assets": "DEBT_TO_ASSETS",
    }

    CATEGORY = "fundamental"

    def __init__(self, source, factor_service):
        """
        Args:
            source: 数据源,需提供 fetch_cn_fundancial_indicator(code, period) -> DataFrame
            factor_service: 因子服务,需提供 add_factor_batch(List[Dict]) -> ServiceResult
        """
        self.source = source
        self.factor_service = factor_service

    def materialize(self, code: str, period: str):
        """
        物化单股单报告期的基本面因子。

        Args:
            code: 股票代码 (ts_code, 如 "000001.SZ")
            period: 报告期 (YYYYMMDD, 如 "20240331")

        Returns:
            ServiceResult: add_factor_batch 的结果;空数据返成功空结果。
        """
        df = self.source.fetch_cn_fundancial_indicator(code=code, period=period)
        if df is None or df.empty:
            return ServiceResult(
                success=True,
                data={"records_added": 0},
                message=f"No fundamental data for {code} @ {period}",
            )

        factors = []
        for _, row in df.iterrows():
            ts_code = str(row.get("ts_code", code))
            end_date = row.get("end_date", period)
            # PIT 严谨:timestamp 取公告日 ann_date,而非报告期 end_date。
            # 报告期早于公告日,forward-fill 后会用未公告数据(lookahead);ann_date 缺失才回退 end_date。
            ann_date = row.get("ann_date", end_date)
            for src_field, factor_name in self.FIELD_MAP.items():
                if src_field in row.index and pd.notna(row[src_field]):
                    factors.append(
                        {
                            "entity_type": ENTITY_TYPES.STOCK,
                            "entity_id": ts_code,
                            "factor_name": factor_name,
                            "factor_value": row[src_field],
                            "factor_category": self.CATEGORY,
                            "timestamp": ann_date,
                        }
                    )

        if not factors:
            return ServiceResult(
                success=True,
                data={"records_added": 0},
                message=f"No mappable fundamental fields for {code} @ {period}",
            )

        return self.factor_service.add_factor_batch(factors)
