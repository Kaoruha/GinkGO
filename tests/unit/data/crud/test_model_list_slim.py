"""ModelList 瘦身测试（ADR-010 Phase 4 Task 4.1）。

验证 ModelList 删除懒转换链路 to_entities/to_entity 后：
- to_dataframe() 保留（唯一保留的转换 API）
- to_entities/to_entity 删除（斩断 _convert_to_business_objects hook 调用方）
- 7 个 DataFrame 模拟方法（first/count/filter/empty/shape/head/tail）删除（dead code）
- _business_objects_cache 懒转换缓存属性删除
"""

from ginkgo.data.crud.model_conversion import ModelList, ModelConversion


def test_modellist_keeps_to_dataframe():
    """to_dataframe() 是保留的唯一转换方法。"""
    assert hasattr(ModelList, "to_dataframe")


def test_modellist_drops_to_entities():
    """to_entities() 删除（懒转换入口）。"""
    assert not hasattr(ModelList, "to_entities")


def test_modellist_drops_to_entity():
    """ModelConversion.to_entity() 删除（单实体懒转换入口）。"""
    assert not hasattr(ModelConversion, "to_entity")


def test_modellist_drops_df_simulators():
    """无调用方的 DataFrame 模拟方法删除（dead code）。

    保留项（有真实业务调用方，本任务不删）：
    - first(): broker_instance_crud.get_broker_by_portfolio /
      user_credential_crud.get_by_user_id / notification_recipient_crud.get_by_name
    - head(): user_group_service.fuzzy_search_groups /
      user_service.fuzzy_search_users（fuzzy_search 返 ModelList）
    - count(): list 内置原生方法（list.count(value)），无法从继承链移除

    删除项（无 ModelList 真实调用方）：
    - filter / empty / shape / tail
    """
    for dead in ("filter", "empty", "shape", "tail"):
        assert not hasattr(ModelList, dead), f"ModelList.{dead} 应删除（dead code）"


def test_modellist_count_is_list_builtin_not_custom():
    """ModelList.count 必须是 list 内置（签名 count(value)），而非已删的自定义无参 count(self)。"""
    import inspect
    sig = inspect.signature(ModelList.count)
    params = [p for p in sig.parameters if p != "self"]
    assert len(params) == 1, f"count 应为 list 内置 count(value)，实际签名: {sig}"


def test_modellist_drops_business_objects_cache():
    """懒转换缓存属性 _business_objects_cache 删除（不再有懒计算路径）。"""
    ml = ModelList([], None)
    assert not hasattr(ml, "_business_objects_cache")
