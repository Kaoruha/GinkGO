class BaseSelector(object):
    def __init__(self, *args, **kwargs):
        self._portfolio = None

    def bind_portfolio(self, portfolio):
        self._portfolio = portfolio

    @property
    def portfolio(self):
        return self._portfolio

    def pick(self) -> list:
        r = []
        return r
