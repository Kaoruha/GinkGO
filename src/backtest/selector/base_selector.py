"""
选股模块的基类
"""


class BaseSelector(object):
    def __init__(self, name='基础筛选器', *args, **kwargs):
        self._name = name

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    def get_result(self, today: str) -> []:
        """
        返回需要查看的股票代码
        """
        return []
        # raise NotImplementedError("Must implement get_result()")
