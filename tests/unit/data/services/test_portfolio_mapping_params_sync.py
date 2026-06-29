# Issue #5880 缺陷5: API 绑参数落库与 CLI 不一致
# Upstream: ginkgo.data.services.portfolio_mapping_service._sync_params_for_mapping
# Downstream: ParamService.add_param -> MParam(index=..., value=...)
# Role: API 写入的参数必须与 CLI create_component_parameters 产出相同的 MParam 格式，
#       即用 params 的 key（逻辑位置索引）作 index，而非 enumerate 顺序位。
#       原 bug: _sync_params_for_mapping 用 enumerate(param_list) 的 idx 作 index，
#       当 key 非连续（如 {"0":..,"2":..}）时丢失逻辑位置，回测/读端取到错位参数。
# 对齐基准: mapping_service.create_component_parameters 用 MParam(index=key, value=value)。

from unittest.mock import MagicMock

from ginkgo.data.services.portfolio_mapping_service import PortfolioMappingService


def _make_svc():
    mock_mapping = MagicMock()
    mock_param = MagicMock()
    mock_mongo = MagicMock()
    mock_file = MagicMock()
    svc = PortfolioMappingService(
        mapping_crud=mock_mapping,
        param_service=mock_param,
        mongo_driver=mock_mongo,
        file_service=mock_file,
    )
    return svc, mock_param


class TestSyncParamsIndexFromKey:
    """缺陷5: index 必须取自 params 的 key（逻辑位置），与 CLI 对齐"""

    def test_non_sequential_keys_preserve_logical_index(self):
        """key 跳号时（{"0":..,"2":..}）index 应为 0 和 2，而非 enumerate 的 0 和 1"""
        svc, mock_param = _make_svc()

        svc._sync_params_for_mapping(
            mapping_uuid="map-1",
            params={"0": "a", "2": "c"},
        )

        indices = sorted(call.kwargs["index"] for call in mock_param.add_param.call_args_list)
        assert indices == [0, 2], f"逻辑 index 应保留 key（0,2），实际 {indices}"


class TestSyncParamsValueRawString:
    """缺陷5: 字符串 value 原样存，不双重 json.dumps（对齐 CLI 原样 str）

    CLI create_component_parameters 存原始 str（如 "0.5"、"StrategyName"），
    读端 json.loads+fallback 反解。API 若再 json.dumps 字符串会得到 '"0.5"'（带引号），
    读端 json.loads 出来是 str 而非 number，与 CLI 同值产出类型分歧。
    """

    def test_string_value_stored_raw_not_double_quoted(self):
        svc, mock_param = _make_svc()

        svc._sync_params_for_mapping(
            mapping_uuid="map-1",
            params={"0": "0.5"},
        )

        value = mock_param.add_param.call_args.kwargs["value"]
        assert value == "0.5", f"字符串 value 应原样存，实际 {value!r}"

    def test_number_value_json_encoded_for_round_trip(self):
        """非字符串（number）经 json.dumps 存，读端 json.loads 还原为 number"""
        svc, mock_param = _make_svc()

        svc._sync_params_for_mapping(
            mapping_uuid="map-1",
            params={"1": 0.3},
        )

        value = mock_param.add_param.call_args.kwargs["value"]
        assert value == "0.3", f"number 应 json.dumps 成字符串供往返还原，实际 {value!r}"
