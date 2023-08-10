class GinkgoSourceBase(object):
    def __init__(self, *args, **kwargs):
        self._client = None

    @property
    def client(self):
        return self._client

    def connect(self):
        raise NotImplementedError()
