# Guard: execution engine 模块不得使用 naive datetime.now()
#
# DST 切换/跨时区部署下 naive datetime 导致 timestamp 跳变、心跳/事件时间戳不一致 (#5548)。
# 所有时间戳必须用 aware datetime（datetime.now(timezone.utc)）。
#
# 本测试用 AST 扫描，匹配裸调用（无参数）的 datetime.now / datetime.datetime.now，
# 兼容 `from datetime import datetime` 与 `import datetime` 两种导入风格。
import ast
from pathlib import Path


EXECUTION_MODULES = [
    "src/ginkgo/trading/brokers/okx_broker.py",
    "src/ginkgo/trading/engines/event_engine.py",
    "src/ginkgo/workers/execution_node/portfolio_processor.py",
    "src/ginkgo/workers/execution_node/heartbeat_manager.py",
    "src/ginkgo/workers/execution_node/metrics.py",
    "src/ginkgo/workers/execution_node/node.py",
    "src/ginkgo/workers/backtest_worker/node.py",
    "src/ginkgo/workers/execution_node/backpressure.py",
]


def _worktree_root() -> Path:
    """从测试文件向上找到含 src/ 与 tests/ 的仓库根。"""
    p = Path(__file__).resolve()
    for parent in p.parents:
        if (parent / "src").is_dir() and (parent / "tests").is_dir():
            return parent
    raise RuntimeError("worktree root not found")


def _is_bare_datetime_now(func: ast.AST) -> bool:
    """匹配 datetime.now 或 datetime.datetime.now 属性访问节点。"""
    if not isinstance(func, ast.Attribute) or func.attr != "now":
        return False
    value = func.value
    # `from datetime import datetime` → datetime.now
    if isinstance(value, ast.Name) and value.id == "datetime":
        return True
    # `import datetime` → datetime.datetime.now
    if (
        isinstance(value, ast.Attribute)
        and value.attr == "datetime"
        and isinstance(value.value, ast.Name)
        and value.value.id == "datetime"
    ):
        return True
    return False


def _find_bare_datetime_now(file_path: Path) -> list[int]:
    """返回文件中裸 datetime.now() 调用（无 tz 参数）的行号列表。"""
    tree = ast.parse(file_path.read_text(encoding="utf-8"))
    lines: list[int] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _is_bare_datetime_now(node.func):
            if not node.args:
                lines.append(node.lineno)
    return lines


def test_no_bare_datetime_now_in_execution_modules():
    """execution engine 模块不得有裸 datetime.now() (#5548)。"""
    root = _worktree_root()
    offenders: dict[str, list[int]] = {}
    for rel in EXECUTION_MODULES:
        f = root / rel
        if not f.exists():
            continue
        lines = _find_bare_datetime_now(f)
        if lines:
            offenders[rel] = lines
    assert not offenders, (
        f"naive datetime.now() (无 timezone) 发现于: {offenders}；"
        f"请改为 datetime.now(timezone.utc) (#5548)"
    )
