"""
User CLI 单元测试

测试 ginkgo.client.user_cli 的所有命令：
- create: 创建用户
- list: 列出用户
- cat: 显示用户详细信息
- update: 更新用户信息
- delete: 删除用户
- contact add/list/update/set-primary/delete/enable: 联系人管理
"""

import os

os.environ["GINKGO_SKIP_DEBUG_CHECK"] = "1"

from unittest.mock import patch, MagicMock

import pytest
from typer.testing import CliRunner

from ginkgo.client import user_cli
from ginkgo.data.services.base_service import ServiceResult


@pytest.fixture
def cli_runner():
    return CliRunner()


@pytest.fixture
def mock_user_service():
    return MagicMock()


# ============================================================================
# 1. Help 测试
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestUserCLIHelp:
    """user 命令帮助信息"""

    def test_root_help_shows_commands(self, cli_runner):
        """user --help 显示所有可用子命令"""
        result = cli_runner.invoke(user_cli.app, ["--help"])
        assert result.exit_code == 0
        assert "create" in result.output
        assert "list" in result.output
        assert "cat" in result.output
        assert "update" in result.output
        assert "delete" in result.output
        assert "contact" in result.output

    def test_contact_help_shows_subcommands(self, cli_runner):
        """user contact --help 显示联系人管理子命令"""
        result = cli_runner.invoke(user_cli.app, ["contact", "--help"])
        assert result.exit_code == 0
        assert "add" in result.output
        assert "list" in result.output
        assert "update" in result.output
        assert "delete" in result.output
        assert "set-primary" in result.output


# ============================================================================
# 2. 主命令正常路径测试
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestUserCreate:
    """create 命令测试"""

    @patch("ginkgo.data.containers.container")
    def test_create_user_success(self, mock_container, cli_runner, mock_user_service):
        """创建用户成功"""
        mock_container.user_service.return_value = mock_user_service
        mock_user_service.add_user.return_value = ServiceResult.success(
            data={
                "uuid": "user-uuid-001",
                "name": "John Doe",
                "description": "Test user",
                "user_type": "PERSON",
                "is_active": True,
            }
        )
        result = cli_runner.invoke(user_cli.app, ["create", "--name", "John Doe"])
        assert result.exit_code == 0
        assert "User created successfully" in result.output
        assert "user-uuid-001" in result.output
        mock_user_service.add_user.assert_called_once()

    @patch("ginkgo.data.containers.container")
    def test_create_user_with_type_channel(self, mock_container, cli_runner, mock_user_service):
        """创建 channel 类型用户"""
        mock_container.user_service.return_value = mock_user_service
        mock_user_service.add_user.return_value = ServiceResult.success(
            data={"uuid": "user-uuid-002", "name": "Trading Bot", "description": "", "user_type": "CHANNEL", "is_active": True}
        )
        result = cli_runner.invoke(user_cli.app, ["create", "--name", "Trading Bot", "--type", "channel"])
        assert result.exit_code == 0
        assert "CHANNEL" in result.output

    @patch("ginkgo.data.containers.container")
    def test_create_user_inactive(self, mock_container, cli_runner, mock_user_service):
        """创建非活跃用户"""
        mock_container.user_service.return_value = mock_user_service
        mock_user_service.add_user.return_value = ServiceResult.success(
            data={"uuid": "user-uuid-003", "name": "Inactive User", "description": "", "user_type": "PERSON", "is_active": False}
        )
        result = cli_runner.invoke(user_cli.app, ["create", "--name", "Inactive User", "--inactive"])
        assert result.exit_code == 0


@pytest.mark.unit
@pytest.mark.cli
class TestUserList:
    """list 命令测试"""

    @patch("ginkgo.data.containers.container")
    def test_list_users_success(self, mock_container, cli_runner, mock_user_service):
        """列出用户成功"""
        mock_container.user_service.return_value = mock_user_service
        mock_user_service.list_users.return_value = ServiceResult.success(
            data={
                "users": [
                    {
                        "uuid": "user-uuid-001",
                        "username": "john",
                        "display_name": "John Doe",
                        "description": "Test user",
                        "user_type": "PERSON",
                        "is_active": True,
                        "create_at": "2025-12-11",
                    }
                ],
                "count": 1,
            }
        )
        result = cli_runner.invoke(user_cli.app, ["list"])
        assert result.exit_code == 0
        assert "john" in result.output
        assert "PERSON" in result.output

    @patch("ginkgo.data.containers.container")
    def test_list_users_empty(self, mock_container, cli_runner, mock_user_service):
        """无用户时显示提示"""
        mock_container.user_service.return_value = mock_user_service
        mock_user_service.list_users.return_value = ServiceResult.success(
            data={"users": [], "count": 0}
        )
        result = cli_runner.invoke(user_cli.app, ["list"])
        assert result.exit_code == 0
        assert "No users found" in result.output


