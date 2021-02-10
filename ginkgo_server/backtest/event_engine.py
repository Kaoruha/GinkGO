from threading import Thread
from ginkgo_server.backtest.enums import EventType, InfoType
from ginkgo_server.backtest.events import *
import queue
import time
import datetime
import pandas as pd


class EventEngine(object):
    """
    事件驱动引擎
    事件驱动引擎中所有的变量都设置为了私有，这是为了防止不小心
    从外部修改了这些变量的值或状态，导致bug。

    变量说明
    __queue：私有变量，事件队列
    __active：私有变量，事件引擎开关
    __thread：私有变量，事件处理线程
    __timer：私有变量，计时器
    __handlers：私有变量，事件处理函数字典


    方法说明
    __run: 私有方法，事件处理线程连续运行用
    __process: 私有方法，处理事件，调用注册在引擎中的监听函数
    __onTimer：私有方法，计时器固定事件间隔触发后，向事件队列中存入计时器事件
    start: 公共方法，启动引擎
    stop：公共方法，停止引擎
    register：公共方法，向引擎中注册监听函数
    unregister：公共方法，向引擎中注销监听函数
    put：公共方法，向事件队列中注入新的事件

    事件监听函数必须定义为输入参数仅为一个event对象，即：

    函数
    def func(event)
        ...

    对象方法
    def method(self, event)
        ...

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
        # 计时器，用于触发计时器事件
        # self.__timer = QTimer()
        # self.__timer.timeout.connect(self.__onTimer)

        # 这里的__handlers是一个字典，用来保存对应的事件调用关系
        # 其中每个键对应的值是一个列表，列表中保存了对该事件进行监听的函数功能
        # Key是事件类型，Value是用来处理的一系列函数
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

    # def __onTimer(self):
    #     """向事件队列中存入计时器事件"""
    #     # 创建计时器事件
    #     event = Event(type_=EVENT_TIMER)
    #
    #     # 向队列中存入计时器事件
    #     self.put(event)

    def start(self, timer=True):
        """
        引擎启动
        timer：是否要启动计时器 TODO 回头实盘引擎需要加入定时器定期获取数据处理数据
        """
        # 将引擎设为启动
        self.__active = True

        # 启动事件处理线程
        self.__thread.start()

        # 启动计时器，计时器事件间隔默认设定为1秒
        # if timer:
        #     self.__timer.start(1000)  # 这是设置时间定时器时间间隔的方法

    def stop(self):
        """停止引擎"""
        # 将引擎设为停止
        self.__active = False

        # 停止计时器
        # self.__timer.stop()

        # 等待事件处理线程退出
        self.__thread.join()

    def register(self, type_: EventType, handler):
        """
        注册事件处理的函数监听
        """
        # 尝试获取该事件类型对应的处理函数队列
        try:
            handler_list = self.__handlers[type_]
        except Exception as e:
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
            print(f"There is no handler for {event}. Please check your configuration!")

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
        for data_ in data.iterrows():
            market_event = MarketEvent(info_type=InfoType.DailyPrice, data=data_)
            self.__info_queue.put(market_event)
