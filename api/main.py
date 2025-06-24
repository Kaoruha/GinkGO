from typing import Union
import yaml
import json
import datetime
import asyncio

from ginkgo.libs.core.config import GCONF
from sqlalchemy.orm import Session
from sqlalchemy import select
from fastapi import FastAPI, Depends, Request
from fastapi.openapi.utils import get_openapi
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from ginkgo.data.ginkgo_data import GDATA
from ginkgo.enums import FILE_TYPES, DIRECTION_TYPES, ORDER_TYPES
from ginkgo.libs.data.normalize import datetime_normalize
from ginkgo.libs import GLOG, GinkgoLogger
from ginkgo.backtest.portfolios.portfolio_live import PortfolioLive

app = FastAPI()
api_logger = GinkgoLogger("ginkgo_api", ["ginkgo_api.log"])

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
async def read_root():
    api_logger.INFO("api test.")
    return "Hello, Ginkgo API Server is running."


@app.get("/api/v1/backtest")
async def fetch_backtest():
    df = GDATA.get_file_list_df(FILE_TYPES.ENGINE)
    if df.shape[0] == 0:
        return []
    for i, r in df.iterrows():
        dic = yaml.safe_load(r["content"])
        df.loc[i, "date_start"] = datetime_normalize(dic["start"])
        df.loc[i, "date_end"] = datetime_normalize(dic["end"])
    res = df.to_dict(orient="records")
    return res


@app.get("/api/v1/record")
async def fetch_record(page: int = 0, size: int = 100):
    df = GDATA.get_backtest_record_df_pagination(page, size)
    if df.shape[0] == 0:
        return []
    df["worth"] = df["profit"]
    res = df.to_dict(orient="records")
    return res


@app.get("/api/v1/analyzer")
async def fetch_record(backtest_id: str = "", analyzer_id: str = ""):
    df = GDATA.get_analyzer_df_by_backtest(backtest_id, analyzer_id)
    if df.shape[0] == 0:
        return []
    res = df.to_dict(orient="records")
    return res


@app.get("/api/v1/order")
async def fetch_order(backtest_id: str = "", date: str = ""):
    df = GDATA.get_order_df_by_backtest_and_date_range_pagination(backtest_id, date, date, 0, 1000)
    if df.shape[0] == 0:
        return []
    res = df.to_dict(orient="records")
    return res


@app.get("/api/v1/order_filled")
async def fetch_order_filled(backtest_id: str = "", code: str = ""):
    df = GDATA.get_orderrecord_df(backtest_id, code)
    if df.shape[0] == 0:
        return []
    res = df.to_dict(orient="records")
    return res


@app.get("/api/v1/signal")
async def fetch_signal(backtest_id: str = "", date: str = "", code: str = ""):
    if code == "":
        df = GDATA.get_signal_df_by_backtest_and_date_range_pagination(backtest_id, date, date, 0, 1000)
    else:
        df = GDATA.get_signal_df_by_backtest_and_code_pagination(
            backtest_id, code, GCONF.DEFAULTSTART, GCONF.DEFAULTEND, 0, 2000
        )
    if df.shape[0] == 0:
        return []
    res = df.to_dict(orient="records")
    return res


@app.get("/api/v1/stockinfo")
async def fetch_stockinfo(code: str = ""):
    df = GDATA.get_stock_info_df_by_code(code)
    if df.shape[0] == 0:
        return None
    else:
        res = df.to_dict(orient="records")
        return res[0]


@app.get("/api/v1/daybar")
async def fetch_daybar(code: str = "", date: str = ""):
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
async def fetch_file_list(query: str = "", page: int = 0, size: int = 100):
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
async def fetch_file(file_id: str = ""):
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
async def rename_file(id: str = "", name: str = ""):
    res = GDATA.update_file(id=id, name=name)
    return res


@app.get("/api/v1/del_backtest")
async def del_backtest(id: str = ""):
    res = GDATA.remove_backtest(id)
    result_order = GDATA.remove_orders(id)
    result_ana = GDATA.remove_analyzers(id)
    result_pos = GDATA.remove_positions(id)
    return res


@app.get("/api/v1/add_liveportfolio")
async def add_liveportfolio(id: str = "", name: str = ""):
    res = GDATA.add_liveportfolio_from_backtest(id, name)
    return res


@app.post("/api/v1/del_liveportfolio")
async def del_liveportfolio(id: str = ""):
    # Kill the proc
    GDATA.remove_liveengine(id)
    # Remove file related to live
    GDATA.del_liveportfolio_related(id)
    # TODO Remove transfer records
    # Remove order records
    res = GDATA.remove_orderrecords_by_portfolio(id)
    # Remove live portfolio itself
    res = GDATA.remove_liveportfolio(id)
    print("del live")
    return res


