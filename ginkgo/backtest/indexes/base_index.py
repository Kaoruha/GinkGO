class BaseIndex(object):
    def __init__(self, name: str, *args, **kwargs):
        self._name = ""
        self._portfolio = None

    @property
    def name(self) -> str:
        return self._name

    def bind_portfolio(self, portfolio):
        self._portfolio = portfolio

    @property
    def portfolio(self):
        return self._portfolio

    @property
    def value(self) -> any:
        raise NotImplementedError()
