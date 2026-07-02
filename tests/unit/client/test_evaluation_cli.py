"""
TDD for ginkgo eval 三命令(stability/monitor-create/monitor-live)恢复。

背景:#4652 误把 import 路径漂移当"未实现",加 return stub 屏蔽。
底层 BacktestEvaluator 实现完好,3 调用方在用。本测试守护命令真正调通 evaluator,
并防回归(输出不得再含 "not yet implemented")。
"""

import sys
import json
import re
from pathlib import Path

import pytest

project_root = Path(__file__).parent.parent.parent.parent
_path = str(project_root / "src")
sys.path.insert(0, _path)

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

runner = CliRunner()

from ginkgo.client.evaluation_cli import app  # noqa: E402
from ginkgo.trading.evaluation.rules.rule_registry import get_global_registry  # noqa: E402

# patch 源模块(命令体为函数级 import,每次执行从源模块取属性)
_EVALUATOR_PATH = "ginkgo.trading.analysis.evaluation.backtest_evaluator.BacktestEvaluator"

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


def _success_result() -> dict:
    """匹配 _display_stability_results / _display_baseline_summary 期望的键。"""
    return {
        "status": "success",
        "evaluation_time": "2026-07-01T10:00:00",
        "portfolio_id": "port-001",
        # 返回键是 task_id(ADR-016),展示层读 engine_id → 兼容读取
        "task_id": "task-001",
        "data_summary": {
            "analyzer_records": 100,
            "signal_records": 50,
            "order_records": 40,
            "time_span": {"days": 244},
        },
        "optimal_slice_config": {
            "period_days": 30,
            "stability_score": 0.85,
            "slice_count": 8,
        },
        "stability_analysis": {
            "cross_metric_comparison": {
                "ranking": [("sharpe", 0.85), ("max_drawdown", 0.72)],
            }
        },
        "recommendations": ["consider more slices"],
        "monitoring_baseline": {
            "slice_period_days": 30,
            "total_slices": 8,
            "creation_time": "2026-07-01",
            "baseline_stats": {
                "sharpe": {"mean": 1.2, "std_dev": 0.3, "range": 0.9},
            },
        },
    }


# ---- stability ----

def test_stability_success():
    mock_evaluator = MagicMock()
    mock_evaluator.evaluate_backtest_stability.return_value = _success_result()

    with patch(_EVALUATOR_PATH, return_value=mock_evaluator):
        result = runner.invoke(
            app, ["stability", "--portfolio", "port-001", "--engine", "task-001"]
        )

    out = _strip_ansi(result.output)
    assert result.exit_code == 0, result.output
    assert "not yet implemented" not in out
    mock_evaluator.evaluate_backtest_stability.assert_called_once_with(
        portfolio_id="port-001",
        task_id="task-001",
        start_date=None,
        end_date=None,
    )
    # 展示层渲染了 result 关键值
    assert "port-001" in out
    assert "244" in out  # time span days
    assert "0.8500" in out  # stability_score :.4f


def test_stability_no_stub():
    """防回归 #4652: 不得再 return stub。"""
    mock_evaluator = MagicMock()
    mock_evaluator.evaluate_backtest_stability.return_value = _success_result()

    with patch(_EVALUATOR_PATH, return_value=mock_evaluator):
        result = runner.invoke(
            app, ["stability", "--portfolio", "port-001", "--engine", "task-001"]
        )

    out = _strip_ansi(result.output)
    assert "not yet implemented" not in out
    assert "4639" not in out  # TODO issue 链接也不应在用户输出里


def test_stability_failed():
    mock_evaluator = MagicMock()
    mock_evaluator.evaluate_backtest_stability.return_value = {
        "status": "failed",
        "reason": "invalid_data",
    }

    with patch(_EVALUATOR_PATH, return_value=mock_evaluator):
        result = runner.invoke(
            app, ["stability", "--portfolio", "port-001", "--engine", "task-001"]
        )

    out = _strip_ansi(result.output)
    assert result.exit_code == 0
    assert "invalid_data" in out


def test_stability_portfolio_required():
    """--portfolio/--engine 必填(删交互式列出后)。"""
    result = runner.invoke(app, ["stability"])
    assert result.exit_code != 0  # typer 缺必填参数


# ---- monitor-create ----

