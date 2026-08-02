import inspect
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from ginkgo.data.services.factor_service import FactorService


def _model_list(rows, dataframe=None):
    """构造 list 形态 CRUD 结果。

    ADR-029 §Decision 9：CRUD 直接返 list，service 调 ``models_to_dataframe`` 走
    ``__table__`` 反射。原 ``crud._convert_models_to_dataframe`` 桩已失效——若需
    控制 DF 输出，调用方应直接 ``patch models_to_dataframe``。
    """
    return list(rows)


@pytest.fixture
def factor_crud():
    return MagicMock()


@pytest.fixture
def service(factor_crud):
    with patch("ginkgo.libs.GLOG"):
        return FactorService(factor_crud=factor_crud)


class TestFactorServiceDfContract:
    def test_get_factors_by_entity_returns_stable_modellist_contract(self, service, factor_crud):
        factors = _model_list([MagicMock(), MagicMock()])
        factor_crud.get_factors_by_entity.return_value = factors

        result = service.get_factors_by_entity(entity_type=1, entity_id="000001.SZ")

        assert result.success is True
        assert result.data["factors"] is factors
        assert result.data["count"] == 2

    def test_get_factors_by_entity_empty_modellist_count_zero(self, service, factor_crud):
        factors = _model_list([])
        factor_crud.get_factors_by_entity.return_value = factors

        result = service.get_factors_by_entity(entity_type=1, entity_id="missing")

        assert result.success is True
        assert result.data["factors"] is factors
        assert result.data["count"] == 0

    def test_calculate_factor_correlation_consumes_modellist_dataframe_contract(self, service, factor_crud):
        df_a = pd.DataFrame(
            [
                {"timestamp": "2024-01-01", "entity_id": "A", "factor_name": "momentum", "factor_value": 1.0},
                {"timestamp": "2024-01-02", "entity_id": "A", "factor_name": "momentum", "factor_value": 2.0},
            ]
        )
        df_b = pd.DataFrame(
            [
                {"timestamp": "2024-01-01", "entity_id": "B", "factor_name": "momentum", "factor_value": 2.0},
                {"timestamp": "2024-01-02", "entity_id": "B", "factor_name": "momentum", "factor_value": 4.0},
            ]
        )
        factor_crud.get_factors_by_entity.side_effect = [
            _model_list([MagicMock(), MagicMock()]),
            _model_list([MagicMock(), MagicMock()]),
        ]

        # ADR-029 §Decision 9：service 直接调 ``models_to_dataframe`` 走反射；
        # 测试需控制 DF 输出时直接 patch 此函数（不再能经 crud_stub 桩）。
        with patch(
            "ginkgo.data.services.factor_service.models_to_dataframe",
            side_effect=[df_a, df_b],
        ):
            result = service.calculate_factor_correlation(
                entity_type=1,
                entity_ids=["A", "B"],
                factor_names=["momentum"],
            )

        assert result.success is True
        matrix = result.data["correlation_matrix"]
        assert list(matrix.columns) == ["A_momentum", "B_momentum"]
        assert matrix.loc["A_momentum", "B_momentum"] == pytest.approx(1.0)

    def test_calculate_factor_correlation_empty_data_returns_clear_error(self, service, factor_crud):
        factor_crud.get_factors_by_entity.return_value = _model_list([])

        result = service.calculate_factor_correlation(
            entity_type=1,
            entity_ids=["missing"],
            factor_names=["momentum"],
        )

        assert result.success is False
        assert result.error == "No factor data found for correlation analysis"

    def test_factor_service_has_no_factor_shape_duck_typing(self):
        get_source = inspect.getsource(FactorService.get_factors_by_entity)
        latest_source = inspect.getsource(FactorService.get_latest_factors_by_entity)
        correlation_source = inspect.getsource(FactorService.calculate_factor_correlation)

        assert "isinstance(factors, list)" not in get_source
        assert "isinstance(latest_factors, list)" not in latest_source
        assert "hasattr(factors_data" not in correlation_source
        assert "to_dataframe') else" not in correlation_source