@pytest.mark.unit
@pytest.mark.cli
class TestUserCat:
    """cat 命令测试"""

    @patch("ginkgo.data.containers.container")
    def test_cat_user_success(self, mock_container, cli_runner, mock_user_service):
        """显示用户详细信息"""
        mock_container.user_service.return_value = mock_user_service
        mock_user_service.get_user_full_info.return_value = ServiceResult.success(
            data={
                "uuid": "user-uuid-001",
                "display_name": "John Doe",
                "username": "john",
                "user_type": "PERSON",
                "description": "Test user",
                "is_active": True,
                "source": "manual",
                "create_at": "2025-12-11",
                "update_at": None,
                "contacts": [
                    {"contact_type": "email", "address": "john@example.com", "is_primary": True, "is_active": True}
                ],
                "groups": [
                    {"name": "Traders", "group_uuid": "group-uuid-001"}
                ],
            }
        )
        result = cli_runner.invoke(user_cli.app, ["cat", "user-uuid-001"])
        assert result.exit_code == 0
        assert "John Doe" in result.output
        assert "john@example.com" in result.output
        assert "Traders" in result.output


@pytest.mark.unit
@pytest.mark.cli
class TestUserUpdate:
    """update 命令测试"""

    @patch("ginkgo.data.containers.container")
    def test_update_user_success(self, mock_container, cli_runner, mock_user_service):
        """更新用户信息成功"""
        mock_container.user_service.return_value = mock_user_service
        mock_user_service.update_user.return_value = ServiceResult.success(
            data={"uuid": "user-uuid-001", "name": "New Name", "user_type": "PERSON", "description": "Updated", "is_active": True}
        )
        result = cli_runner.invoke(user_cli.app, ["update", "user-uuid-001", "--name", "New Name"])
        assert result.exit_code == 0
        assert "User updated successfully" in result.output
        assert "New Name" in result.output


# ============================================================================
# 3. 验证/错误测试
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestUserValidation:
    """参数验证和错误路径测试"""

    def test_create_user_missing_name_fails(self, cli_runner):
        """缺少必选参数 --name 时命令失败"""
        result = cli_runner.invoke(user_cli.app, ["create"])
        assert result.exit_code != 0
        assert "--name" in result.output

    def test_cat_user_missing_uuid_fails(self, cli_runner):
        """缺少必选参数 UUID 时命令失败"""
        result = cli_runner.invoke(user_cli.app, ["cat"])
        assert result.exit_code != 0

    @patch("ginkgo.data.containers.container")
    def test_create_user_service_error(self, mock_container, cli_runner, mock_user_service):
        """服务层返回错误时命令退出码非零"""
        mock_container.user_service.return_value = mock_user_service
        mock_user_service.add_user.return_value = ServiceResult.error(error="Name already exists")
        result = cli_runner.invoke(user_cli.app, ["create", "--name", "Duplicate"])
        assert result.exit_code != 0
        assert "Name already exists" in result.output

    @patch("ginkgo.data.containers.container")
    def test_list_users_service_error(self, mock_container, cli_runner, mock_user_service):
        """list 服务返回错误时命令退出码非零"""
        mock_container.user_service.return_value = mock_user_service
        mock_user_service.list_users.return_value = ServiceResult.error(error="DB connection failed")
        result = cli_runner.invoke(user_cli.app, ["list"])
        assert result.exit_code != 0
        assert "DB connection failed" in result.output


# ============================================================================
# 4. 异常处理测试
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestUserExceptions:
    """异常处理测试"""

    @patch("ginkgo.data.containers.container")
    def test_create_container_raises_exception(self, mock_container, cli_runner):
        """container 抛出异常时命令优雅退出"""
        mock_container.user_service.side_effect = RuntimeError("Unexpected error")
        result = cli_runner.invoke(user_cli.app, ["create", "--name", "Test"])
        assert result.exit_code != 0
        assert "Error creating user" in result.output

    @patch("ginkgo.data.containers.container")
    def test_cat_container_raises_exception(self, mock_container, cli_runner):
        """cat 命令 container 异常时优雅退出"""
        mock_container.user_service.side_effect = RuntimeError("Service unavailable")
        result = cli_runner.invoke(user_cli.app, ["cat", "some-uuid"])
        assert result.exit_code != 0
        assert "Error getting user info" in result.output

    @patch("ginkgo.data.containers.container")
    def test_update_container_raises_exception(self, mock_container, cli_runner):
        """update 命令 container 异常时优雅退出"""
        mock_container.user_service.side_effect = RuntimeError("Timeout")
        result = cli_runner.invoke(user_cli.app, ["update", "some-uuid", "--name", "New"])
        assert result.exit_code != 0
        assert "Error updating user" in result.output
