"""
性能: 待测
"""

# Upstream: BaseMongoCRUD (继承)
# Downstream: None (单元测试)
# Role: BaseMongoCRUD update/modify 输入突变防护测试 (#5564)
#
# 验证 update_dict / updates 不被原地 setdefault("update_at") 污染：
# caller 复用同一 dict 批量调用，不会累积 stale 字段。


from unittest.mock import MagicMock

from ginkgo.data.crud.base_mongo_crud import BaseMongoCRUD
from ginkgo.data.models.model_mongobase import MMongoBase


class _ConcreteMongoCRUD(BaseMongoCRUD):
    """最小具体子类：满足 __init_subclass__ 的 _model_class 要求，
    override _get_collection 返回注入的 mock collection，绕过真实 driver。"""

    _model_class = MMongoBase

    def __init__(self, collection):
        super().__init__(MMongoBase, MagicMock())
        self._collection = collection

    def _get_collection(self):
        return self._collection


def test_update_does_not_mutate_caller_update_dict():
    """update() 自动补 update_at 时，不应污染 caller 传入的 update_dict。"""
    collection = MagicMock()
    collection.update_one.return_value = MagicMock(modified_count=1)
    crud = _ConcreteMongoCRUD(collection)

    caller_dict = {"name": "updated"}
    crud.update("some-uuid", caller_dict)

    # caller 的原 dict 保持纯净，未被加上 update_at
    assert "update_at" not in caller_dict
    # 传给 MongoDB 的 $set 仍应包含自动补的 update_at
    set_doc = collection.update_one.call_args[0][1]["$set"]
    assert "update_at" in set_doc


def test_modify_does_not_mutate_caller_updates():
    """modify() 自动补 update_at 时，不应污染 caller 传入的 updates dict。"""
    collection = MagicMock()
    collection.update_many.return_value = MagicMock(modified_count=2)
    crud = _ConcreteMongoCRUD(collection)

    caller_updates = {"status": "active"}
    crud.modify({"category": "x"}, caller_updates)

    assert "update_at" not in caller_updates
    set_doc = collection.update_many.call_args[0][1]["$set"]
    assert "update_at" in set_doc


def test_same_dict_reused_across_updates_keeps_caller_pure():
    """验收第2条：同一 dict 被多次 update 复用，caller dict 不累积 stale update_at。"""
    collection = MagicMock()
    collection.update_one.return_value = MagicMock(modified_count=1)
    crud = _ConcreteMongoCRUD(collection)

    shared = {"name": "x"}
    crud.update("u1", shared)
    crud.update("u2", shared)
    crud.update("u3", shared)

    # caller 的 shared dict 三次调用后仍只有原始 key，不累积 update_at
    assert set(shared.keys()) == {"name"}
