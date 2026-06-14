# Upstream: tests/unit/data/mappers/（ADR-010 Mapper TDD）
# Downstream: ginkgo.data.mappers.MappingMapper
# Role: MappingMapper from_model（带 mapping_type 形参）+ 智能左右键检测 + 批量

import pytest

from ginkgo.data.mappers import MappingMapper
from ginkgo.data.models import MStockInfo
from ginkgo.entities import Mapping


class _FakeMappingModel:
    """模拟映射模型：携带 portfolio_id + file_id 两个映射键字段（智能检测）。

    不依赖具体 M* 映射表（项目映射模型分散），用最小假对象验证智能检测逻辑。
    """

    def __init__(self, portfolio_id="", file_id="", uuid="u-123"):
        self.portfolio_id = portfolio_id
        self.file_id = file_id
        self.uuid = uuid


class TestMappingMapperFromModel:
    def test_from_model_returns_mapping_with_mapping_type(self):
        """from_model 必传 mapping_type 形参（决定映射语义）。"""
        model = _FakeMappingModel(portfolio_id="p-1", file_id="f-1")
        mapping = MappingMapper.from_model(model, mapping_type="PortfolioFile")
        assert isinstance(mapping, Mapping)
        assert mapping.mapping_type == "PortfolioFile"

    def test_from_model_smart_detects_left_right_keys(self):
        """智能检测：遍历 potential_keys，第一个非空为 left，第二个为 right。"""
        model = _FakeMappingModel(portfolio_id="p-1", file_id="f-2")
        mapping = MappingMapper.from_model(model, mapping_type="PortfolioFile")
        assert mapping.left_key == "p-1"
        assert mapping.right_key == "f-2"

    def test_from_model_default_mapping_type_when_empty(self):
        """mapping_type 空串时回退到类名推断（原码 cls.__name__.replace('Mapping','')）。"""
        model = _FakeMappingModel(portfolio_id="p-1", file_id="f-2")
        mapping = MappingMapper.from_model(model, mapping_type="")
        # Mapping.__name__ = "Mapping" → replace 后空串
        assert isinstance(mapping, Mapping)

    def test_from_model_empty_keys_raises_valueerror(self):
        """已知 bug：模型两键都空时，from_model 走 left_key or ""=空串传构造器，
        触发 Mapping.__init__ 校验 ValueError。忠实搬运保留（原码 left_key or ""
        是 None→"" 兜底，但空串仍被构造器拒）。留后续 issue。
        """
        model = _FakeMappingModel(portfolio_id="", file_id="")
        with pytest.raises(ValueError):
            MappingMapper.from_model(model, mapping_type="Test")

    def test_from_models_batch(self):
        model = _FakeMappingModel(portfolio_id="p-1", file_id="f-1")
        mappings = MappingMapper.from_models([model, model], mapping_type="PF")
        assert len(mappings) == 2
        assert all(isinstance(m, Mapping) for m in mappings)


class TestMappingMapperToModel:
    def test_to_model_not_implemented(self):
        """原码无 to_model（Mapping 只读，无写路径）。忠实搬运 NotImplementedError。"""
        with pytest.raises(NotImplementedError):
            MappingMapper.to_model(Mapping(left_key="a", right_key="b", mapping_type="t"))
