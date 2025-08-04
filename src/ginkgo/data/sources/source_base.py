class GinkgoSourceBase(object):
    def __init__(self, *args, **kwargs):
        self._client = None

    @property
    def client(self):
        return self._client

    @client.setter
    def client(self, value) -> None:
        self._client = value

    def connect(self, *args, **kwargs):
        raise NotImplementedError()
