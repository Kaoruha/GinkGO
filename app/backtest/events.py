"""
事件类
定义不同种类的事件
"""

from app.libs.enums import EventType

class MarketEvent(object):
    def __init__(self):
        self.type = EventType.Market

class SignalEvent(object):
    def __init__(self):
        self.type = EventType.Signal

class OrderEvent(object):
    def __init__(self):
        self.type = EventType.Order

class FillEvent(object):
    def __init__(self):
        self.type = EventType.Fill