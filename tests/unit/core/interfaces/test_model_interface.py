"""
模型接口单元测试

测试 IModel、ITimeSeriesModel、IEnsembleModel 接口定义，
验证构造、状态管理、超参数、训练记录、克隆等功能。
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np

from ginkgo.core.interfaces.model_interface import (
    ModelStatus,
    IModel,
    ITimeSeriesModel,
    IEnsembleModel,
)
from ginkgo.enums import MODEL_TYPES


# ── 具体实现用于测试抽象类 ──────────────────────────────────────────


class ConcreteModel(IModel):
    """IModel 的具体实现"""

    def fit(self, X, y=None, **kwargs):
        self.status = ModelStatus.TRAINED
        return self

    def predict(self, X, **kwargs):
        return np.array([1.0, 2.0])

    def set_hyperparameters(self, **hyperparams):
        self._hyperparameters.update(hyperparams)


class ConcreteTimeSeriesModel(ITimeSeriesModel):
    """ITimeSeriesModel 的具体实现"""

    def fit(self, X, y=None, **kwargs):
        self.status = ModelStatus.TRAINED
        return self

    def predict(self, X, **kwargs):
        return np.array([1.0])

    def set_hyperparameters(self, **hyperparams):
        self._hyperparameters.update(hyperparams)

    def predict_sequence(self, X, steps=None):
        return pd.DataFrame({"prediction": [1.0, 2.0, 3.0]})


class ConcreteEnsembleModel(IEnsembleModel):
    """IEnsembleModel 的具体实现"""

    def fit(self, X, y=None, **kwargs):
        self.status = ModelStatus.TRAINED
        return self

    def predict(self, X, **kwargs):
        return np.array([1.0])

    def set_hyperparameters(self, **hyperparams):
        self._hyperparameters.update(hyperparams)


# ── ModelStatus 枚举测试 ────────────────────────────────────────────


@pytest.mark.unit
class TestModelStatus:
    """ModelStatus 枚举测试"""

    def test_enum_values(self):
        """验证所有状态值"""
        assert ModelStatus.UNTRAINED.value == "untrained"
        assert ModelStatus.TRAINING.value == "training"
        assert ModelStatus.TRAINED.value == "trained"
        assert ModelStatus.DEPLOYED.value == "deployed"
        assert ModelStatus.DEPRECATED.value == "deprecated"

    def test_enum_member_count(self):
        """验证枚举成员数量"""
        assert len(ModelStatus) == 5


# ── IModel 构造测试 ─────────────────────────────────────────────────


@pytest.mark.unit
class TestIModelConstruction:
    """IModel 构造测试"""

    def test_default_construction(self):
        """默认参数构造"""
        model = ConcreteModel()
        assert model.name == "UnknownModel"
        assert model.status == ModelStatus.UNTRAINED
        assert model.version == "1.0.0"
        assert model.created_at is not None
        assert model.updated_at is not None

    def test_custom_name_and_type(self):
        """自定义名称和类型"""
        model = ConcreteModel(name="MyModel", model_type=MODEL_TYPES.TIME_SERIES)
        assert model.name == "MyModel"
        assert model.model_type == MODEL_TYPES.TIME_SERIES

    def test_initial_config_empty(self):
        """初始配置为空"""
        model = ConcreteModel()
        assert model.config == {}

    def test_initial_hyperparameters_empty(self):
        """初始超参数为空"""
        model = ConcreteModel()
        assert model.hyperparameters == {}

    def test_initial_training_history_empty(self):
        """初始训练历史为空"""
        model = ConcreteModel()
        assert model.training_history == []

    def test_initial_validation_metrics_empty(self):
        """初始验证指标为空"""
        model = ConcreteModel()
        assert model.validation_metrics == {}

    def test_initial_feature_names_empty(self):
        """初始特征名为空"""
        model = ConcreteModel()
        assert model.feature_names == []

    def test_initial_target_names_empty(self):
        """初始目标变量名为空"""
        model = ConcreteModel()
        assert model.target_names == []


# ── IModel 属性测试 ─────────────────────────────────────────────────


@pytest.mark.unit
class TestIModelProperties:
    """IModel 属性测试"""

    def test_is_trained_when_trained(self):
        """训练后 is_trained 为 True"""
        model = ConcreteModel()
        model.status = ModelStatus.TRAINED
        assert model.is_trained is True

    def test_is_trained_when_deployed(self):
        """部署后 is_trained 为 True"""
        model = ConcreteModel()
        model.status = ModelStatus.DEPLOYED
        assert model.is_trained is True

    def test_is_trained_when_untrained(self):
        """未训练时 is_trained 为 False"""
        model = ConcreteModel()
        assert model.is_trained is False

    def test_is_trained_when_training(self):
        """训练中 is_trained 为 False"""
        model = ConcreteModel()
        model.status = ModelStatus.TRAINING
        assert model.is_trained is False


# ── IModel 超参数测试 ───────────────────────────────────────────────


@pytest.mark.unit
class TestIModelHyperparameters:
    """IModel 超参数管理测试"""

    def test_set_hyperparameters(self):
        """设置超参数"""
        model = ConcreteModel()
        model.set_hyperparameters(learning_rate=0.01, epochs=100)
        assert model.hyperparameters["learning_rate"] == 0.01
        assert model.hyperparameters["epochs"] == 100

    def test_get_hyperparameter(self):
        """获取超参数"""
        model = ConcreteModel()
        model.set_hyperparameters(learning_rate=0.01)
        assert model.get_hyperparameter("learning_rate") == 0.01

    def test_get_hyperparameter_default(self):
        """获取不存在的超参数返回默认值"""
        model = ConcreteModel()
        assert model.get_hyperparameter("nonexistent", 0.5) == 0.5

    def test_validate_hyperparameters_default_true(self):
        """默认超参数验证返回 True"""
        model = ConcreteModel()
        assert model.validate_hyperparameters() is True


# ── IModel 训练和预测测试 ───────────────────────────────────────────


@pytest.mark.unit
class TestIModelTraining:
    """IModel 训练和预测测试"""

    def test_fit_sets_trained_status(self):
        """训练后状态变为 TRAINED"""
        model = ConcreteModel()
        X = pd.DataFrame({"feature": [1, 2, 3]})
        model.fit(X)
        assert model.status == ModelStatus.TRAINED

    def test_fit_returns_self(self):
        """fit 返回自身实例"""
        model = ConcreteModel()
        X = pd.DataFrame({"feature": [1, 2, 3]})
        result = model.fit(X)
        assert result is model

    def test_predict_returns_result(self):
        """predict 返回预测结果"""
        model = ConcreteModel()
        X = pd.DataFrame({"feature": [1, 2, 3]})
        result = model.predict(X)
        assert len(result) == 2

    def test_predict_proba_not_implemented(self):
        """默认不支持概率预测"""
        model = ConcreteModel()
        X = pd.DataFrame({"feature": [1, 2, 3]})
        with pytest.raises(NotImplementedError, match="不支持概率预测"):
            model.predict_proba(X)


# ── IModel 状态和记录测试 ───────────────────────────────────────────


@pytest.mark.unit
class TestIModelStateManagement:
    """IModel 状态管理测试"""

    def test_update_status(self):
        """更新模型状态"""
        model = ConcreteModel()
        model.update_status(ModelStatus.TRAINING)
        assert model.status == ModelStatus.TRAINING
        assert model.updated_at is not None

    def test_add_training_record(self):
        """添加训练记录"""
        model = ConcreteModel()
        model.add_training_record({"loss": 0.5, "accuracy": 0.9}, epoch=1)
        assert len(model.training_history) == 1
        record = model.training_history[0]
        assert record["metrics"]["loss"] == 0.5
        assert record["epoch"] == 1
        assert "timestamp" in record

    def test_add_training_record_without_epoch(self):
        """不带 epoch 的训练记录"""
        model = ConcreteModel()
        model.add_training_record({"loss": 0.3})
        assert "epoch" not in model.training_history[0]

    def test_set_validation_metrics(self):
        """设置验证指标"""
        model = ConcreteModel()
        model.set_validation_metrics({"accuracy": 0.95, "f1": 0.92})
        assert model.validation_metrics["accuracy"] == 0.95
        assert model.validation_metrics["f1"] == 0.92

    def test_get_feature_importance_default_none(self):
        """默认特征重要性为 None"""
        model = ConcreteModel()
        assert model.get_feature_importance() is None


# ── IModel 克隆测试 ─────────────────────────────────────────────────


@pytest.mark.unit
class TestIModelClone:
    """IModel 克隆测试"""

    def test_clone_creates_new_instance(self):
        """克隆创建新实例"""
        model = ConcreteModel(name="Original")
        cloned = model.clone()
        assert cloned is not model
        assert cloned.name == "Original_clone"

    def test_clone_preserves_config(self):
        """克隆保留配置"""
        model = ConcreteModel()
        model.set_hyperparameters(lr=0.01)
        cloned = model.clone()
        assert cloned.hyperparameters["lr"] == 0.01

    def test_clone_is_independent(self):
        """克隆独立于原始模型"""
        model = ConcreteModel()
        model.set_hyperparameters(lr=0.01)
        cloned = model.clone()
        cloned.set_hyperparameters(lr=0.02)
        assert model.hyperparameters["lr"] == 0.01


# ── IModel 元数据和字符串测试 ───────────────────────────────────────


@pytest.mark.unit
class TestIModelMetadata:
    """IModel 元数据测试"""

    def test_get_metadata_keys(self):
        """元数据包含必要字段"""
        model = ConcreteModel(name="TestModel")
        metadata = model.get_metadata()
        assert metadata["name"] == "TestModel"
        assert "model_type" in metadata
        assert "status" in metadata
        assert "version" in metadata
        assert "created_at" in metadata
        assert "updated_at" in metadata
        assert "is_trained" in metadata
        assert "feature_count" in metadata
        assert "target_count" in metadata
        assert "hyperparameters" in metadata
        assert "validation_metrics" in metadata

    def test_str_representation(self):
        """字符串表示"""
        model = ConcreteModel(name="TestModel")
        s = str(model)
        assert "TestModel" in s

    def test_repr_equals_str(self):
        """repr 与 str 相同"""
        model = ConcreteModel()
        assert repr(model) == str(model)


# ── ITimeSeriesModel 测试 ───────────────────────────────────────────


@pytest.mark.unit
class TestITimeSeriesModel:
    """时序模型接口测试"""

    def test_default_sequence_length(self):
        """默认序列长度"""
        model = ConcreteTimeSeriesModel()
        assert model.sequence_length == 60

    def test_default_prediction_horizon(self):
        """默认预测步长"""
        model = ConcreteTimeSeriesModel()
        assert model.prediction_horizon == 1

    def test_set_sequence_config(self):
        """设置序列配置"""
        model = ConcreteTimeSeriesModel()
        model.set_sequence_config(30, 5)
        assert model.sequence_length == 30
        assert model.prediction_horizon == 5

    def test_default_model_type(self):
        """默认模型类型为时序"""
        model = ConcreteTimeSeriesModel()
        assert model.model_type == MODEL_TYPES.TIME_SERIES

    def test_predict_sequence(self):
        """序列预测"""
        model = ConcreteTimeSeriesModel()
        X = pd.DataFrame({"close": [1, 2, 3, 4, 5]})
        result = model.predict_sequence(X, steps=3)
        assert isinstance(result, pd.DataFrame)

    def test_inherits_from_imodel(self):
        """继承 IModel"""
        assert issubclass(ITimeSeriesModel, IModel)


# ── IEnsembleModel 测试 ─────────────────────────────────────────────


@pytest.mark.unit
class TestIEnsembleModel:
    """集成模型接口测试"""

    def test_initial_empty(self):
        """初始无基础模型"""
        model = ConcreteEnsembleModel()
        assert model.base_models == []
        assert model.weights == []

    def test_add_base_model(self):
        """添加基础模型"""
        model = ConcreteEnsembleModel()
        base = ConcreteModel(name="Base1")
        model.add_base_model(base, weight=0.5)
        assert len(model.base_models) == 1
        assert model.weights == [0.5]

    def test_remove_base_model(self):
        """移除基础模型"""
        model = ConcreteEnsembleModel()
        base = ConcreteModel(name="Base1")
        model.add_base_model(base)
        model.remove_base_model(0)
        assert len(model.base_models) == 0

    def test_remove_invalid_index_no_error(self):
        """移除无效索引不报错"""
        model = ConcreteEnsembleModel()
        model.remove_base_model(0)  # 空列表，不应抛出异常

    def test_set_weights_correct_count(self):
        """设置正确数量的权重"""
        model = ConcreteEnsembleModel()
        model.add_base_model(ConcreteModel())
        model.add_base_model(ConcreteModel())
        model.set_weights([0.7, 0.3])
        assert model.weights == [0.7, 0.3]

    def test_set_weights_wrong_count_raises(self):
        """权重数量不匹配抛出异常"""
        model = ConcreteEnsembleModel()
        model.add_base_model(ConcreteModel())
        with pytest.raises(ValueError, match="权重数量"):
            model.set_weights([0.5, 0.5])

    def test_normalize_weights(self):
        """权重归一化"""
        model = ConcreteEnsembleModel()
        model.add_base_model(ConcreteModel())
        model.add_base_model(ConcreteModel())
        model.set_weights([3.0, 1.0])
        model.normalize_weights()
        assert abs(model.weights[0] - 0.75) < 1e-6
        assert abs(model.weights[1] - 0.25) < 1e-6

    def test_normalize_zero_weights(self):
        """零权重归一化不变"""
        model = ConcreteEnsembleModel()
        model.add_base_model(ConcreteModel())
        model.set_weights([0.0])
        model.normalize_weights()
        assert model.weights == [0.0]

    def test_inherits_from_imodel(self):
        """继承 IModel"""
        assert issubclass(IEnsembleModel, IModel)
