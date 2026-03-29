"""
Group CLI 单元测试

测试 ginkgo.client.group_cli 的所有命令：
- create: 创建用户组
- list: 列出用户组
- cat: 显示组详情
- delete: 删除用户组
- add: 添加用户到组
- remove: 从组中移除用户
- members: 列出组成员
- user-groups: 列出用户所属组
"""

import os

os.environ["GINKGO_SKIP_DEBUG_CHECK"] = "1"

from unittest.mock import patch, MagicMock

import pytest
from typer.testing import CliRunner

from ginkgo.client import group_cli
from ginkgo.data.services.base_service import ServiceResult


@pytest.fixture
def cli_runner():
    return CliRunner()


@pytest.fixture
def mock_group_service():
    return MagicMock()


@pytest.fixture
def mock_user_service():
    return MagicMock()


# ============================================================================
# 1. Help 测试
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestGroupCLIHelp:
    """group 命令帮助信息"""

    def test_root_help_shows_commands(self, cli_runner):
        """group --help 显示所有可用子命令"""
        result = cli_runner.invoke(group_cli.app, ["--help"])
        assert result.exit_code == 0
        assert "create" in result.output
        assert "list" in result.output
        assert "cat" in result.output
        assert "delete" in result.output
        assert "add" in result.output
        assert "remove" in result.output
        assert "members" in result.output
        assert "user-groups" in result.output

    def test_create_help_shows_options(self, cli_runner):
        """group create --help 显示创建参数"""
        result = cli_runner.invoke(group_cli.app, ["create", "--help"])
        assert result.exit_code == 0
        assert "--name" in result.output
        assert "--desc" in result.output
        assert "--active" in result.output
        assert "--inactive" in result.output


# ============================================================================
# 2. 主命令正常路径测试
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestGroupCreate:
    """create 命令测试"""

    @patch("ginkgo.data.containers.container")
    def test_create_group_success(self, mock_container, cli_runner, mock_group_service):
        """创建用户组成功"""
        mock_container.user_group_service.return_value = mock_group_service
        mock_group_service.create_group.return_value = ServiceResult.success(
            data={"uuid": "group-uuid-001", "name": "Traders", "description": "Trading team", "is_active": True}
        )
        result = cli_runner.invoke(group_cli.app, ["create", "--name", "Traders", "--desc", "Trading team"])
        assert result.exit_code == 0
        assert "Group created successfully" in result.output
        assert "group-uuid-001" in result.output
        mock_group_service.create_group.assert_called_once()

    @patch("ginkgo.data.containers.container")
    def test_create_group_inactive(self, mock_container, cli_runner, mock_group_service):
        """创建非活跃用户组"""
        mock_container.user_group_service.return_value = mock_group_service
        mock_group_service.create_group.return_value = ServiceResult.success(
            data={"uuid": "group-uuid-002", "name": "Archived", "description": None, "is_active": False}
        )
        result = cli_runner.invoke(group_cli.app, ["create", "--name", "Archived", "--inactive"])
        assert result.exit_code == 0


@pytest.mark.unit
@pytest.mark.cli
class TestGroupList:
    """list 命令测试"""

    @patch("ginkgo.data.containers.container")
    def test_list_groups_success(self, mock_container, cli_runner, mock_group_service):
        """列出用户组成功"""
        mock_container.user_group_service.return_value = mock_group_service
        mock_group_service.list_groups.return_value = ServiceResult.success(
            data={
                "groups": [
                    {"uuid": "group-uuid-001", "name": "Traders", "description": "Trading team", "is_active": True, "update_at": "2025-12-11"}
                ],
                "count": 1,
            }
        )
        result = cli_runner.invoke(group_cli.app, ["list"])
        assert result.exit_code == 0
        assert "Traders" in result.output

    @patch("ginkgo.data.containers.container")
    def test_list_groups_empty(self, mock_container, cli_runner, mock_group_service):
        """无用户组时显示提示"""
        mock_container.user_group_service.return_value = mock_group_service
        mock_group_service.list_groups.return_value = ServiceResult.success(
            data={"groups": [], "count": 0}
        )
        result = cli_runner.invoke(group_cli.app, ["list"])
        assert result.exit_code == 0
        assert "No groups found" in result.output


@pytest.mark.unit
@pytest.mark.cli
class TestGroupCat:
    """cat 命令测试"""

    @patch("ginkgo.data.containers.container")
    def test_cat_group_success(self, mock_container, cli_runner, mock_group_service):
        """显示组详情"""
        mock_container.user_group_service.return_value = mock_group_service
        mock_group_service.get_group.return_value = ServiceResult.success(
            data={
                "uuid": "group-uuid-001",
                "name": "Traders",
                "description": "Trading team",
                "is_active": True,
                "source": "manual",
                "create_at": "2025-12-11",
                "update_at": None,
            }
        )
        result = cli_runner.invoke(group_cli.app, ["cat", "group-uuid-001"])
        assert result.exit_code == 0
        assert "Traders" in result.output
        assert "group-uuid-001" in result.output


