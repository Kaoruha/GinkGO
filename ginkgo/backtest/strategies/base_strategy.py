"""
基础策略

生存第一
生存第一
生存第一
生存第一


"""

class BaseStrategy(object):
    """
    策略基类

    定义一些策略的基本方法
    """
    def check(self, data):
        self.data = data