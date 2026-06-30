"""
MySQL migration 链完整性测试 (#5529)

验证 migrations/mysql/versions/ 形成**线性链**（无分支冲突、无悬空 down_revision），
且 merge node 84a2de8c7c00 正确合并 0336f9b2c8a2 + t088_trade_records 两分支，
upgrade 同时建 deployment 与 user_credentials 表。

纯 ast 静态解析（不 import alembic / 不连 DB），聚焦链结构与建表声明的正确性。
"""

import ast
import importlib.util
import sys
from pathlib import Path

import pytest

MIGRATIONS_DIR = Path(__file__).resolve().parents[4] / "migrations" / "mysql" / "versions"


def _parse_module(path: Path) -> ast.AST:
    return ast.parse(path.read_text(encoding="utf-8"))


def _extract_revision_metadata(tree: ast.AST):
    """从模块 ast 提取 revision / down_revision（str 或 tuple）。"""
    revision = None
    down_revision = None
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.value is None:
                continue
            if node.target.id == "revision":
                revision = ast.literal_eval(node.value)
            elif node.target.id == "down_revision":
                down_revision = ast.literal_eval(node.value)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    if target.id == "revision":
                        revision = ast.literal_eval(node.value)
                    elif target.id == "down_revision":
                        down_revision = ast.literal_eval(node.value)
    return revision, down_revision


def _first_string_arg(call: ast.Call):
    """op.create_table('name', ...) / op.drop_table('name') 的第一个字面量参数。"""
    if call.args and isinstance(call.args[0], ast.Constant):
        return call.args[0].value
    return None


def _tables_in_func(tree: ast.AST, func_name: str, method: str):
    """收集某函数体里 op.<method>('table') 的所有表名。"""
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            tables = []
            for inner in ast.walk(node):
                if (isinstance(inner, ast.Call)
                        and isinstance(inner.func, ast.Attribute)
                        and inner.func.attr == method
                        and isinstance(inner.func.value, ast.Name)):
                    name = _first_string_arg(inner)
                    if name is not None:
                        tables.append(name)
            return tables
    return []


def _load_all_migrations():
    """返回 {revision: {'path', 'down_revision', 'tree'}}。down_revision 归一为 tuple。"""
    result = {}
    for py in sorted(MIGRATIONS_DIR.glob("*.py")):
        if py.name == "__init__.py":
            continue
        tree = _parse_module(py)
        revision, down = _extract_revision_metadata(tree)
        if revision is None:
            continue
        down_tuple = down if isinstance(down, tuple) else ((down,) if down else ())
        result[revision] = {"path": py, "down": down_tuple, "raw_down": down, "tree": tree}
    return result


# ---------- 84a2 merge node 存在性与结构 ----------

def _find_84a2_path():
    for py in MIGRATIONS_DIR.glob("*.py"):
        if py.name.startswith("84a2de8c7c00"):
            return py
    return None


def test_84a2_merge_node_exists_on_master():
    """84a2 必须存在于 master（#5529：a1b2 down=84a2 但文件缺失致链断裂）。"""
    path = _find_84a2_path()
    assert path is not None, "84a2de8c7c00 merge node 不存在 → a1b2c3d4e5f6 的 down_revision 悬空"


def test_84a2_down_revision_merges_both_branches():
    """84a2.down_revision 必须是 tuple 合并 0336f9b2c8a2 + t088_trade_records。"""
    path = _find_84a2_path()
    if path is None:
        pytest.skip("84a2 不存在（前置测试未通过）")
    tree = _parse_module(path)
    revision, down = _extract_revision_metadata(tree)
    assert revision == "84a2de8c7c00"
    assert isinstance(down, tuple), f"down_revision 应为 tuple（merge node），实际 {type(down).__name__}: {down}"
    assert "0336f9b2c8a2" in down and "t088_trade_records" in down


def test_84a2_upgrade_creates_deployment_and_user_credentials():
    """upgrade 必须同时建 deployment 与 user_credentials（#5529：原仅建 deployment 漏 user_credentials）。"""
    path = _find_84a2_path()
    if path is None:
        pytest.skip("84a2 不存在")
    tree = _parse_module(path)
    created = set(_tables_in_func(tree, "upgrade", "create_table"))
    assert "deployment" in created, f"upgrade 未建 deployment，实际 {created}"
    assert "user_credentials" in created, f"upgrade 未建 user_credentials（#5529 缺口），实际 {created}"


def test_84a2_downgrade_drops_both_tables():
    """downgrade 必须 drop user_credentials 与 deployment（逆序）。"""
    path = _find_84a2_path()
    if path is None:
        pytest.skip("84a2 不存在")
    tree = _parse_module(path)
    dropped = _tables_in_func(tree, "downgrade", "drop_table")
    assert "user_credentials" in dropped
    assert "deployment" in dropped
    # user_credentials 后建，必须先 drop（逆序）
    assert dropped.index("user_credentials") < dropped.index("deployment")


# ---------- 全链完整性 ----------

def test_no_dangling_down_revision():
    """每个 down_revision 必须指向链中存在的 revision（或为空=根）。"""
    migrations = _load_all_migrations()
    known = set(migrations.keys())
    dangling = []
    for rev, meta in migrations.items():
        for parent in meta["down"]:
            if parent not in known:
                dangling.append((rev, parent))
    assert not dangling, f"悬空 down_revision: {dangling}（指向不存在的 revision）"


def test_migration_chain_has_single_head():
    """链必须有唯一 head（无下游的 revision）。多个 head = 分支未 merge = upgrade head 歧义。"""
    migrations = _load_all_migrations()
    if not migrations:
        pytest.skip("无 migration 文件")
    all_parents = {p for meta in migrations.values() for p in meta["down"]}
    heads = [rev for rev in migrations if rev not in all_parents]
    assert len(heads) == 1, (
        f"期望单一 head，实际 {len(heads)} 个 heads: {heads}（存在未 merge 的分支）"
    )


def test_branch_points_have_merge_nodes():
    """每个分支点（>1 子节点）必须被某 merge node 收敛（down_revision tuple）。"""
    migrations = _load_all_migrations()
    # parent -> 子节点列表
    children_count = {}
    for meta in migrations.values():
        for parent in meta["down"]:
            children_count[parent] = children_count.get(parent, 0) + 1
    # 分支点：有 >1 子节点
    branch_points = {p for p, c in children_count.items() if c > 1}
    if not branch_points:
        return
    # 每个 branch_point 必须存在某 migration 的 down_revision(tuple) 收敛其所有子节点
    for bp in branch_points:
        # 找该 branch_point 的所有子 revision
        children_of_bp = {rev for rev, meta in migrations.items() if bp in meta["down"]}
        # 找 merge node：down_revision 为 tuple 且包含全部 children_of_bp
        merged = False
        for rev, meta in migrations.items():
            if isinstance(meta["raw_down"], tuple) and children_of_bp <= set(meta["down"]):
                merged = True
                break
        assert merged, f"分支点 {bp} 的子节点 {children_of_bp} 未被 merge node 收敛"
