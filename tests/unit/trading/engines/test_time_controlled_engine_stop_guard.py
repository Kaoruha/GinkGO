"""AST guard: TimeControlledEventEngine.stop() 单一定义且保留 executor shutdown。

回归守护 #5551：曾有两个 stop() 定义共存（@187 调试残留 `🔥+traceback` 被
@251 正式版遮蔽为死代码，且 @187 的 `-> bool` 标注错误——经 EventEngine.stop()
实返 None）。重新引入重复定义或误删 executor 清理时此测试立即 RED。

采用 AST 静态扫描（参照 tests/unit/workers/test_no_naive_datetime_guard.py
先例），无需实例化重资源引擎，专注守护结构不变量。
"""
import ast
from pathlib import Path

ENGINE_FILE = (
    Path(__file__).resolve().parents[4]
    / "src/ginkgo/trading/engines/time_controlled_engine.py"
)


def _class_body(class_name: str) -> ast.ClassDef:
    tree = ast.parse(ENGINE_FILE.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return node
    raise AssertionError(f"类 {class_name} 未在 {ENGINE_FILE} 中找到")


def _method_source(class_def: ast.ClassDef, method_name: str) -> str:
    """返回指定方法名的源码段（取第一个匹配）。"""
    for n in class_def.body:
        if isinstance(n, ast.FunctionDef) and n.name == method_name:
            return ast.unparse(n)
    raise AssertionError(f"方法 {method_name} 未找到")


def test_stop_defined_once():
    """stop() 在 TimeControlledEventEngine 中只能定义一次（#5551 AC1）。

    重复定义时后定义遮蔽前定义，前者成死代码——这是 #5551 的根因。
    """
    cls = _class_body("TimeControlledEventEngine")
    stop_defs = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "stop"]
    assert len(stop_defs) == 1, (
        f"stop() 应只定义一次，实际 {len(stop_defs)} 次"
        "（重复定义会互相遮蔽，见 #5551）"
    )


def test_stop_preserves_executor_shutdown():
    """保留下来的 stop() 必须清理线程池 _executor（#5551 AC2）。

    合并重复定义时不得丢失 @251 正式版的 executor.shutdown(wait=True)，
    否则引擎停止后线程池泄漏。
    """
    cls = _class_body("TimeControlledEventEngine")
    src = _method_source(cls, "stop")
    assert "_executor" in src, "stop() 必须引用 _executor（清理线程池资源）"
    assert "shutdown" in src, "stop() 必须调用 _executor.shutdown(wait=True)"


def test_set_time_provider_defined_once():
    """set_time_provider() 只能定义一次（#5551 AC: remove duplicate definitions）。

    曾有两处定义：@161 静默吞版（无模式校验，try/except 吞异常 + 设 global）
    被 @360 带校验版（BACKTEST/LIVE 模式 + TimeProvider 注解）遮蔽为死代码，
    与 stop() 同构。后定义覆盖前定义的命名空间绑定，前者从不被调用。
    """
    cls = _class_body("TimeControlledEventEngine")
    defs = [
        n for n in cls.body
        if isinstance(n, ast.FunctionDef) and n.name == "set_time_provider"
    ]
    assert len(defs) == 1, (
        f"set_time_provider() 应只定义一次，实际 {len(defs)} 次"
        "（重复定义会互相遮蔽，见 #5551）"
    )


def test_set_time_provider_keeps_mode_validation():
    """保留的 set_time_provider() 必须含模式校验（#5551 AC: keep validated version）。

    带校验版校验 BACKTEST→LogicalTimeProvider / LIVE→SystemTimeProvider，
    合并重复定义时不得丢失校验逻辑（否则退回静默吞版的无校验行为）。
    """
    cls = _class_body("TimeControlledEventEngine")
    src = _method_source(cls, "set_time_provider")
    assert "BACKTEST" in src, "set_time_provider 必须校验 BACKTEST 模式"
    assert "LogicalTimeProvider" in src, "set_time_provider 必须校验 LogicalTimeProvider"
    assert "SystemTimeProvider" in src, "set_time_provider 必须校验 SystemTimeProvider"
