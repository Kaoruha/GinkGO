import time
import queue
import datetime
import pandas as pd
from threading import Thread
from ginkgo.backtest.enums import EventType, InfoType
from ginkgo.backtest.events import MarketEvent
from ginkgo.backtest.price import DayBar


class EventEngine(object):
    """
    事件驱动引擎

    """

    def __init__(self, *, heartbeat: float = 0):
        """
        初始化事件引擎
        """
        # 事件队列
        self.__event_queue = queue.Queue()

        # 信息队列
        self.__info_queue = queue.Queue()

        # 事件引擎开关
        self.__active = False  # 引擎初始化时状态设置为关闭

        # 事件处理线程
        self.__thread = Thread(target=self.__run)
        # self.__feed_thread = Thread(target=self.__feed)

        # 设置心跳时间
        self.heartbeat = heartbeat
        self.__handlers = {}

        # __general_handlers是一个列表，与__handlers类似，用来保存通用回调函数（所有事件均调用）
        self.__general_handlers = []

    def set_heartbeat(self, heartbeat: float):
        """
        设置心跳的间隔
        """
        if heartbeat > 0:
            self.heartbeat = heartbeat
        else:
            print("heartbeat should bigger than 0")

    def __run(self):
        """引擎运行"""
        while self.__active:
            try:
                info = self.__info_queue.get(block=False)  # 获取消息的阻塞时间
                self.__process(info)
                # 先处理信息事件，一个信息事件可能产生N个事件
                # 每个循环都会把一个信息事件带来的所有事件处理完再处理下一个信息事件
            except queue.Empty:
                # 事件列表为空时，输出现在的时间
                now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"\rData_list is Empty!! {now}", end="")
                return
            # 处理事件列表
            while True:
                try:
                    event = self.__event_queue.get(False)
                    self.__process(event)  # 处理事件列表
                except queue.Empty:
                    break
            # 当心跳不为0时，事件引擎会短暂停歇，默认如果调用set_heartbeat设置心跳，不开启，但是可能CPU负荷过高
            if self.heartbeat != 0:
                time.sleep(self.heartbeat)

    def __process(self, event):
        """处理事件"""
        # 检查是否存在对该事件进行监听的处理函数
        if event.type_ in self.__handlers:
            # 若存在，将事件传递给处理函数执行
            [handler(event) for handler in self.__handlers[event.type_]]

            # 以上语句为Python列表解析方式的写法，对应的常规循环写法为：
            # for handler in self.__handlers[event.type_]:
            #     handler(event)
        else:
            print(f"没有{event.type_}对应的处理函数")

        # 调用通用处理函数进行处理
        if self.__general_handlers:
            [handler(event) for handler in self.__general_handlers]

    def start(self):
        """
        引擎启动
        """
        # TODO 回头实盘引擎需要加入定时器定期获取数据处理数据
        # 将引擎设为启动
        self.__active = True

        # 启动事件处理线程
        self.__thread.start()

    def stop(self):
        """停止引擎"""
        # 将引擎设为停止
        self.__active = False

        # 等待事件处理线程退出
        self.__thread.join()

    def register(self, type_: EventType, handler):
        """
        注册事件处理的函数监听
        """
        # 尝试获取该事件类型对应的处理函数队列
        try:
            handler_list = self.__handlers[type_]
        except Exception:
            self.__handlers[type_] = []
            handler_list = self.__handlers[type_]

        # 若要注册的处理函数不在该事件的处理函数列表中，则注册该事件
        if handler not in handler_list:
            handler_list.append(handler)
            self.__handlers[type_] = handler_list

    def withdraw(self, type_: EventType, handler):
        """注销事件处理函数监听"""
        # 尝试获取该事件类型对应的处理函数列表，若无则忽略该次注销请求
        handler_list = self.__handlers[type_]

        # 如果该函数存在于列表中，则移除
        if handler in handler_list:
            handler_list.remove(handler)

        # 如果函数列表为空，则从引擎中移除该事件类型
        if not handler_list:
            del self.__handlers[type_]

    def put(self, event):
        """向事件队列中存入事件"""
        try:
            if self.__handlers[event.type_] is not None:
                self.__event_queue.put(event)
        except Exception as e:
            print(
                f"There is no handler for {event}. Please check your configuration!  \n {e}"
            )

    def register_general_handler(self, handler):
        """注册通用事件处理函数监听"""
        if handler not in self.__general_handlers:
            self.__general_handlers.append(handler)

    def withdraw_general_handler(self, handler):
        """注销通用事件处理函数监听"""
        if handler in self.__general_handlers:
            self.__general_handlers.remove(handler)

    def feed(self, data: pd.DataFrame):
        """
        给引擎喂批量数据
        :param data: DataFrame格式的数据
        :return: void
        """
        for i, r in data.iterrows():
            day_bar = DayBar(
                date=r.date,
                code=r.code,
                open_=r.open,
                high=r.high,
                low=r.low,
                close=r.close,
                pre_close=r.pre_close,
                volume=r.volume,
                amount=r.amount,
                adjust_flag=r.adjust_flag,
                turn=r.turn,
                pct_change=r["pct_change"],
                is_st=r.is_st,
            )
            market_event = MarketEvent(
                date=r.date,
                code=r.code,
                source="GM 历史数据",
                info_type=InfoType.DailyPrice,
                data=day_bar,
            )
            self.__info_queue.put(market_event)
