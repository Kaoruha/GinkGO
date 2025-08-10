import pandas as pd


from concurrent.futures import ProcessPoolExecutor, as_completed
import time
import random

import pandas as pd
import datetime
from typing import Optional
from sqlalchemy import text

from decimal import Decimal
from functools import singledispatchmethod
from sqlalchemy import Column, String, Integer, DECIMAL, Enum
from sqlalchemy.orm import Mapped, mapped_column

from src.ginkgo.enums import SOURCE_TYPES, TICKDIRECTION_TYPES
from src.ginkgo.data.drivers import _connection_manager, is_table_exists
from src.ginkgo.data.crud.tick_crud import *
import uuid
import datetime

from typing import Optional
from types import FunctionType, MethodType
from sqlalchemy import Enum, String, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import DeclarativeBase
from clickhouse_sqlalchemy import engines


from src.ginkgo.data.models.model_base import MBase
from src.ginkgo.libs import datetime_normalize
from src.ginkgo.libs.utils.display import base_repr
from src.ginkgo.enums import SOURCE_TYPES


import json, os, threading, time
from typing import List


STATE_FILE = "migration_state.json"
_lock = threading.RLock()  # 改用 RLock 允许同一线程重入
_TIMEOUT = 5  # 秒


def _load() -> List[str]:
    # 读操作无需排他锁
    try:
        with open(STATE_FILE) as f:
            return json.load(f).get("done_codes", [])
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save(codes: List[str]):
    # 写操作加锁，带超时
    if _lock.acquire(timeout=_TIMEOUT):
        try:
            tmp = STATE_FILE + ".tmp"
            with open(tmp, "w") as f:
                json.dump({"done_codes": codes}, f, separators=(",", ":"))
            os.replace(tmp, STATE_FILE)
        finally:
            _lock.release()
    else:
        raise RuntimeError("Could not acquire lock in time")


def mark_done(code: str) -> bool:
    with _lock:  # 自动释放
        codes = set(_load())
        if code in codes:
            return False
        codes.add(code)
        _save(list(codes))
        return True


def is_done(code: str) -> bool:
    # 只读，不拿锁
    return code in _load()


class Base(DeclarativeBase):
    pass


class MClickMigrationBase(Base, MBase):
    __abstract__ = True
    __tablename__ = "ClickMigrationBaseModel"
    __table_args__ = (
        engines.MergeTree(order_by=("timestamp",)),
        {"extend_existing": True},
    )

    uuid: Mapped[str] = mapped_column(String(), primary_key=True, default=lambda: str(uuid.uuid4().hex))
    meta: Mapped[Optional[str]] = mapped_column(String(), default="{}")
    desc: Mapped[Optional[str]] = mapped_column(String(), default="This man is lazy, there is no description.")
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime)
    source: Mapped[SOURCE_TYPES] = mapped_column(Enum(SOURCE_TYPES), default=SOURCE_TYPES.OTHER)


class MTickMigration(MClickMigrationBase):
    __abstract__ = True
    __tablename__ = "tick"

    code: Mapped[str] = mapped_column(String(), default="ginkgo_test_code")
    price: Mapped[Decimal] = mapped_column(DECIMAL(16, 2), default=0)
    volume: Mapped[int] = mapped_column(Integer, default=0)
    direction: Mapped[TICKDIRECTION_TYPES] = mapped_column(Enum(TICKDIRECTION_TYPES), default=TICKDIRECTION_TYPES.OTHER)


def get_tick_migration_model(code: str) -> type:
    table_name = f"{code.replace('.', '_')}_Tick_Migration"

    newclass = type(
        table_name,
        (MTickMigration,),
        {
            "__tablename__": table_name,
            "__abstract__": False,
        },
    )
    return newclass


def migrate_one(code: str):
    if is_done(code):
        return
    # is talbe exist
    if not is_table_exists(get_tick_model(code)):
        mark_done(code)
        return
    drop_table(get_tick_migration_model(code).__tablename__)
    create_migration_table(code)
    copy_data(code)
    rename_talbe(get_tick_model(code).__tablename__, f"{get_tick_model(code).__tablename__}_Back")
    rename_talbe(get_tick_migration_model(code).__tablename__, get_tick_model(code).__tablename__)
    drop_table(f"{get_tick_model(code).__tablename__}_Back")
    drop_table(get_tick_migration_model(code).__tablename__)
    mark_done(code)


def rename_talbe(old_table_name: str, new_table_name: str):
    _connection_manager.get_clickhouse_connection().session.execute(
        text(f"RENAME TABLE {old_table_name} TO {new_table_name}")
    )


def drop_table(name: str):
    _connection_manager.get_clickhouse_connection().session.execute(text(f"DROP TABLE IF EXISTS {name}"))


def create_migration_table(code):
    model = get_tick_migration_model(code)

    model.metadata.create_all(bind=_connection_manager.get_clickhouse_connection().engine)


def copy_data(code: str):
    print(f"copy {code}")
    origin_model = get_tick_model(code)
    migration_model = get_tick_migration_model(code)
    origin_crud = TickCRUD(code)
    count = origin_crud.count()
    count_per_page = 100000
    max_page = int(count / count_per_page) + 1
    for i in range(max_page):
        df = origin_crud.find_by_time_range(page=i, page_size=count_per_page, as_dataframe=True)
        print(df)
        to_insert_list = []
        for index, row in df.iterrows():
            item = migration_model()
            # 复制所有核心字段
            item.code = row["code"]
            item.price = row["price"]
            item.volume = row["volume"]
            item.direction = row["direction"]
            item.timestamp = row["timestamp"]
            item.source = row.get("source", SOURCE_TYPES.TDX)
            item.uuid = row.get("uuid", str(uuid.uuid4().hex))
            item.meta = row.get("meta", "{}")

            to_insert_list.append(item)
        bulk_insert(to_insert_list)
        to_insert_list = []


def bulk_insert(insert_list):
    click_conn = _connection_manager.get_clickhouse_connection()

    # 使用上下文管理器改进会话管理
    with click_conn.get_session() as session:
        # 使用bulk_insert_mappings提高ClickHouse插入性能
        model_groups = {}
        for item in insert_list:
            model_type = type(item)
            if model_type not in model_groups:
                model_groups[model_type] = []
            model_groups[model_type].append(item)

        # 为每个模型类型执行批量插入
        for model_type, items in model_groups.items():
            try:
                # 将对象转换为字典
                mappings = []
                for item in items:
                    mapping = {}
                    for column in item.__table__.columns:
                        mapping[column.name] = getattr(item, column.name)
                    mappings.append(mapping)

                # 执行批量插入
                session.bulk_insert_mappings(model_type, mappings)
                print(f"ClickHouse bulk inserted {len(mappings)} {model_type.__name__} records")

            except Exception as bulk_error:
                print(f"ClickHouse bulk insert failed for {model_type.__name__}, falling back to add_all: {bulk_error}")
                # 回退到add_all方法
                session.add_all(items)
    # click_count = len(insert_list)
    # print(f"Clickhouse committed {len(insert_list)} records total.")


if __name__ == "__main__":
    from src.ginkgo.data import get_stockinfos

    cn_index = get_stockinfos()["code"].tolist()

    with ProcessPoolExecutor(max_workers=12) as pool:
        # 提交所有任务
        futures = [pool.submit(migrate_one, code) for code in cn_index]

        # 按完成顺序打印结果
        for f in as_completed(futures):
            print(f.result())

    print("所有任务完成，线程池已自动关闭。")
