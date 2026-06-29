"""#5389: trailing slash 307 修复。

核心逻辑：HTTP middleware 把带 trailing slash 的请求路径内部 strip
（改 request.scope["path"]，路由匹配前生效），避免 307 重定向丢失 Auth header。
"""
import importlib.util
from pathlib import Path

from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import PlainTextResponse
from starlette.testclient import TestClient

# 从文件路径加载（绕过 sys.path/sys.modules 缓存；worktree editable .pth 默认
# 指向主仓库，见 arch_worktree_editable_import_divergence）
_MOD_PATH = Path(__file__).parents[2] / "api" / "trailing_slash.py"
_spec = importlib.util.spec_from_file_location("api_trailing_slash_under_test", _MOD_PATH)
_ts = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_ts)
strip_trailing_slash = _ts.strip_trailing_slash


def _make_app(path: str = "/items"):
    async def homepage(request):
        return PlainTextResponse("ok")

    app = Starlette(routes=[Route(path, homepage)])
    app.middleware("http")(strip_trailing_slash)
    return TestClient(app)


def test_no_slash_matches():
    """路由注册无 slash，请求无 slash → 200。"""
    client = _make_app()
    assert client.get("/items").status_code == 200


def test_trailing_slash_stripped_no_redirect():
    """带 slash 请求被 middleware strip → 200（非 307）。"""
    client = _make_app()
    r = client.get("/items/")
    assert r.status_code == 200
    assert r.status_code != 307


def test_root_path_not_stripped():
    """根 '/' 不应被 strip（len==1 守卫，docs/redoc 正常）。"""
    app = Starlette(routes=[Route("/", PlainTextResponse("root"))])
    app.middleware("http")(strip_trailing_slash)
    client = TestClient(app)
    assert client.get("/").status_code == 200


# ---------- Slice 2: main.py 配置 ----------


def test_main_redirect_slashes_false():
    """FastAPI() 构造必须传 redirect_slashes=False（禁 307）。"""
    import ast
    tree = ast.parse((Path(__file__).parents[2] / "api" / "main.py").read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            is_fastapi = (isinstance(f, ast.Name) and f.id == "FastAPI") or (
                isinstance(f, ast.Attribute) and f.attr == "FastAPI"
            )
            if is_fastapi:
                for kw in node.keywords:
                    if kw.arg == "redirect_slashes":
                        assert isinstance(kw.value, ast.Constant) and kw.value.value is False, \
                            "redirect_slashes 必须为 False"
                        return
                raise AssertionError("FastAPI() 缺 redirect_slashes=False")
    raise AssertionError("FastAPI() 构造未找到")


def test_main_registers_strip_middleware():
    """main.py 必须注册 strip_trailing_slash middleware。"""
    src = (Path(__file__).parents[2] / "api" / "main.py").read_text()
    assert "strip_trailing_slash" in src, "main.py 未注册 strip_trailing_slash"


# ---------- Slice 3: 10 列表端点路由迁移 "/" → "" ----------

# 列表根端点（@router.*("/")），迁移后应为 @router.*("")
LIST_ENDPOINT_FILES = [
    "api/api/accounts.py",
    "api/api/components.py",
    "api/api/deployment.py",
    "api/api/backtest.py",
    "api/api/dashboard.py",
    "api/api/trading.py",
    "api/api/portfolio.py",
    "api/api/node_graph.py",
]


def test_no_list_endpoint_uses_root_slash():
    """所有列表根端点 @router.*("/") 必须迁移为 @router.*("")。

    路由注册带 slash 会与 redirect_slashes=False 冲突（无 slash 请求 404）。
    """
    import re
    root_slash_re = re.compile(r'@router\.(get|post|put|delete|patch)\(\s*"/"\s*[,)]')
    offenders = []
    for rel in LIST_ENDPOINT_FILES:
        src = (Path(__file__).parents[2] / rel).read_text()
        for m in root_slash_re.finditer(src):
            offenders.append(f"{rel}: {m.group(0).strip()}")
    assert not offenders, "以下列表端点仍用 \"/\" 路由（应迁移为 \"\"）:\n" + "\n".join(offenders)
