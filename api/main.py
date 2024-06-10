from typing import Union
import yaml
import datetime

from ginkgo.libs.ginkgo_conf import GCONF
from sqlalchemy.orm import Session
from sqlalchemy import select
from fastapi import FastAPI, Depends, Request
from fastapi.openapi.utils import get_openapi
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.middleware.cors import CORSMiddleware
from ginkgo.data.ginkgo_data import GDATA
from ginkgo.enums import FILE_TYPES, DIRECTION_TYPES, ORDER_TYPES
from ginkgo.libs.ginkgo_normalize import datetime_normalize
from ginkgo.data.models.model_backtest import MBacktest
from ginkgo.backtest.portfolios.portfolio_live import PortfolioLive

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


@app.get("/api/v1/file_list")
def fetch_file_list(query: str = "", page: int = 0, size: int = 100):
    def convert(enum):
        return enum.name.lower()

    print(f"Try get files in Size:{size} Index:{page}")
    file_type = FILE_TYPES.enum_convert(query)
    if file_type is None:
        df = GDATA.get_file_list_df_fuzzy(query, page, size)
    else:
        df = GDATA.get_file_list_df(file_type, page, size)

    df.drop(["content", "isdel", "desc"], axis=1, inplace=True)

    if df.shape[0] == 0:
        return []
    df["type"] = df["type"].apply(convert)
    res = df.to_dict(orient="records")
    return res


@app.get("/api/v1/file")
def fetch_file(file_id: str = ""):
    res = GDATA.get_file_by_id(file_id)
    print("Get file by id:")
    print(file_id)
    print(res.content)
    print("======================")
    return res


@app.post("/api/v1/update_file")
async def update_file(file_id: str = "", request: Request = {}):
    json_data = await request.json()
    content = json_data.get("content")
    bytes_content = content.encode("utf-8")
    res = GDATA.update_file(id=file_id, content=bytes_content)
    return res


@app.post("/api/v1/rename_file")
def rename_file(id: str = "", name: str = ""):
    res = GDATA.update_file(id=id, name=name)
    return res


@app.get("/api/v1/del_backtest")
def del_backtest(id: str = ""):
    res = GDATA.remove_backtest(id)
    print(res)
    return res


@app.get("/api/v1/add_liveportfolio")
def add_liveportfolio(id: str = "", name: str = ""):
    res = GDATA.add_liveportfolio_from_backtest(id, name)
    print(res)
    return res


@app.post("/api/v1/del_liveportfolio")
def del_liveportfolio(id: str = ""):
    print(id)
    res = GDATA.remove_orderrecords_by_portfolio(id)
    print(res)
    res = GDATA.remove_liveportfolio(id)
    print(res)
    return res


@app.get("/api/v1/liveportfolio")
def fetch_liveportfolio(page: int = 0, size: int = 100):
    df = GDATA.get_liveportfolio_df_pagination(page, size)
    if df.shape[0] == 0:
        return []
    df["worth"] = df["profit"]
    res = df.to_dict(orient="records")
    print(res)
    return res


@app.get("/api/v1/code_list")
def fetch_code_list(query: str = "", page: int = 0, size: int = 10):
    df = GDATA.get_stockinfo_df_fuzzy(query, page, size)
    if df.shape[0] == 0:
        return []
    res = df.to_dict(orient="records")
    print(res)
    return res


@app.post("/api/v1/del_traderecord")
def del_traderecord(id: str = ""):
    res = GDATA.remove_orderrecord_by_id(id)
    if res:
        return "Delete Success."
    return "Delete Failed."


@app.post("/api/v1/add_traderecord")
def add_traderecord(
    id: str = "",
    code: str = "",
    direction: str = "",
    date: str = "",
    price: float = 0,
    volume: int = 0,
    comission: float = 0,
    fee: float = 0,
):
    direction_type = DIRECTION_TYPES.enum_convert(direction)
    timestamp = datetime_normalize(date)
    GDATA.add_order_record(
        id,
        code,
        direction_type,
        ORDER_TYPES.LIMITORDER,
        price,
        volume,
        0,
        fee,
        timestamp,
    )


@app.post("/api/v1/update_traderecord")
def update_traderecord(
    id: str = "",
    code: str = "",
    direction: str = "",
    date: str = "",
    price: float = 0,
    volume: int = 0,
    comission: float = 0,
    fee: float = 0,
):
    direction_type = DIRECTION_TYPES.enum_convert(direction)
    timestamp = datetime_normalize(date)
    GDATA.update_order_record(
        id,
        code,
        direction_type,
        ORDER_TYPES.LIMITORDER,
        price,
        volume,
        0,
        fee,
        timestamp,
    )


@app.get("/api/v1/traderecord")
def fetch_traderecrod(id: str = "", page: int = 0, size: int = 1000):
    df = GDATA.get_orderrecord_df_pagination(id, "2000-01-01", "2050-01-01", page, size)
    if df.shape[0] == 0:
        return []
    df["name"] = "Unknown"
    code_info_df = GDATA.get_stock_info_df()
    for i, r in df.iterrows():
        code = r["code"]
        if code not in code_info_df["code"].values:
            continue
        name = code_info_df[code_info_df["code"] == code]["code_name"].values[0]
        df.loc[df["code"] == code, "name"] = name
    print(df.shape[0])
    res = df.to_dict(orient="records")
    return res


@app.get("/api/v1/live_position")
def fetch_liveposition(id: str = "", page: int = 0, size: int = 1000):
    print(id)
    p = PortfolioLive()
    p.set_portfolio_id(id)
    l = p.recover_position(datetime.datetime.now())
    res = []
    for i in l:
        item = {}
        info = GDATA.get_stock_info_df_by_code(i.code)
        item["code"] = i.code
        item["code_name"] = info.code_name.values[0]
        item["cost"] = i.cost
        item["volume"] = i.volume
        now = datetime.datetime.now()
        date_start = now + datetime.timedelta(days=-20)
        price_info = GDATA.get_daybar_df(
            code=i.code, date_start=date_start, date_end=now
        )
        info = price_info.iloc[-1]
        item["price"] = info["close"]
        item["change"] = info["close"] - info["open"]
        item["change_pct"] = (info["close"] - info["open"]) / info["open"]
        item["unrealized"] = (info["close"] - i.cost) * i.volume
        item["unrealized_pct"] = (info["close"] - i.cost) / i.cost
        res.append(item)
    return res
