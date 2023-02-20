import abc
import datetime


class DataHandler(abc.ABC):
    """
    DataHandler is used for getting price infomation and feed them to engine.
    At leat contains SimHandler and Realtimehandler.
    """

    __metaclass__ = abc.ABCMeta

    @property
    def now(self):
        if self.calendar == None:
            return None
        return self.calendar[self.now_index]

    def __init__(self, first_day: datetime.datetime):
        self.cache = None
        self.calendar = None
        self.now_index = 0
        # TODO Cal the index accroding the param first_day

    @abc.abstractmethod
    def get_latest(self):
        raise NotImplementedError("Should implement func: get_latest_bars()")

    @abc.abstractmethod
    def update_bars(self, data, N=1):
        raise NotImplementedError("Should implement func: update_bars()")

    def next(self):
        # TODO go to the next day
        pass