def test_monitor_create_success(tmp_path):
    mock_evaluator = MagicMock()
    mock_evaluator.evaluate_backtest_stability.return_value = _success_result()
    out_file = tmp_path / "baseline.json"

    with patch(_EVALUATOR_PATH, return_value=mock_evaluator):
        result = runner.invoke(
            app,
            [
                "monitor-create",
                "-p", "port-001",
                "-e", "task-001",
                "-o", str(out_file),
            ],
        )

    assert result.exit_code == 0, result.output
    assert "not yet implemented" not in _strip_ansi(result.output)
    assert out_file.exists()
    saved = json.loads(out_file.read_text(encoding="utf-8"))
    assert saved["slice_period_days"] == 30


# ---- monitor-live ----

def test_monitor_live_no_stub(tmp_path):
    """monitor-live 去 stub 后真调 create_live_monitor(demo loop 用异常短路)。"""
    baseline_file = tmp_path / "b.json"
    baseline_file.write_text(
        json.dumps(_success_result()["monitoring_baseline"]), encoding="utf-8"
    )

    mock_evaluator = MagicMock()
    # 让 demo loop 第一次 sleep 即抛错,被 except Exception 捕获后正常返回
    with patch(_EVALUATOR_PATH, return_value=mock_evaluator), \
            patch(
                "time.sleep",
                side_effect=RuntimeError("short-circuit demo loop"),
            ):
        result = runner.invoke(
            app,
            [
                "monitor-live",
                "-b", str(baseline_file),
                "-p", "port-001",
                "--interval", "1",
            ],
        )

    out = _strip_ansi(result.output)
    assert "not yet implemented" not in out
    assert mock_evaluator.create_live_monitor.called


# ---- eval strategy: level 分级 (#4702) ----
# 背景:--level strict 与 basic 输出完全一致。根因双重:
#   ① SimpleEvaluator.evaluate 不按 level 过滤规则(base_evaluator)
#   ② CLI 从未注册 best_practice_rules 里的 5 条 STRICT 规则
# 框架已有 base_rule.is_applicable(level) = enabled and level.includes(self.level),
# 但 SimpleEvaluator 未调用它。本组测试经 CLI 公共接口验证三档分级正确。

# best_practice_rules 里全部 STRICT 级规则 id
_STRICT_RULE_IDS = (
    "DECORATOR_USAGE",
    "EXCEPTION_HANDLING",
    "LOGGING_USAGE",
    "PARAMETER_VALIDATION",
    "RESET_STATE_CALL",
)


@pytest.fixture
def clean_eval_registry():
    """全局 registry 是单例;每次 eval-strategy 测试前清空,保证计数确定。"""
    get_global_registry().clear()
    yield
    get_global_registry().clear()


@pytest.fixture
def best_practice_deficient_strategy(tmp_path):
    """合法 BaseStrategy 子类,但缺最佳实践:无装饰器/无 try-except/无 GLOG/无参数校验。
    会触发 STRICT 规则(DECORATOR_USAGE/EXCEPTION_HANDLING/LOGGING_USAGE/PARAMETER_VALIDATION)。"""
    content = (
        "from ginkgo.trading.strategies.strategy_base import BaseStrategy\n"
        "\n"
        "class DeficientStrategy(BaseStrategy):\n"
        "    def cal(self, portfolio_info, event):\n"
        "        return []\n"
    )
    p = tmp_path / "deficient.py"
    p.write_text(content)
    return p


