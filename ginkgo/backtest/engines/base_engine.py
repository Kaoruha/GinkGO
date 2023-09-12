class BaseEngine(object):
    def __init__(self, name: str = "BaseEngine", *args, **kwargs):
        self._active: bool = False
        self._name = ""
        self.set_name(name)

    @property
    def is_active(self) -> bool:
        return self._active

    @property
    def name(self) -> str:
        return self._name

    def start(self) -> None:
        self._active = True

    def pause(self) -> None:
        self._active = False

    def stop(self) -> None:
        self._active = False

    def __repr__(self) -> str:
        return self.name

    def set_name(self, name: str):
        self._name = name
