from .base_matchmaking import MatchMakingBase


class MatchMakingLive(MatchMakingBase):
    # The class with this __abstract__  will rebuild the class from bytes.
    # If not run time function will pass the class.
    __abstract__ = False
    pass
