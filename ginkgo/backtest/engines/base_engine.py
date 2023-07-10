class BaseEngine(object):
    def __init__(self, *args, **kwargs):
        self._active: bool = False

    @property
    def is_active(self) -> bool:
        return self._active

    def start(self) -> None:
        self._active = True

    def pause(self) -> None:
        self._active = False

    def stop(self) -> None:
        self._active = False
