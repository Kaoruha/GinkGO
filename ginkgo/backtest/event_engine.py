import time
import queue
import datetime
import pandas as pd
from threading import Thread
from ginkgo.backtest.enums import EventType
from ginkgo.data.ginkgo_mongo import ginkgo_mongo as gm
from ginkgo.backtest.events import Event, MarketEvent
from ginkgo.backtest.price import Bar
from ginkgo.libs import GINKGOLOGGER as gl


class EventEngine(object):
    """
    事件驱动引擎

    """

    def __init__(
        self,
        *,
        heartbeat: float = 0.0,
        timersleep: float = 0.0,
        is_timer_on: bool = False,
    ) -> None:
        """
        初始化
        """
        self._event_queue = queue.Queue()  # 事件队列
        self._info_queue = queue.Queue()  # 信息队列
        self._active = False  # 事件引擎开关,引擎初始化时状态设置为关闭
        self._thread = Thread(target=self.__run)  # 事件处理线程
        self._timer_thread = Thread(target=self.__timer_run)  # 定时器处理线程
        self.heartbeat = heartbeat  # 心跳间隔
        self.timersleep = timersleep  # 定时器间隔
        self._timer_on = is_timer_on
        self._timer_handlers = []
        self._handlers = {}  # 事件处理的回调函数
        self._general_handlers = (
            []
        )  # __general_handlers是一个列表，与__handlers类似，用来保存通用回调函数（所有事件均调用）

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
        """
        引擎运行
        """
        while self._active:
            try:
                e = self._event_queue.get(block=False)  # 获取消息的阻塞时间
                self.__process(e)
                # 每个循环都会把一个事件带来的所有事件处理完再处理事件
            except queue.Empty:
                # 事件列表为空时，回测结束，Live系统应该继续等待
                gl.logger.info("回测结束")
                break
            # 当心跳不为0时，事件引擎会短暂停歇，默认如果调用set_heartbeat设置心跳，不开启，但是可能CPU负荷过高
            time.sleep(self.heartbeat)

    def __timer_run(self) -> None:
        """
        定期运行
        """
        while self.__active:
            if len(self._timer_handlers) > 0:
                [handler for handler in self._timer_handlers]
                time.sleep(self.timersleep)
            else:
                time.sleep(10)

    def __process(self, event: Event) -> None:
        """
        处理事件
        """
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

        # 启动定时处理线程
        if self._timmer_on:
            self._timer_thread.start()

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

    def put(self, event: Event) -> None:
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

    def register_timer_handler(self, handler) -> list:
        """注册计时器事件处理函数监听"""
        if handler not in self._timer_handlers:
            self._timer_handlers.append(handler)
        return self._timmer_handlers

    def withdraw_timer_handler(self, handler) -> list:
        """注销计时器事件处理函数监听"""
        if handler in self._timer_handlers:
            self._timer_handlers.remove(handler)
        return self._timmer_handlers
