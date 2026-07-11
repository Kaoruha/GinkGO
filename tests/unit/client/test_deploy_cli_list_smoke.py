"""#5009 deploy list 分页 CliRunner smoke（#6685 diff coverage gate 采集）。

deploy_cli.list_deployments 为本 PR 重构（--page/--page-size offset 分页 + --format json
ADR-021 envelope + count_deployments metadata.total）。container import 链触达该模块
但 smoke 不调命令体 → 改动行无覆盖信号 → 门禁红。本文件用 CliRunner + mock
trading_container 补信号（不连 DB / 不真起服务）。
"""

import os
import sys
import json
import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

_path = os.path.join(os.path.dirname(__file__), "..", "..", "..")
if _path not in sys.path:
    sys.path.insert(0, _path)

from ginkgo.client.deploy_cli import app

runner = CliRunner()


def _record(**over):
    rec = {
        "deployment_id": "dep-1",
        "source_task_id": "task-1",
        "target_portfolio_id": "pf-tgt",
        "mode": 1,
        "status": 0,
        "create_at": "2026-01-02 03:04:05",
    }
    rec.update(over)
    return rec


def _mock_svc(records=None, count=5, list_ok=True):
    svc = MagicMock()
    list_res = MagicMock()
    list_res.success = list_ok
    list_res.data = records if records is not None else []
    list_res.error = "boom"
    list_res.code = None  # 真实 failed ServiceResult 形状；避免 MagicMock auto-attr 陷阱
    list_res.warnings = []  # format_result 失败路径 getattr(result,"warnings") or []；不设则 auto-MagicMock 触发 json 无限递归
    svc.list_deployments.return_value = list_res

    count_res = MagicMock()
    count_res.success = True
    count_res.data = {"count": count}
    svc.count_deployments.return_value = count_res
    return svc


class TestDeployListJson:
    """--format json：ADR-021 envelope + #5009 metadata.total/limit/offset。"""

    @pytest.mark.unit
    def test_list_json_envelope_pagination(self):
        svc = _mock_svc(records=[_record()], count=1)
        with patch("ginkgo.trading.containers.trading_container") as tc:
            tc.deployment_service.return_value = svc
            result = runner.invoke(app, ["list", "--format", "json", "--page", "1", "--page-size", "5"])
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["success"] is True
        assert payload["count"] == 1
        assert payload["metadata"]["total"] == 1
        assert payload["metadata"]["limit"] == 5
        assert payload["metadata"]["offset"] == 5  # page1 * size5
        _, kwargs = svc.list_deployments.call_args
        assert kwargs["page"] == 1 and kwargs["page_size"] == 5

    @pytest.mark.unit
    def test_list_json_unlimited(self):
        # --page-size 0 → unlimited：q_page/q_page_size=None 下推 service；
        # build_list_result(limit=None) 时 limit 回退 len(records)（cli_utils.py:412）。
        svc = _mock_svc(records=[_record()], count=1)
        with patch("ginkgo.trading.containers.trading_container") as tc:
            tc.deployment_service.return_value = svc
            result = runner.invoke(app, ["list", "--format", "json", "--page-size", "0"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["metadata"]["limit"] == 1  # 回退 len(records)
        assert payload["metadata"]["offset"] == 0
        _, kwargs = svc.list_deployments.call_args
        assert kwargs["page"] is None and kwargs["page_size"] is None

    @pytest.mark.unit
    def test_list_portfolio_filter_forwarded(self):
        svc = _mock_svc(records=[], count=0)
        with patch("ginkgo.trading.containers.trading_container") as tc:
            tc.deployment_service.return_value = svc
            runner.invoke(app, ["list", "--format", "json", "--portfolio", "pf-42"])
        _, kwargs = svc.list_deployments.call_args
        assert kwargs["portfolio_id"] == "pf-42"
        _, ckwargs = svc.count_deployments.call_args
        assert ckwargs["portfolio_id"] == "pf-42"


class TestDeployListValidation:
    """#5009 契约守卫：--page/--page-size 负值 → typer.Exit(1)（非 0）。"""

    @pytest.mark.unit
    def test_negative_page_exits_nonzero(self):
        result = runner.invoke(app, ["list", "--page=-1"])
        assert result.exit_code != 0

    @pytest.mark.unit
    def test_negative_page_size_exits_nonzero(self):
        result = runner.invoke(app, ["list", "--page-size=-1"])
        assert result.exit_code != 0


class TestDeployListTextAndError:
    """text 路径（rich Table）+ 空记录分支 + 服务失败分支。"""

    @pytest.mark.unit
    def test_list_text_renders_table(self):
        svc = _mock_svc(records=[_record()], count=1)
        with patch("ginkgo.trading.containers.trading_container") as tc:
            tc.deployment_service.return_value = svc
            result = runner.invoke(app, ["list", "--page", "0", "--page-size", "5"])
        assert result.exit_code == 0
        assert "部署记录" in result.output  # Table title

    @pytest.mark.unit
    def test_list_text_empty_records(self):
        svc = _mock_svc(records=[], count=0)
        with patch("ginkgo.trading.containers.trading_container") as tc:
            tc.deployment_service.return_value = svc
            result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "无部署记录" in result.output

    @pytest.mark.unit
    def test_list_service_failure_json_envelope_exit_nonzero(self):
        """ADR-021 第 1/5/6 维：--format json + service 失败 → stdout 合法 JSON 错误 envelope + exit 1。"""
        svc = _mock_svc(list_ok=False)
        with patch("ginkgo.trading.containers.trading_container") as tc:
            tc.deployment_service.return_value = svc
            result = runner.invoke(app, ["list", "--format", "json"])
        assert result.exit_code != 0
        payload = json.loads(result.output)
        assert payload["success"] is False
        assert payload["error"]["message"] == "boom"

    @pytest.mark.unit
    def test_list_service_exception_json_envelope_exit_nonzero(self):
        """ADR-021 第 1/5/6 维：--format json + service 异常 → INTERNAL envelope + exit 1。"""
        svc = _mock_svc()
        svc.list_deployments.side_effect = RuntimeError("db down")
        with patch("ginkgo.trading.containers.trading_container") as tc:
            tc.deployment_service.return_value = svc
            result = runner.invoke(app, ["list", "--format", "json"])
        assert result.exit_code != 0
        payload = json.loads(result.output)
        assert payload["success"] is False
        assert payload["error"]["code"] == "INTERNAL"
