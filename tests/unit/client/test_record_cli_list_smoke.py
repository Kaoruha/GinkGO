"""#5009 record_cli signal/order/position/analyzer 分页 CliRunner smoke（#6685 gate 采集）。

record_cli 4 命令为本 PR 重构（--page/--page-size offset 分页 + --format json ADR-021
envelope + count_X metadata.total）。container import 链触达该模块但 smoke 不调命令体
→ 改动行无覆盖信号 → 门禁红。本文件用 CliRunner + mock data.containers.Container 补
信号（不连 DB / 不真起服务），覆盖 JSON/text/空记录/负值守卫四条路径 × 4 命令。
"""

import os
import sys
import json
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

_path = os.path.join(os.path.dirname(__file__), "..", "..", "..")
if _path not in sys.path:
    sys.path.insert(0, _path)

from ginkgo.client.record_cli import app

runner = CliRunner()

# command → (container attr, get_df method, count method, text-path columns)
_COMMANDS = {
    "signal": ("signal_service", "get_signals_df", "count_signals",
               ["uuid", "engine_id", "portfolio_id", "task_id", "direction", "code", "timestamp", "reason"]),
    "order": ("order_service", "get_orders_df", "count_orders",
              ["uuid", "portfolio_id", "code", "direction", "order_type", "quantity", "limit_price", "timestamp", "status"]),
    "position": ("result_service", "get_positions_df", "count_positions",
                 ["uuid", "portfolio_id", "code", "volume", "cost", "price", "fee", "timestamp"]),
    "analyzer": ("analyzer_service", "get_records_df", "count_records",
                 ["uuid", "portfolio_id", "engine_id", "analyzer_id", "name", "value", "timestamp"]),
}


def _df(columns):
    return pd.DataFrame([{c: f"v_{c}" for c in columns}])


def _setup(command, records_df, count=1, ok=True):
    """Patch Container.<svc_attr> → 返回 mock service；返回 (patch_ctx, svc, get_method)."""
    svc_attr, get_method, count_method, _cols = _COMMANDS[command]
    svc = MagicMock()
    get_res = MagicMock()
    get_res.success = ok
    get_res.data = records_df
    get_res.error = "boom"
    get_res.code = None  # 真实 failed ServiceResult 形状；避免 MagicMock auto-attr 陷阱
    get_res.warnings = []  # format_result 失败路径 getattr(result,"warnings") or []；不设则 auto-MagicMock 触发 json 无限递归
    getattr(svc, get_method).return_value = get_res
    count_res = MagicMock()
    count_res.success = True
    count_res.data = {"count": count}
    getattr(svc, count_method).return_value = count_res
    ctx = patch("ginkgo.data.containers.Container")
    return ctx, svc, svc_attr, get_method


def _invoke(command, args):
    """command: signal|order|position|analyzer。返回 (result, svc, get_method)。"""
    cols = _COMMANDS[command][3]
    ctx, svc, svc_attr, get_method = _setup(command, _df(cols), count=2)
    with ctx as Container:
        getattr(Container, svc_attr).return_value = svc
        result = runner.invoke(app, [command] + args)
    return result, svc, get_method


class TestRecordJson:
    """--format json：ADR-021 envelope + #5009 metadata.total/limit/offset，4 命令。"""

    @pytest.mark.unit
    @pytest.mark.parametrize("command", list(_COMMANDS))
    def test_json_envelope_pagination(self, command):
        result, svc, get_method = _invoke(command, ["--format", "json", "--page", "1", "--page-size", "5"])
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["success"] is True
        assert payload["metadata"]["total"] == 2
        assert payload["metadata"]["offset"] == 5  # page1 * size5
        _, kwargs = getattr(svc, get_method).call_args
        assert kwargs["page"] == 1 and kwargs["page_size"] == 5

    @pytest.mark.unit
    @pytest.mark.parametrize("command", list(_COMMANDS))
    def test_json_unlimited_passes_none(self, command):
        result, svc, get_method = _invoke(command, ["--format", "json", "--page-size", "0"])
        assert result.exit_code == 0
        _, kwargs = getattr(svc, get_method).call_args
        assert kwargs["page"] is None and kwargs["page_size"] is None
        assert json.loads(result.output)["metadata"]["offset"] == 0


