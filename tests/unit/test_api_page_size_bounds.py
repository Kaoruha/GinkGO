"""#5566: API page_size 上限约束集中到默认配置。

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


def _is_default_max_page_size(node) -> bool:
    return isinstance(node, ast.Name) and node.id == "DEFAULT_MAX_PAGE_SIZE"


def _is_bounded_query(node) -> bool:
    """page_size 默认须是 Query(...) 调用且 keywords 含 le=DEFAULT_MAX_PAGE_SIZE, ge=1。"""
    if not isinstance(node, ast.Call):
        return False
    f = node.func
    name = f.id if isinstance(f, ast.Name) else getattr(getattr(f, "attr", None), None)
    if name != "Query":
        return False
    le = ge = None
    for kw in node.keywords:
        if kw.arg == "le":
            le = kw.value
        if kw.arg == "ge" and isinstance(kw.value, ast.Constant):
            ge = kw.value.value
    return _is_default_max_page_size(le) and ge == 1


def test_default_max_page_size_config_exists():
    tree = ast.parse((REPO / "api/core/pagination.py").read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "DEFAULT_MAX_PAGE_SIZE":
                    assert isinstance(node.value, ast.Constant)
                    assert node.value.value == 500
                    return
    raise AssertionError("api/core/pagination.py must define DEFAULT_MAX_PAGE_SIZE = 500")


def test_api_routes_do_not_hardcode_default_max_page_size():
    offenders = []
    for path in sorted((REPO / "api/api").glob("*.py")):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func_name = node.func.id if isinstance(node.func, ast.Name) else None
            if func_name != "Query":
                continue
            for kw in node.keywords:
                if kw.arg == "le" and isinstance(kw.value, ast.Constant) and kw.value.value == 500:
                    offenders.append(f"{path.relative_to(REPO)}:{node.lineno}")
    assert offenders == []


@pytest.mark.parametrize("rel,fn_name", CASES)
def test_page_size_bounded(rel, fn_name):
    default = _page_size_default(rel, fn_name)
    assert default is not None, f"{fn_name}: page_size has no default value"
    assert _is_bounded_query(default), (
        f"{fn_name}: page_size must be Query(default=…, ge=1, le=DEFAULT_MAX_PAGE_SIZE), " f"got {ast.dump(default)}"
    )
