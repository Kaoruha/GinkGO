from ginkgo.enums import RECRODSTAGE_TYPES


class BaseIndex(object):
    def __init__(self, name: str, *args, **kwargs):
        self._name = name
        self._active_stage = RECRODSTAGE_TYPES.NEWDAY
        self._portfolio = None

    @property
    def portfolio(self):
        return self._portfolio

    @property
    def active_stage(self) -> RECRODSTAGE_TYPES:
        return self._active_stage

    def bind_portfolio(self, portfolio, *args, **kwargs):
        self._portfolio = portfolio

    @property
    def name(self) -> str:
        return self._name

    def record(self, *args, **kwargs) -> None:
        raise NotImplemented

    @property
    def value(self) -> any:
        return "Should be overwrite the value property"
