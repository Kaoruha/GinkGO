from typing import Union
import yaml
import datetime

from ginkgo.libs.ginkgo_conf import GCONF
from sqlalchemy.orm import Session
from sqlalchemy import select
from fastapi import FastAPI, Depends
from fastapi.openapi.utils import get_openapi
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.middleware.cors import CORSMiddleware
from ginkgo.data.ginkgo_data import GDATA
from ginkgo.enums import FILE_TYPES
from ginkgo.libs.ginkgo_normalize import datetime_normalize
from ginkgo.data.models.model_backtest import MBacktest

app = FastAPI()

# 创建一个允许的源列表
origins = ["http://localhost", "http://127.0.0.1", "http://localhost:8080", "*"]
origins = ["*"]

# 将 CORS 中间件添加到您的应用程序中
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # 允许的源
    allow_credentials=True,  # 允许凭证（如 Cookies、授权 headers 等）
    allow_methods=["*"],  # 允许所有 HTTP 方法
    allow_headers=["*"],  # 允许所有 HTTP headers
)


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/api/v1/backtest")
async def fetch_backtest():
    df = GDATA.get_file_list_df(FILE_TYPES.BACKTEST)
    if df.shape[0] == 0:
        return []
    for i, r in df.iterrows():
        dic = yaml.safe_load(r["content"])
        df.loc[i, "date_start"] = datetime_normalize(dic["start"])
        df.loc[i, "date_end"] = datetime_normalize(dic["end"])
    res = df.to_dict(orient="records")
    return res


@app.get("/api/v1/record")
def fetch_record(page: int = 0, size: int = 100):
    df = GDATA.get_backtest_record_df_pagination(page, size)
    if df.shape[0] == 0:
        return []
    df["worth"] = df["profit"]
    res = df.to_dict(orient="records")
    return res


@app.get("/api/v1/analyzer")
def fetch_record(backtest_id: str = "", analyzer_id: str = ""):
    df = GDATA.get_analyzer_df_by_backtest(backtest_id, analyzer_id)
    if df.shape[0] == 0:
        return []
    res = df.to_dict(orient="records")
    return res


@app.get("/api/v1/order")
def fetch_order(backtest_id: str = "", date: str = ""):
    df = GDATA.get_order_df_by_backtest_and_date_range_pagination(
        backtest_id, date, date, 0, 1000
    )
    if df.shape[0] == 0:
        return []
    res = df.to_dict(orient="records")
    return res


@app.get("/api/v1/order_filled")
def fetch_order_filled(backtest_id: str = "", code: str = ""):
    df = GDATA.get_orderrecord_df(backtest_id, code)
    if df.shape[0] == 0:
        return []
    res = df.to_dict(orient="records")
    return res


@app.get("/api/v1/signal")
def fetch_signal(backtest_id: str = "", date: str = "", code: str = ""):
    if code == "":
        df = GDATA.get_signal_df_by_backtest_and_date_range_pagination(
            backtest_id, date, date, 0, 1000
        )
    else:
        df = GDATA.get_signal_df_by_backtest_and_code_pagination(
            backtest_id, code, GCONF.DEFAULTSTART, GCONF.DEFAULTEND, 0, 2000
        )
    if df.shape[0] == 0:
        return []
    res = df.to_dict(orient="records")
    return res


@app.get("/api/v1/stockinfo")
def fetch_stockinfo(code: str = ""):
    df = GDATA.get_stock_info_df_by_code(code)
    if df.shape[0] == 0:
        return None
    else:
        res = df.to_dict(orient="records")
        return res[0]


@app.get("/api/v1/daybar")
def fetch_daybar(code: str = "", date: str = ""):
    date = datetime_normalize(date)
    date_start = date + datetime.timedelta(days=-120)
    date_end = date + datetime.timedelta(days=60)
    df = GDATA.get_daybar_df(code, date_start, date_end)
    if df.shape[0] == 0:
        return None
    else:
        res = df.to_dict(orient="records")
        return res
