"""
TDD tests for BaseMongoCRUD._get_collection None check (#5557)。

#5557: GinkgoMongo.get_collection() 连接失败时按降级契约返回 None（docstring 明示
"调用方应检查"），但 BaseMongoCRUD._get_collection() 直接透传 None 给 CRUD 方法，
导致 .find_one()/.insert_one() 等对 None 调用 → AttributeError 而非有意义的连接错误。

修复：_get_collection() 在 driver 返 None 时抛 ConnectionError（含 collection 名），
让调用方收到明确的"MongoDB 不可用"信号而非误导性的 AttributeError。
"""

import os

os.environ["GINKGO_SKIP_DEBUG_CHECK"] = "1"

import pytest
from unittest.mock import MagicMock

from ginkgo.data.crud.base_mongo_crud import BaseMongoCRUD


class _FakeModel:
    """最小 model 替身：只需 get_collection_name()（_get_collection 的唯一 model 依赖）。"""

    @classmethod
    def get_collection_name(cls) -> str:
        return "test_collection"


def _make_crud(driver_return):
    """构造 BaseMongoCRUD 实例，driver.get_collection 返回 driver_return。"""
    driver = MagicMock()
    driver.get_collection.return_value = driver_return
    return BaseMongoCRUD(model_class=_FakeModel, driver=driver)


@pytest.mark.unit
class TestGetCollectionNoneCheck:
    def test_raises_connection_error_when_driver_returns_none(self):
        """#5557: driver 连接失败返 None 时，_get_collection 应抛 ConnectionError 而非透传 None。

        旧行为：透传 None → CRUD 方法 None.find_one() → AttributeError（误导性，看不出是连接问题）。
        """
        crud = _make_crud(None)
        with pytest.raises(ConnectionError, match="test_collection"):
            crud._get_collection()

    def test_returns_collection_when_driver_available(self):
        """正常路径：driver 返 collection 时透传，None check 不破坏正常流程。"""
        collection = MagicMock(name="collection")
        crud = _make_crud(collection)
        assert crud._get_collection() is collection