@pytest.mark.unit
@pytest.mark.cli
class TestGroupAddRemove:
    """add/remove 用户到组测试"""

    @patch("ginkgo.data.containers.container")
    def test_add_user_to_group_success(self, mock_container, cli_runner, mock_group_service):
        """添加用户到组成功"""
        mock_container.user_group_service.return_value = mock_group_service
        mock_group_service.add_user_to_group.return_value = ServiceResult.success(
            data={"mapping_uuid": "map-uuid-001", "user_uuid": "user-uuid-001", "group_uuid": "group-uuid-001"}
        )
        result = cli_runner.invoke(group_cli.app, ["add", "--user", "user-uuid-001", "--group", "group-uuid-001"])
        assert result.exit_code == 0
        assert "User added to group successfully" in result.output

    @patch("ginkgo.data.containers.container")
    def test_remove_user_from_group_success(self, mock_container, cli_runner, mock_group_service):
        """从组中移除用户成功"""
        mock_container.user_group_service.return_value = mock_group_service
        mock_group_service.remove_user_from_group.return_value = ServiceResult.success(
            data={"deleted_count": 1}
        )
        result = cli_runner.invoke(group_cli.app, ["remove", "--user", "user-uuid-001", "--group", "group-uuid-001"])
        assert result.exit_code == 0
        assert "User removed from group successfully" in result.output


@pytest.mark.unit
@pytest.mark.cli
class TestGroupMembers:
    """members / user-groups 命令测试"""

    @patch("ginkgo.data.containers.container")
    def test_members_success(self, mock_container, cli_runner, mock_group_service):
        """列出组成员成功"""
        mock_container.user_group_service.return_value = mock_group_service
        mock_group_service.get_group.return_value = ServiceResult.success(
            data={"uuid": "group-uuid-001", "name": "Traders"}
        )
        mock_group_service.get_group_members.return_value = ServiceResult.success(
            data={
                "members": [
                    {"user_name": "John Doe", "user_uuid": "user-uuid-001", "mapping_uuid": "map-uuid-001"}
                ],
                "count": 1,
            }
        )
        result = cli_runner.invoke(group_cli.app, ["members", "group-uuid-001"])
        assert result.exit_code == 0
        assert "John Doe" in result.output
        assert "Traders" in result.output

    @patch("ginkgo.data.containers.container")
    def test_user_groups_success(self, mock_container, cli_runner, mock_group_service):
        """列出用户所属组成功"""
        mock_container.user_group_service.return_value = mock_group_service
        mock_group_service.get_user_groups.return_value = ServiceResult.success(
            data={
                "groups": [
                    {"group_uuid": "group-uuid-001", "name": "Traders", "description": "Trading team"}
                ],
                "count": 1,
            }
        )
        result = cli_runner.invoke(group_cli.app, ["user-groups", "user-uuid-001"])
        assert result.exit_code == 0
        assert "Traders" in result.output


# ============================================================================
# 3. 验证/错误测试
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestGroupValidation:
    """参数验证和错误路径测试"""

    def test_create_group_missing_name_fails(self, cli_runner):
        """缺少必选参数 --name 时命令失败"""
        result = cli_runner.invoke(group_cli.app, ["create"])
        assert result.exit_code != 0
        assert "--name" in result.output

    def test_system_group_protection(self, cli_runner):
        """创建名为 System 的组被保护拦截"""
        result = cli_runner.invoke(group_cli.app, ["create", "--name", "System"])
        assert result.exit_code != 0
        assert "Cannot create" in result.output
        assert "System" in result.output

    @patch("ginkgo.data.containers.container")
    def test_create_group_service_error(self, mock_container, cli_runner, mock_group_service):
        """服务层返回错误时命令退出码非零"""
        mock_container.user_group_service.return_value = mock_group_service
        mock_group_service.create_group.return_value = ServiceResult.error(error="Group name already exists")
        result = cli_runner.invoke(group_cli.app, ["create", "--name", "Duplicate"])
        assert result.exit_code != 0
        assert "Group name already exists" in result.output

    @patch("ginkgo.data.containers.container")
    def test_add_user_service_error(self, mock_container, cli_runner, mock_group_service):
        """add 命令服务层错误"""
        mock_container.user_group_service.return_value = mock_group_service
        mock_group_service.add_user_to_group.return_value = ServiceResult.error(error="User not found")
        result = cli_runner.invoke(group_cli.app, ["add", "--user", "bad-uuid", "--group", "group-uuid"])
        assert result.exit_code != 0
        assert "User not found" in result.output


# ============================================================================
# 4. 异常处理测试
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestGroupExceptions:
    """异常处理测试"""

    @patch("ginkgo.data.containers.container")
    def test_create_container_raises_exception(self, mock_container, cli_runner):
        """container 抛出异常时命令优雅退出"""
        mock_container.user_group_service.side_effect = RuntimeError("DB connection failed")
        result = cli_runner.invoke(group_cli.app, ["create", "--name", "TestGroup"])
        assert result.exit_code != 0
        assert "Error creating group" in result.output

    @patch("ginkgo.data.containers.container")
    def test_cat_container_raises_exception(self, mock_container, cli_runner):
        """cat 命令 container 异常时优雅退出"""
        mock_container.user_group_service.side_effect = RuntimeError("Service unavailable")
        result = cli_runner.invoke(group_cli.app, ["cat", "some-uuid"])
        assert result.exit_code != 0
        assert "Error getting group" in result.output

    @patch("ginkgo.data.containers.container")
    def test_delete_container_raises_exception(self, mock_container, cli_runner):
        """delete 命令 container 异常时优雅退出"""
        mock_container.user_group_service.side_effect = RuntimeError("Timeout")
        result = cli_runner.invoke(group_cli.app, ["delete", "some-uuid", "--confirm"])
        assert result.exit_code != 0
        assert "Error deleting group" in result.output
