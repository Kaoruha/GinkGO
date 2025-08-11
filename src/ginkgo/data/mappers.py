"""
Data Mappers

This module is responsible for mapping data from one format to another,
for example, from a raw Pandas DataFrame to a list of database models.
This isolates transformation logic and makes it reusable.
"""
import pandas as pd
from typing import List, Any

from ..libs import datetime_normalize, to_decimal, GCONF
from .models import MAdjustfactor, MStockInfo, MBar
from .crud.tick_crud import get_tick_model
from ..enums import SOURCE_TYPES, CURRENCY_TYPES, MARKET_TYPES, FREQUENCY_TYPES, TICKDIRECTION_TYPES

def dataframe_to_adjustfactor_models(df: pd.DataFrame, code: str) -> List[MAdjustfactor]:
    """
    Maps a DataFrame from Tushare to a list of MAdjustfactor models.
    
    Note: Only saves the original adj_factor from Tushare. 
    The fore/back adjust factors are set to default values (1.0) and will be 
    calculated separately using the calc command.
    """
    items = []
    for _, r in df.iterrows():
        if pd.notna(r["adj_factor"]) and r["adj_factor"] > 0:
            items.append(
                MAdjustfactor(
                    code=code,
                    foreadjustfactor=to_decimal(1.0),                    # Default value, calculated later
                    backadjustfactor=to_decimal(1.0),                    # Default value, calculated later
                    adjustfactor=to_decimal(r["adj_factor"]),            # Original Tushare adj_factor
                    timestamp=datetime_normalize(r["trade_date"]),
                    source=SOURCE_TYPES.TUSHARE.value,
                )
            )
    return items

def row_to_stockinfo_upsert_dict(row: pd.Series) -> dict:
    """Maps a single row from Tushare DataFrame to a dictionary for upserting MStockInfo."""
    # Handle delist_date: use default end date if None
    delist_date = row["delist_date"]
    if pd.notna(delist_date):
        delist_date = datetime_normalize(delist_date)
    else:
        # Use GCONF.DEFAULTEND as default delist date for active stocks
        delist_date = datetime_normalize(GCONF.DEFAULTEND)
    
    return {
        "code": row["ts_code"],
        "code_name": row["name"],
        "industry": row["industry"],
        "currency": CURRENCY_TYPES.CNY.value,
        "market": MARKET_TYPES.CHINA.value,
        "list_date": datetime_normalize(row["list_date"]),
        "delist_date": delist_date,
        "source": SOURCE_TYPES.TUSHARE.value,
    }

def dataframe_to_stockinfo_upsert_list(df: pd.DataFrame) -> List[dict]:
    """Maps a DataFrame from Tushare to a list of dictionaries for upserting MStockInfo."""
    items = []
    for _, r in df.iterrows():
        item = row_to_stockinfo_upsert_dict(r)
        items.append(item)
    return items

def dataframe_to_bar_models(df: pd.DataFrame, code: str, frequency: FREQUENCY_TYPES = FREQUENCY_TYPES.DAY) -> List[MBar]:
    """Maps a DataFrame from Tushare to a list of MBar models."""
    items = []
    for _, r in df.iterrows():
        # Skip rows with invalid data
        if pd.isna(r["open"]) or pd.isna(r["close"]) or pd.isna(r["high"]) or pd.isna(r["low"]):
            continue
            
        items.append(
            MBar(
                code=code,
                open=to_decimal(r["open"]),
                high=to_decimal(r["high"]),
                low=to_decimal(r["low"]),
                close=to_decimal(r["close"]),
                volume=int(r["vol"]) if pd.notna(r["vol"]) else 0,
                amount=to_decimal(r["amount"]) if pd.notna(r["amount"]) else to_decimal(0),
                frequency=FREQUENCY_TYPES.validate_input(frequency),
                timestamp=datetime_normalize(r["trade_date"]),
                source=SOURCE_TYPES.TUSHARE.value,
            )
        )
    return items

def dataframe_to_tick_models(df: pd.DataFrame, code: str) -> List[Any]:
    """Maps a DataFrame from TDX to a list of dynamic tick models for the specific stock code."""
    # Get the dynamic tick model class for this stock code
    tick_model_class = get_tick_model(code)
    
    items = []
    for _, r in df.iterrows():
        # Skip rows with invalid data
        if pd.isna(r["price"]) or pd.isna(r["volume"]) or pd.isna(r["timestamp"]):
            continue
            
        # Convert buyorsell to TICKDIRECTION_TYPES
        direction = TICKDIRECTION_TYPES(r["buyorsell"]) if "buyorsell" in r and pd.notna(r["buyorsell"]) else TICKDIRECTION_TYPES.UNKNOWN
        
        items.append(
            tick_model_class(
                code=code,
                price=to_decimal(r["price"]),
                volume=int(r["volume"]),
                direction=TICKDIRECTION_TYPES.validate_input(direction),
                timestamp=r["timestamp"],
                source=SOURCE_TYPES.TDX.value,
            )
        )
    return items