@app.get("/api/v1/liveportfolio")
async def fetch_liveportfolio(page: int = 0, size: int = 100):
    df = GDATA.get_liveportfolio_df_pagination(page, size)
    if df.shape[0] == 0:
        return []
    df["worth"] = df["profit"]
    res = df.to_dict(orient="records")
    for i in res:
        fid = i["uuid"]
        status = GDATA.get_live_status_by_id(fid)
        i["status"] = status if status else "stop"
    return res


@app.get("/api/v1/code_list")
async def fetch_code_list(query: str = "", page: int = 0, size: int = 10):
    df = GDATA.get_stockinfo_df_fuzzy(query, page, size)
    if df.shape[0] == 0:
        return []
    res = df.to_dict(orient="records")
    return res


@app.post("/api/v1/del_traderecord")
async def del_traderecord(id: str = ""):
    res = GDATA.remove_orderrecord_by_id(id)
    if res:
        return "Delete Success."
    return "Delete Failed."


@app.post("/api/v1/add_traderecord")
async def add_traderecord(
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
    # TODO 需要加上校验 可能当天没有价格,无法成交
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
    p = PortfolioLive()
    p.set_portfolio_id(id)
    l = p.reset_positions()


@app.post("/api/v1/update_traderecord")
async def update_traderecord(
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
async def fetch_traderecrod(id: str = "", page: int = 0, size: int = 1000):
    df = GDATA.get_orderrecord_df_pagination(id, "2000-01-01", "2050-01-01", page, size)
    df = df.sort_values(by="timestamp", ascending=True)
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
    res = df.to_dict(orient="records")
    return res


@app.get("/api/v1/reset_liveposition")
async def reset_liveposition(id: str = ""):
    p = PortfolioLive()
    p.set_portfolio_id(id)
    l = p.reset_positions()


@app.get("/api/v1/live_position")
async def fetch_liveposition(id: str = "", page: int = 0, size: int = 1000):
    l = GDATA.get_positionrecords_pagination(backtest_id=id, page=0, size=1000)
    res = []
    for i in l:
        i.cost = float(i.cost)
        i.volume = int(i.volume)
        item = {}
        info = GDATA.get_stock_info_df_by_code(i.code)
        item["code"] = i.code
        item["code_name"] = info.code_name.values[0]
        item["cost"] = i.cost
        item["volume"] = i.volume
        latest_price = GDATA.get_latest_price(i.code)
        if latest_price[0] == 0:
            continue
        if latest_price[1] == 0:
            continue

        item["price"] = latest_price[0]
        item["change"] = latest_price[0] - latest_price[1]
        item["change_pct"] = (latest_price[0] - latest_price[1]) / latest_price[1]
        item["unrealized"] = (latest_price[0] - i.cost) * i.volume
        item["unrealized_pct"] = (latest_price[0] - i.cost) / i.cost
        res.append(item)
    return res


async def live_status_query():
    count = 0
    while True:
        await asyncio.sleep(2)
        count += 1
        if count > 10:
            # TODO Move to main control in future
            GDATA.clean_live_status()
            count = 0
        data = GDATA.get_live_status()
        yield f"data: {json.dumps(data)}\n\n"


@app.get("/stream/v1/live_status")
async def stream_live_status():
    return StreamingResponse(live_status_query(), media_type="text/event-stream")


async def live_price_stream():
    count = 0
    concerned_list = []  # TODO get from redis
    while True:
        await asyncio.sleep(10)
        count += 1
        if count > 10:
            # TODO Move to main control in future
            count = 0
        res = {}
        for i in concerned_list:
            res[i] = 1  # TODO get price from redis
        yield f"data: {json.dumps(res)}\n\n"


@app.get("/stream/v1/live_price")
async def stream_live_price():
    return StreamingResponse(live_price_stream(), media_type="text/event-stream")


@app.post("/api/v1/live_control")
async def send_live_control_signal(id: str, command: str):
    if command.upper() == "START":
        GDATA.send_signal_run_live(id)
        GLOG.INFO(f"Try start live engine {id}")
    if command.upper() == "STOP":
        GDATA.send_signal_stop_live(id)
        GLOG.INFO(f"Try stop live engine {id}")
    try:
        if command.upper() == "START":
            cmd = "start"
        elif command.upper() == "STOP":
            cmd = "stop"
        elif command.upper() == "PAUSE":
            cmd = "pause"
        elif command.upper() == "RESTART":
            cmd = "restart"
        elif command.upper() == "RESUME":
            cmd = "resume"
        GDATA.send_signal_to_liveengine(id, cmd)
        GLOG.INFO(f"Try send signal {cmd} to live engine {id}")
        return f"Order send success. {cmd}"
    except Exception as e:
        return f"Order send failed. {e}"
