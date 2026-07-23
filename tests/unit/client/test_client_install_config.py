"""install.py client 分支烟测 (ADR-024 Task #7)。

覆盖闭环：
1. ``write_client_config`` 产 client 版 config.yml（mode:client + api_* 键）；secure.yml 由独立的 ``write_client_secure`` 写
2. ``write_client_secure`` 从 secure.template 拷贝并把数据面 DB host 全指向 server（api_host）；已存在则跳过（保护凭据）
3. ``GCONF.API_HOST/API_PORT/API_TLS/MODE`` 从 client config.yml 读回生效（``_get_config`` mtime 自动重载）
4. ``ginkgo config set api_host <host>`` 改 config.yml 后 GCONF 读到新值（install 写 + config 改 闭环）

纯文件 IO，不触 Docker/DB/网络。install.py 是仓库根脚本非包，按路径加载取 ``write_client_config`` / ``write_client_secure``。
"""
import importlib.util
from pathlib import Path

import pytest
import yaml


def _repo_root() -> Path:
    """从本测试向上找含 ``install.py`` 的目录（worktree 根），不硬编码 parents 下标。"""
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "install.py").exists():
            return p
        p = p.parent
    raise RuntimeError("install.py 未在上级目录中找到")


@pytest.fixture(scope="module")
def install_mod():
    spec = importlib.util.spec_from_file_location("_install_under_test", _repo_root() / "install.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # main() 仅 __main__ 跑，import 无副作用
    return mod


@pytest.fixture
def ginkgo_dir(tmp_path, monkeypatch):
    """隔离 GINKGO_DIR：config 写 tmp，绝不碰用户真实 ~/.ginkgo。"""
    gd = tmp_path / ".ginkgo"
    gd.mkdir()
    monkeypatch.setenv("GINKGO_DIR", str(gd))
    # env 优先级高于 config.yml，清掉测试机可能存在的同名 env 防污染
    for k in ("GINKGO_MODE", "GINKGO_API_HOST", "GINKGO_API_PORT", "GINKGO_API_TLS"):
        monkeypatch.delenv(k, raising=False)
    return gd


def _reset_gconf_cache():
    """GCONF 单例 mtime/存在性缓存跨用例残留，强制重新探测 + 重读文件。

    注意 ``_get_config`` 的读门是 ``if self._has_local_config:``（config.py:361），
    若残留 None/False 会直接返默认值、**绕过** _read_config。故这里：先清存在性标记为
    None（未知），再显式调 ``_read_config()``——它内部 ``generate_config_file`` 会按
    真实文件存在性重置 ``_has_local_config=True`` 并重读 tmp/config.yml。
    """
    from ginkgo.libs import GCONF
    GCONF._has_local_config = None
    GCONF._has_local_secure = None
    GCONF._config_cache = {}
    GCONF._config_mtime = 0
    GCONF._read_config()


def test_write_client_config_writes_client_block_no_secure(install_mod, ginkgo_dir):
    """client 瘦装只落 config.yml，不落 secure.yml（ADR-024 §1）。"""
    path = install_mod.write_client_config(str(ginkgo_dir), "api.example.com", "9000", True)
    cfg = yaml.safe_load((ginkgo_dir / "config.yml").read_text())
    assert cfg["mode"] == "client"
    assert cfg["api_host"] == "api.example.com"
    assert cfg["api_port"] == "9000"
    assert cfg["api_tls"] == "true"
    assert not (ginkgo_dir / "secure.yml").exists()
    assert path == str(ginkgo_dir / "config.yml")


def test_gconf_reads_client_config_back(ginkgo_dir, install_mod):
    """install 写完 client config.yml，GCONF 立即可读（无需手动清缓存——mtime 重载）。"""
    install_mod.write_client_config(str(ginkgo_dir), "bt.svc.local", "8443", True)
    _reset_gconf_cache()
    from ginkgo.libs import GCONF
    assert GCONF.MODE == "client"
    assert GCONF.API_HOST == "bt.svc.local"
    assert GCONF.API_PORT == "8443"
    assert GCONF.API_TLS is True


def test_config_set_api_host_round_trips(ginkgo_dir, install_mod):
    """install 先落 client config（api_host=old）→ config set 改 new → 文件层 + GCONF 层都生效。"""
    install_mod.write_client_config(str(ginkgo_dir), "old.host", "8000", False)
    _reset_gconf_cache()
    from typer.testing import CliRunner
    from ginkgo.client.config_cli import app

    result = CliRunner().invoke(app, ["set", "api_host", "new.host"])
    assert result.exit_code == 0, result.output
    # 文件层
    cfg = yaml.safe_load((ginkgo_dir / "config.yml").read_text())
    assert cfg["api_host"] == "new.host"
    # GCONF 层（mtime 自动重载，config set 写后下次读即新值）
    from ginkgo.libs import GCONF
    assert GCONF.API_HOST == "new.host"


def test_config_set_mode_rejects_invalid(ginkgo_dir, install_mod):
    """非法 mode（server）不落盘，保持 client——防误装成不存在的模式。"""
    install_mod.write_client_config(str(ginkgo_dir), "h", "8000", False)
    _reset_gconf_cache()
    from typer.testing import CliRunner
    from ginkgo.client.config_cli import app

    result = CliRunner().invoke(app, ["set", "mode", "server"])
    assert "仅支持 local | client" in result.output
    cfg = yaml.safe_load((ginkgo_dir / "config.yml").read_text())
    assert cfg["mode"] == "client"  # 未被改成 server


def test_write_client_secure_repoints_db_hosts_to_server(install_mod, ginkgo_dir):
    """client secure.yml 从 secure.template 拷贝，数据面 DB host 全指向 server（api_host）。ADR-024 §4。

    B 复用 A 的共享 DB 凭据直连——host 指向 A，账号/密码/库保持模板占位（装完 config set 填真凭据）。
    """
    template = _repo_root() / "src" / "ginkgo" / "config" / "secure.template"
    path = install_mod.write_client_secure(str(ginkgo_dir), "a.example.com", str(template))
    assert path == str(ginkgo_dir / "secure.yml")

    sec = yaml.safe_load((ginkgo_dir / "secure.yml").read_text())
    db = sec["database"]
    for engine in ("clickhouse", "mysql", "mongodb", "redis", "kafka"):
        assert db[engine]["host"] == "a.example.com", engine
    # 凭据 / 库名来自模板，不被改动（装完由 config set 填真实值）
    assert db["mysql"]["username"] == "ginkgoadm"
    assert db["clickhouse"]["port"] == 8123


def test_write_client_secure_skips_if_exists(install_mod, ginkgo_dir):
    """已存在 secure.yml 则跳过、不覆盖——保护用户已填的真实凭据。"""
    template = _repo_root() / "src" / "ginkgo" / "config" / "secure.template"
    pre = "database: {mysql: {host: kept.host, username: real}}\n"
    (ginkgo_dir / "secure.yml").write_text(pre)

    install_mod.write_client_secure(str(ginkgo_dir), "a.example.com", str(template))

    sec = yaml.safe_load((ginkgo_dir / "secure.yml").read_text())
    assert sec["database"]["mysql"]["host"] == "kept.host"  # 未被 repoint
    assert sec["database"]["mysql"]["username"] == "real"  # 未被覆盖


def test_write_client_config_skips_if_exists(install_mod, ginkgo_dir):
    """已存在 config.yml 则跳过、不覆盖——保护用户安装后用 ``config set`` 改过的 api_host/port。

    与 ``write_client_secure`` 对称：重跑 install 不应把 api_host 回退到安装期占位值。
    要重新指向 server 用 ``ginkgo config set api_host <host>``。
    """
    pre = "mode: client\napi_host: user.set.host\napi_port: '9999'\napi_tls: 'false'\n"
    (ginkgo_dir / "config.yml").write_text(pre)

    install_mod.write_client_config(str(ginkgo_dir), "install.default.host", "8000", False)

    cfg = yaml.safe_load((ginkgo_dir / "config.yml").read_text())
    assert cfg["api_host"] == "user.set.host"  # 未被回退
    assert cfg["api_port"] == "9999"
    assert cfg["mode"] == "client"
