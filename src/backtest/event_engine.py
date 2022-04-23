import time
import queue
import datetime
import pandas as pd
from threading import Thread
from src.backtest.enums import EventType
from src.data.ginkgo_mongo import ginkgo_mongo as gm
from src.backtest.events import Event, MarketEvent
from src.backtest.price import Bar
from src.libs import GINKGOLOGGER as gl


class EventEngine(object):
    """
    事件驱动引擎

    """

    def __init__(self, *, heartbeat: float = 0) -> None:
        """
        初始化
        """
        self._event_queue = queue.Queue()  # 事件队列
        self._info_queue = queue.Queue()  # 信息队列
        self._active = False  # 事件引擎开关,引擎初始化时状态设置为关闭
        self._thread = Thread(target=self.__run)  # 事件处理线程
        # self.__feed_thread = Thread(target=self.__feed)
        self.heartbeat = heartbeat  # 心跳间隔
        self._handlers = {}  # 事件处理的回调函数
        self._general_handlers = (
            []
        )  # __general_handlers是一个列表，与__handlers类似，用来保存通用回调函数（所有事件均调用）
        self._next_day = None
        self._price_pool = {}  # 价格信息池

    def set_heartbeat(self, heartbeat: float) -> None:
        """
        设置心跳间隔
        """
        if heartbeat > 0:
            self.heartbeat = heartbeat
            gl.logger.info(f"设置心跳间隔为「{heartbeat}s」")
        else:
            gl.logger.warning("heartbeat should bigger than 0")

    def __run(self) -> None:
        """引擎运行"""
        while self._active:
            try:
                e = self._event_queue.get(block=False)  # 获取消息的阻塞时间
                self.__process(e)
                # 每个循环都会把一个事件带来的所有事件处理完再处理事件
            except queue.Empty:
                # 事件列表为空时，回测结束，Live系统应该继续等待
                # TODO 调用分析模块
                gl.logger.info("回测结束")
                break
            # 当心跳不为0时，事件引擎会短暂停歇，默认如果调用set_heartbeat设置心跳，不开启，但是可能CPU负荷过高
            if self.heartbeat != 0:
                time.sleep(self.heartbeat)

    def __process(self, event: Event) -> None:
        """处理事件"""
        # 检查是否存在对该事件进行监听的处理函数
        if event.event_type in self._handlers:
            # 若存在，将事件传递给处理函数执行
            gl.logger.info(f"处理{event}")
            [handler(event) for handler in self._handlers[event.event_type]]

            # 以上语句为Python列表解析方式的写法，对应的常规循环写法为：
            # for handler in self.__handlers[event.type_]:
            #     handler(event)
        else:
            gl.logger.error(f"没有{event.event_type}对应的处理函数")

        # 调用通用处理函数进行处理
        if self._general_handlers:
            [handler(event) for handler in self._general_handlers]

    def start(self) -> None:
        """
        引擎启动
        """
        # TODO 回头实盘引擎需要加入定时器定期获取数据处理数据
        # 将引擎设为启动
        self._active = True

        # 启动事件处理线程
        self._thread.start()

    def stop(self) -> None:
        """停止引擎"""
        # 将引擎设为停止
        self._active = False

        # 等待事件处理线程退出
        # self._thread.join()

    def register(self, event_type: EventType, handler) -> dict:
        """
        注册事件处理的函数监听
        """
        # 尝试获取该事件类型对应的处理函数队列
        try:
            handler_list = self._handlers[event_type]
        except Exception:
            self._handlers[event_type] = []
            handler_list = self._handlers[event_type]

        # 若要注册的处理函数不在该事件的处理函数列表中，则注册该事件
        if handler not in handler_list:
            handler_list.append(handler)
            self._handlers[event_type] = handler_list

        return self._handlers

    def withdraw(self, event_type: EventType, handler) -> dict:
        """注销事件处理函数监听"""
        # 尝试获取该事件类型对应的处理函数列表，若无则忽略该次注销请求
        handler_list = self._handlers[event_type]

        # 如果该函数存在于列表中，则移除
        if handler in handler_list:
            handler_list.remove(handler)

        # 如果函数列表为空，则从引擎中移除该事件类型
        if not handler_list:
            del self._handlers[event_type]

        return self._handlers

    def put(self, event: Event):
        """向事件队列中存入事件"""
        try:
            if self._handlers[event.event_type] is not None:
                self._event_queue.put(event)
        except Exception as e:
            gl.logger.error(
                f"There is no handler for {event}. Please check your configuration!  \n {e}"
            )

    def register_general_handler(self, handler) -> list:
        """注册通用事件处理函数监听"""
        if handler not in self._general_handlers:
            self._general_handlers.append(handler)
        return self._general_handlers

    def withdraw_general_handler(self, handler) -> list:
        """注销通用事件处理函数监听"""
        if handler in self._general_handlers:
            self._general_handlers.remove(handler)
        return self._general_handlers

    def register_next_day(self, func):
        """
        注册下一天的方法
        """
        self._next_day = func

    def feed(self, code: str, data: pd.DataFrame):
        """
        向价格信息池注入信息
        :param code:
        :param data: DataFrame格式的数据
        :return: void
        """
        # 1 如果没有，则建立新的K，V
        if code not in self._price_pool.keys():
            self._price_pool[code] = data

        # TODO 更新可能需要有个判断逻辑防止内存爆了

    def get_price(self, code: str, date: str) -> MarketEvent:
        """
        获取价格信息
        """
        # 1 如果池子里没有当前Code的价格信息，则从数据库获取该Code的全量数据
        if code not in self._price_pool.keys():
            df = gm.get_dayBar_by_mongo(code=code)
            self.feed(code, df)
        # 2 从价格池获取价格
        df = self._price_pool[code][self._price_pool[code]["date"] == date]
        # 3 如果数据库里没有数据，退出回
        if df.empty:
            gl.logger.error(f"试图获取一个不存在的数据 {date} {code}，退出回测")
            return None
        else:
            day_bar = DayBar(
                date=df.date,
                code=df.code,
                open_=df.open,
                high=df.high,
                low=df.low,
                close=df.close,
                pre_close=df.pre_close,
                volume=df.volume,
                amount=df.amount,
                adjust_flag=df.adjust_flag,
                turn=df.turn,
                pct_change=df["pct_change"],
                is_st=df.is_st,
            )
            market_event = MarketEvent(
                date=df.date,
                code=df.code,
                source="GM 历史数据",
                info_type=InfoType.DailyPrice,
                data=day_bar,
            )

            # 4 如果顺利获取到价格，则把价格信息推入info_queue
            self._info_queue.put(market_event)
            return market_event
