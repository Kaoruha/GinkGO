import abc


class DataHandler(abc.ABC):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def get_latest_bars(self, data, N=1):
        raise NotImplementedError("Should implement func: get_latest_bars()")

    @abc.abstractmethod
    def update_bars(self, data, N=1):
        raise NotImplementedError("Should implement func: update_bars()")
