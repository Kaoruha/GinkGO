"""#5566 AC1: 7 端点 page_size 加 Query(ge=1, le=500) 上限约束。

防 `?page_size=999999` 无界查询直达 DB LIMIT N 致内存膨胀。
用 AST 源码级断言（零 import，绕过 api 层命名空间/容器启动问题）。
"""
import ast
from pathlib import Path

import pytest

REPO = Path(__file__).parents[2]  # tests/unit/xxx.py → worktree root

CASES = [
    ("api/api/data.py", "get_stockinfo"),
    ("api/api/data.py", "get_bars"),
    ("api/api/data.py", "get_ticks"),
    ("api/api/data.py", "get_adjust_factors"),
    ("api/api/data.py", "get_sync_history"),
    ("api/api/settings.py", "list_notification_history"),
    ("api/api/node_graph.py", "list_node_graphs"),
]


def _page_size_default(rel: str, fn_name: str):
    """返回 page_size 参数默认值的 AST 节点，或 None。"""
    tree = ast.parse((REPO / rel).read_text())
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == fn_name:
            args = node.args
            all_args = list(args.posonlyargs) + list(args.args)
            for i, a in enumerate(all_args):
                if a.arg == "page_size":
                    ndef = len(args.defaults)
                    start = len(all_args) - ndef  # defaults 对齐普通参数末尾
                    j = i - start
                    return args.defaults[j] if 0 <= j < ndef else None
            return None
    raise AssertionError(f"{fn_name} not found in {rel}")


def _is_bounded_query(node) -> bool:
    """page_size 默认须是 Query(...) 调用且 keywords 含 le=500, ge=1。"""
    if not isinstance(node, ast.Call):
        return False
    f = node.func
    name = f.id if isinstance(f, ast.Name) else getattr(getattr(f, "attr", None), None)
    if name != "Query":
        return False
    le = ge = None
    for kw in node.keywords:
        if kw.arg == "le" and isinstance(kw.value, ast.Constant):
            le = kw.value.value
        if kw.arg == "ge" and isinstance(kw.value, ast.Constant):
            ge = kw.value.value
    return le == 500 and ge == 1


@pytest.mark.parametrize("rel,fn_name", CASES)
def test_page_size_bounded(rel, fn_name):
    default = _page_size_default(rel, fn_name)
    assert default is not None, f"{fn_name}: page_size has no default value"
    assert _is_bounded_query(default), (
        f"{fn_name}: page_size must be Query(default=…, ge=1, le=500), "
        f"got {ast.dump(default)}"
    )
