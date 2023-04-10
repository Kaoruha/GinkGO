class BaseEngine(object):
    def __init__(self, *args, **kwargs):
        self.__is_running = False

    @property
    def is_running(self) -> bool:
        return self.__is_running

    def start(self) -> None:
        self.is_running = True

    def pause(self) -> None:
        self.is_running = False

    def stop(self) -> None:
        self.is_running = False