class TestRecordTextAndEmpty:
    """text 路径（display_dataframe + columns_config）+ 空记录分支。"""

    @pytest.mark.unit
    @pytest.mark.parametrize("command", list(_COMMANDS))
    def test_text_renders(self, command):
        result, _, _ = _invoke(command, ["--page", "0", "--page-size", "5"])
        assert result.exit_code == 0, result.output

    @pytest.mark.unit
    @pytest.mark.parametrize("command", list(_COMMANDS))
    def test_text_empty_records(self, command):
        cols = _COMMANDS[command][3]
        ctx, svc, svc_attr, _ = _setup(command, pd.DataFrame(), count=0)  # 空 df
        with ctx as Container:
            getattr(Container, svc_attr).return_value = svc
            result = runner.invoke(app, [command])
        assert result.exit_code == 0
        assert "No" in result.output  # "No signals/orders/positions/analyzer records found."


class TestRecordValidation:
    """#5009 契约守卫：--page/--page-size 负值 → exit 2（BAD_PARAMS，ADR-021 dim 6）。4 命令各自独立守卫块。"""

    @pytest.mark.unit
    @pytest.mark.parametrize("command", list(_COMMANDS))
    def test_negative_page_exits_nonzero(self, command):
        result, _, _ = _invoke(command, ["--page=-1"])
        assert result.exit_code != 0

    @pytest.mark.unit
    @pytest.mark.parametrize("command", list(_COMMANDS))
    @pytest.mark.parametrize("bad_arg", ["--page=-1", "--page-size=-1"])
    def test_negative_param_json_envelope_exit_2(self, command, bad_arg):
        """--page/--page-size <0 + --format json → BAD_PARAMS envelope + exit 2（#6652 review E2，ADR-021 dim 1/6）。

        旧实现 JSON 模式 console.print Rich 标记到 stdout + exit 1，stdout 非合法 JSON，jq 崩。
        """
        result, _, _ = _invoke(command, [bad_arg, "--format", "json"])
        assert result.exit_code == 2, result.output
        payload = json.loads(result.output)
        assert payload["success"] is False
        assert payload["error"]["code"] == "BAD_PARAMS"


class TestRecordServiceFailure:
    """get_X_df 失败分支：result.success False → JSON 模式发 error envelope + exit 1（ADR-021 第 5/6 维）。
    text 模式打印诊断 + exit 1（原隐式 exit 0 是 bug）。"""

    @pytest.mark.unit
    @pytest.mark.parametrize("command", list(_COMMANDS))
    def test_service_failure_json_envelope_exit_nonzero(self, command):
        cols = _COMMANDS[command][3]
        ctx, svc, svc_attr, get_method = _setup(command, _df(cols), count=0, ok=False)
        with ctx as Container:
            getattr(Container, svc_attr).return_value = svc
            result = runner.invoke(app, [command, "--format", "json"])
        assert result.exit_code != 0  # 失败分支 JSON 模式 raise typer.Exit(1)
        payload = json.loads(result.output)
        assert payload["success"] is False
        assert payload["error"]["message"] == "boom"

    @pytest.mark.unit
    @pytest.mark.parametrize("command", list(_COMMANDS))
    def test_service_failure_text_exits_nonzero(self, command):
        cols = _COMMANDS[command][3]
        ctx, svc, svc_attr, _ = _setup(command, _df(cols), count=0, ok=False)
        with ctx as Container:
            getattr(Container, svc_attr).return_value = svc
            result = runner.invoke(app, [command])  # 默认 text
        assert result.exit_code != 0  # text 失败也 exit 1（原隐式 exit 0 是 bug）

    @pytest.mark.unit
    @pytest.mark.parametrize("command", list(_COMMANDS))
    def test_service_exception_json_envelope_exit_nonzero(self, command):
        """service 抛异常 → except 分支 JSON 模式发 INTERNAL envelope + exit 1（ADR-021 第 1 维）。"""
        cols = _COMMANDS[command][3]
        ctx, svc, svc_attr, get_method = _setup(command, _df(cols), count=0, ok=True)
        getattr(svc, get_method).side_effect = RuntimeError("db down")
        with ctx as Container:
            getattr(Container, svc_attr).return_value = svc
            result = runner.invoke(app, [command, "--format", "json"])
        assert result.exit_code != 0
        payload = json.loads(result.output)
        assert payload["success"] is False
        assert payload["error"]["code"] == "INTERNAL"
