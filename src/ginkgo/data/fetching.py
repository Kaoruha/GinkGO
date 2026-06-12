# Upstream: 数据服务层(StockinfoService调用process_stockinfo_data)
# Downstream: 数据源(GinkgoTushare/GinkgoTDX提供外部数据获取)、CRUD层(AdjustfactorCRUD/StockInfoCRUD)、数据模型(MAdjustfactor/MBar/MStockInfo)、枚举类型(SOURCE_TYPES/FREQUENCY_TYPES/CURRENCY_TYPES/MARKET_TYPES/TICKDIRECTION_TYPES)
# Role: 数据获取和持久化模块从Tushare/TDX等获取数据并使用CRUD层持久化到数据库






"""
Data Fetching and Persistence Logic

This module contains the core logic for fetching data from external sources (like Tushare)
and persisting it into the database using the CRUD layer.
"""
import pandas as pd

from ginkgo.data.sources import GinkgoTushare, GinkgoTDX
from ginkgo.data.utils import get_crud
from ginkgo.libs import (
    GLOG,
    datetime_normalize,
    RichProgress,
)
from ginkgo.data.models import MBar, MStockInfo
from ginkgo.entities import Tick
from ginkgo.enums import SOURCE_TYPES, FREQUENCY_TYPES, CURRENCY_TYPES, MARKET_TYPES, TICKDIRECTION_TYPES

# --- StockInfo --- #
def _upsert_stock_info_batch(all_stocks_df: pd.DataFrame):
    stock_info_crud = get_crud('stock_info')
    with RichProgress() as progress:
        task = progress.add_task("[cyan]Upserting Stock Info", total=all_stocks_df.shape[0])
        for _, r in all_stocks_df.iterrows():
            code = r["ts_code"]
            progress.update(task, advance=1, description=f"{code} {r['name']}")
            stock_data = {
                "code": code,
                "code_name": r["name"],
                "industry": r["industry"],
                "currency": CURRENCY_TYPES.CNY,
                "market": MARKET_TYPES.CHINA,
                "list_date": datetime_normalize(r["list_date"]),
                "delist_date": datetime_normalize(r["delist_date"]) if pd.notna(r["delist_date"]) else None,
                "source": SOURCE_TYPES.TUSHARE,
            }
            try:
                if stock_info_crud.exists(filters={"code": code}):
                    stock_info_crud.modify(filters={"code": code}, updates=stock_data)
                else:
                    stock_info_crud.create(**stock_data)
            except Exception as e:
                GLOG.ERROR(f"Failed to upsert stock info for {code}: {e}")

def process_stockinfo_data():
    try:
        all_stocks = GinkgoTushare().fetch_cn_stockinfo()
        if all_stocks is None or all_stocks.empty:
            GLOG.WARN("No stock info data returned from Tushare.")
            return
    except Exception as e:
        GLOG.ERROR(f"Failed to fetch stock info from Tushare: {e}")
        return
    _upsert_stock_info_batch(all_stocks)

