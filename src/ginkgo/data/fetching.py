"""
Data Fetching and Persistence Logic

This module contains the core logic for fetching data from external sources (like Tushare)
and persisting it into the database using the CRUD layer.
"""
import pandas as pd
import time
from datetime import datetime, timedelta

from .sources import GinkgoTushare, GinkgoTDX
from .utils import get_crud, is_code_in_stocklist
from ..libs import (
    GCONF,
    GLOG,
    datetime_normalize,
    to_decimal,
    RichProgress,
)
from .models import MAdjustfactor, MBar, MStockInfo
from ..backtest import Tick
from ..enums import SOURCE_TYPES, FREQUENCY_TYPES, CURRENCY_TYPES, MARKET_TYPES, TICKDIRECTION_TYPES

# --- Adjustfactor --- #
def _get_adjustfactor_fetch_range(code: str, fast_mode: bool) -> tuple:
    adjustfactor_crud = get_crud('adjustfactor')
    start_date = datetime_normalize(GCONF.DEFAULTSTART)
    if fast_mode:
        latest = adjustfactor_crud.find(filters={"code": code}, page_size=1, desc_order=True)
        if latest:
            start_date = latest[0].timestamp + timedelta(days=1)
    return start_date, datetime.now()

def _prepare_adjustfactor_models(data: pd.DataFrame, code: str) -> list:
    items = []
    for _, r in data.iterrows():
        if pd.notna(r["adj_factor"]) and r["adj_factor"] > 0:
            items.append(
                MAdjustfactor(
                    code=code,
                    foreadjustfactor=to_decimal(r["adj_factor"]),
                    backadjustfactor=to_decimal(r["adj_factor"]),
                    adjustfactor=to_decimal(r["adj_factor"]),
                    timestamp=datetime_normalize(r["trade_date"]),
                    source=SOURCE_TYPES.TUSHARE,
                )
            )
    return items

def _persist_adjustfactors(code: str, items: list, fast_mode: bool):
    if not items:
        return
    adjustfactor_crud = get_crud('adjustfactor')
    if not fast_mode:
        min_date = min(item.timestamp for item in items)
        max_date = max(item.timestamp for item in items)
        adjustfactor_crud.remove(filters={"code": code, "timestamp__gte": min_date, "timestamp__lte": max_date})
        time.sleep(0.2)
    adjustfactor_crud.add_batch(items)
    GLOG.DEBUG(f"Persisted {len(items)} adjustfactor records for {code}.")

def process_adjustfactor_data(code: str, fast_mode: bool):
    if not is_code_in_stocklist(code):
        return

    start_date, end_date = _get_adjustfactor_fetch_range(code, fast_mode)
    GLOG.DEBUG(f"Fetching adjustfactors for {code} from {start_date.date()} to {end_date.date()}")

    try:
        raw_data = GinkgoTushare().fetch_cn_stock_adjustfactor(code=code, start_date=start_date, end_date=end_date)
        if raw_data is None or raw_data.empty:
            GLOG.DEBUG(f"No new adjustfactor data for {code}.")
            return
    except Exception as e:
        GLOG.ERROR(f"Failed to fetch adjustfactors for {code}: {e}")
        return

    model_items = _prepare_adjustfactor_models(raw_data, code)
    _persist_adjustfactors(code, model_items, fast_mode)

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
