import unittest

from ginkgo.data.models import MTick
from ginkgo.backtest import Tick
from ginkgo.enums import TICKDIRECTION_TYPES


class OperationTickTest(unittest.TestCase):
    """
    UnitTest for Tick CRUD
    """

    def __init__(self, *args, **kwargs) -> None:
        super(OperationTickTest, self).__init__(*args, **kwargs)
        self.params = [
            {
                "code": "testcode001",
                "price": 10.1,
                "volume": 1000,
                "direction": TICKDIRECTION_TYPES.OTHER,
                "timestamp": "2020-01-01 10:00:01",
            },
            {
                "code": "testcode001",
                "price": 10.2,
                "volume": 1000,
                "direction": TICKDIRECTION_TYPES.OTHER,
                "timestamp": "2020-01-01 10:00:02",
            },
            {
                "code": "testcode001",
                "price": 10.3,
                "volume": 1000,
                "direction": TICKDIRECTION_TYPES.OTHER,
                "timestamp": "2020-01-01 10:00:03",
            },
            {
                "code": "testcode001",
                "price": 10.4,
                "volume": 1000,
                "direction": TICKDIRECTION_TYPES.OTHER,
                "timestamp": "2020-01-01 10:00:04",
            },
        ]

    def test_OperationTick_create(self) -> None:
        pass

    def test_OperationTick_bulkinsert(self) -> None:
        pass

    def test_OperationTick_update(self) -> None:
        pass

    def test_OperationTick_read(self) -> None:
        # in format ModelTick
        # in format dataframe
        pass

    def test_OperationTick_delete(self) -> None:
        pass

    def test_OperationTick_exists(self) -> None:
        pass

    def test_OperationTick_exceptions(self) -> None:
        pass
