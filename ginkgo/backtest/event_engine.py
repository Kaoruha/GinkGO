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
    event drivern engine
    """

    def __init__(
        self,
        *,
        heartbeat: float = 0.001,
        timersleep: float = 1,
        is_timer_on: bool = false,
    ) -> none:
        self.__event_queue = queue.queue()  # 事件队列
        self.__info_queue = queue.queue()  # 信息队列
        self.active = false  # 事件引擎开关,引擎初始化时状态设置为关闭
        self.__thread = thread(target=self.__run)  # 事件处理线程
        self.__timer_thread = thread(target=self.__timer_run)  # 定时器处理线程
        self.heartbeat = heartbeat  # 心跳间隔
        self.timersleep = timersleep  # 定时器间隔
        self.__timer_on = is_timer_on
        self.__timer_handlers = []
        self.__handlers = {}  # 事件处理的回调函数
        self.__general_handlers = []  # 保存通用回调函数（所有事件均调用）
        self.__wait_count = 0
        self.__wait_time = 1
        self.__max_wait = 5
        self.__timer_limit = 0
        self.__timer_count = 0

    # active
    @property
    def active(self):
        return self.__active

    @active.setter
    def active(self, is_active: bool):
        self.active = is_active

    # hearbeat
    @property
    def heartbeat(self):
        return self.__heartbeat

    @heartbeat.setter
    def heartbeat(self, heartbeat: float):
        if heartbeat > 0:
            self.__heartbeat = heartbeat
            gl.logger.info(f"设置心跳间隔为「{heartbeat}s」")
        else:
            gl.logger.warning("heartbeat should bigger than 0")

    def set_timerlimit(self, limit: int) -> none:
        """
        设置计时器最大次数，不设置为0，无限
        """
        if limit <= 0:
            return
        self.__timer_limit = limit

    def __run(self) -> none:
        """
        引擎运行
        """
        while true:
            while self.active:
                try:
                    e = self.__event_queue.get(block=false)  # 获取消息的阻塞时间
                    self.__process(e)
                    self.__wait_count = 0
                    # 每个循环都会把一个事件带来的所有事件处理完再处理事件
                except queue.empty:
                    # 事件列表为空时，回测结束，live系统应该继续等待
                    self.__wait_count += 1

                    if self.__timer_on:
                        gl.logger.info(f"队列为空，等待事件推入第{self.__wait_count}次")

                        if self.__wait_count >= self.__max_wait:
                            if self.__timer_count >= self.__timer_limit:
                                break
                    else:
                        s = f"{self.__wait_count}/{self.__max_wait}"
                        gl.logger.info(f"队列为空，等待事件推入 第{s}次")
                        if self.__wait_count >= self.__max_wait:
                            break
            # 默认如果调用set_heartbeat设置心跳，不开启，但是可能cpu负荷过高
        if self.heartbeat > 0:
            time.sleep(self.heartbeat)

    def __timer_run(self) -> none:
        """
        定期运行
        """
        while self.active:
            self.__timer_count += 1
            if len(self._timer_handlers) > 0:
                [handler() for handler in self.__timer_handlers]

            time.sleep(self.timersleep)
            gl.logger.warn(f"timer loop {self.__timer_count}")

            if self.__timer_limit > 0:
                if self.__timer_count >= self.__timer_limit:
                    self.stop()

    def __process(self, event: event) -> none:
        """
        处理事件
        """
        # 检查是否存在对该事件进行监听的处理函数
        if event.event_type in self.__handlers:
            # 若存在，将事件传递给处理函数执行
            gl.logger.info(f"处理{event}")
            [handler(event) for handler in self.__handlers[event.event_type]]

            # 以上语句为python列表解析方式的写法，对应的常规循环写法为：
            # for handler in self.__handlers[event.type_]:
            #     handler(event)
        else:
            gl.logger.error(f"没有{event.event_type}对应的处理函数")

        # 调用通用处理函数进行处理
        if self._general_handlers:
            [handler(event) for handler in self.__general_handlers]

    def start(self) -> none:
        """
        引擎启动
        """
        # todo 回头实盘引擎需要加入定时器定期获取数据处理数据
        # 将引擎设为启动
        self.active = true

        # 启动事件处理线程
        self.__thread.start()

        # 启动定时处理线程
        if self.__timer_on:
            self.__timer_thread.start()

    def stop(self) -> none:
        """停止引擎"""
        # 将引擎设为停止
        self.active = false

        # 等待事件处理线程退出
        if self.__thread.is_alive():
            self.__thread.join()
        if self.__timer_thread.is_alive():
            self.__timer_thread.join()

    def pause(self) -> none:
        """
        暂停引擎
        """
        self.active = false

    def register(self, event_type: eventtype, handler) -> dict:
        """
        注册事件处理的函数监听
        """
        # 尝试获取该事件类型对应的处理函数队列
        try:
            handler_list = self.__handlers[event_type]
        except exception:
            self._handlers[event_type] = []
            handler_list = self.__handlers[event_type]

        # 若要注册的处理函数不在该事件的处理函数列表中，则注册该事件
        if handler not in handler_list:
            handler_list.append(handler)
            self._handlers[event_type] = handler_list

        return self._handlers

    def withdraw(self, event_type: eventtype, handler) -> dict:
        """注销事件处理函数监听"""
        # 尝试获取该事件类型对应的处理函数列表，若无则忽略该次注销请求
        handler_list = self.__handlers[event_type]

        # 如果该函数存在于列表中，则移除
        if handler in handler_list:
            handler_list.remove(handler)
        else:
            return self.__handlers

        # 如果函数列表为空，则从引擎中移除该事件类型
        if not handler_list:
            del self.__handlers[event_type]

        return self.__handlers

    def put(self, event: event) -> none:
        """
        向事件队列中存入事件
        """
        self.__event_queue.put(event)
        if event.event_type not in self.__handlers:
            gl.logger.warn(f"当前引擎没有{event.event_type}事件的处理函数")

    def register_general_handler(self, handler) -> list:
        """注册通用事件处理函数监听"""
        if handler not in self.__general_handlers:
            self.__general_handlers.append(handler)
        return self.__general_handlers

    def withdraw_general_handler(self, handler) -> list:
        """注销通用事件处理函数监听"""
        if handler in self.__general_handlers:
            self.__general_handlers.remove(handler)
        return self.__general_handlers

    def register_timer_handler(self, handler) -> list:
        """注册计时器事件处理函数监听"""
        if handler not in self.__timer_handlers:
            self.__timer_handlers.append(handler)
        return self.__timer_handlers

    def withdraw_timer_handler(self, handler) -> list:
        """注销计时器事件处理函数监听"""
        if handler in self.__timer_handlers:
            self.__timer_handlers.remove(handler)
        return self.__timer_handlers
