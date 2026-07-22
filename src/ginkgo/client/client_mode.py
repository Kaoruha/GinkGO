"""ADR-024 §6 client 模式危险操作拦截。

client 模式下，建表 / migrate / schema 变更等危险操作必须禁止——这类操作应在 server（A）
执行。DB 无专门账号（B 复用 A 的共享凭据直连），无法靠 DB 权限拦 DDL，故在 CLI 层拦截；
API 层作纵深防御（拒绝 client 发起的 DDL）。

诚实限制：B 持共享 DB 凭据，绕过 CLI 直接连 server DB 做 DDL 无法阻止——拦截是
"提高门槛 + 明确意图"，非绝对墙（见 ADR-024 §6 / Consequences）。
"""
from ginkgo.libs import GCONF

# client 模式禁止的命令（DDL / schema 变更类）。按需扩展。
CLIENT_FORBIDDEN_COMMANDS = {
    "init",  # create_all_tables（建表 / DDL）
    # "migrate",  # alembic schema 迁移（当前未注册 CLI；注册后加入此集合）
}


def assert_command_allowed_in_client(command_name: str) -> None:
    """client 模式下，若命令属危险类（DDL / schema 变更）则拒绝：明确报错 + 指向 server。

    local 模式直接放行。在 client 模式下需要守护的命令体开头调用即可。拒绝走
    ``SystemExit(1)``（响亮失败，非静默——ADR-022 §3）。
    """
    if GCONF.MODE != "client":
        return
    if command_name not in CLIENT_FORBIDDEN_COMMANDS:
        return
    from rich.console import Console

    console = Console()
    console.print(
        f"[red]:x: `ginkgo {command_name}` 在 client 模式被禁止"
        f"（危险操作：建表 / schema 变更）。[/red]"
    )
    console.print(
        "[yellow]请在 server（A）执行：数据库 schema 变更须由 server 侧发起（ADR-024 §6）。[/yellow]"
    )
    raise SystemExit(1)