class TestEvalStrategyLevelFiltering:
    """#4702: --level strict 必须比 --level basic 跑更多检查。"""

    def test_strict_fires_best_practice_rules_basic_does_not(
        self, clean_eval_registry, best_practice_deficient_strategy
    ):
        """STRICT 规则在 strict 档触发、在 basic 档不触发(tracer:驱动 Fix A 注册 + Fix B 过滤)。"""
        r_strict = runner.invoke(
            app,
            ["strategy", str(best_practice_deficient_strategy), "--level", "strict"],
        )
        r_basic = runner.invoke(
            app,
            ["strategy", str(best_practice_deficient_strategy), "--level", "basic"],
        )

        out_strict = _strip_ansi(r_strict.output)
        out_basic = _strip_ansi(r_basic.output)

        strict_hit = {rid for rid in _STRICT_RULE_IDS if rid in out_strict}
        basic_hit = {rid for rid in _STRICT_RULE_IDS if rid in out_basic}

        assert r_strict.exit_code == 0, r_strict.output
        assert r_basic.exit_code == 0, r_basic.output
        assert strict_hit, (
            f"strict 档应触发 STRICT 规则,实测均未触发。输出:\n{out_strict}"
        )
        assert not basic_hit, (
            f"basic 档不得跑 STRICT 规则,实测触发了 {basic_hit}。输出:\n{out_basic}"
        )

    def test_strict_has_more_issues_than_basic(
        self, clean_eval_registry, best_practice_deficient_strategy
    ):
        """#4702 字面验收:strict 档 issue 数须多于 basic 档(增量检查)。"""
        counts = {}
        for lvl in ("basic", "standard", "strict"):
            # 每档前清空,避免单例 registry 跨调用累积重复注册
            get_global_registry().clear()
            res = runner.invoke(
                app,
                ["strategy", str(best_practice_deficient_strategy), "--level", lvl],
            )
            assert res.exit_code == 0, res.output
            out = _strip_ansi(res.output)
            # EvaluationResult repr 里每条 issue 形如 code='DECORATOR_USAGE'
            codes = re.findall(r"code='([A-Z_]+)'", out)
            counts[lvl] = len(codes)

        # 三档非递减,且 strict 严格多于 basic(修复前两者均为 0,完全一致)
        assert counts["basic"] <= counts["standard"] <= counts["strict"]
        assert counts["strict"] > counts["basic"], (
            f"strict issue 数({counts['strict']})应多于 basic({counts['basic']})"
        )


class TestSimpleEvaluatorLevelFiltering:
    """#4702 根因守护:SimpleEvaluator.evaluate 须按 level 过滤规则(独立于 CLI)。

    直接对 SimpleEvaluator 注入独立 RuleRegistry(隔离全局单例累积),
    验证 base_rule.is_applicable(level) 真的被 evaluate 调用。"""

    def test_evaluate_filters_rules_by_level(self, tmp_path):
        from ginkgo.trading.evaluation.core.enums import (
            ComponentType,
            EvaluationLevel,
        )
        from ginkgo.trading.evaluation.evaluators.base_evaluator import SimpleEvaluator
        from ginkgo.trading.evaluation.rules.rule_registry import RuleRegistry
        from ginkgo.trading.evaluation.rules.structural_rules import (
            StrategyBaseInheritanceRule,
        )
        from ginkgo.trading.evaluation.rules.logical_rules import (
            ReturnStatementRule,
        )
        from ginkgo.trading.evaluation.rules.best_practice_rules import (
            DecoratorUsageRule,
        )

        # 独立 registry,各取一条 BASIC/STANDARD/STRICT 规则
        registry = RuleRegistry()
        registry.register_rule_class(StrategyBaseInheritanceRule, ComponentType.STRATEGY)
        registry.register_rule_class(ReturnStatementRule, ComponentType.STRATEGY)
        registry.register_rule_class(DecoratorUsageRule, ComponentType.STRATEGY)

        strategy = tmp_path / "s.py"
        strategy.write_text(
            "from ginkgo.trading.strategies.strategy_base import BaseStrategy\n"
            "class S(BaseStrategy):\n"
            "    def cal(self, portfolio_info, event):\n"
            "        return []\n"
        )

        evaluator = SimpleEvaluator(ComponentType.STRATEGY, registry=registry)

        # BASIC 档:STANDARD/STRICT 规则不得运行
        result_basic = evaluator.evaluate(strategy, level=EvaluationLevel.BASIC)
        basic_codes = {i.code for i in result_basic.issues}
        assert "DECORATOR_USAGE" not in basic_codes, "STRICT 规则在 BASIC 档不应运行"
        assert "RETURN_STATEMENT" not in basic_codes, "STANDARD 规则在 BASIC 档不应运行"

        # STRICT 档:全部规则运行,STRICT 规则须触发
        result_strict = evaluator.evaluate(strategy, level=EvaluationLevel.STRICT)
        strict_codes = {i.code for i in result_strict.issues}
        assert "DECORATOR_USAGE" in strict_codes, "STRICT 规则在 STRICT 档应触发"

        # STANDARD 档:STRICT 规则仍不得运行
        result_std = evaluator.evaluate(strategy, level=EvaluationLevel.STANDARD)
        std_codes = {i.code for i in result_std.issues}
        assert "DECORATOR_USAGE" not in std_codes, "STRICT 规则在 STANDARD 档不应运行"
