"""#5633: Account 响应字段统一为 "uuid"（对齐 MLiveAccount.to_dict() 及其他模块）。

根因: LiveAccountService.create_account / update_account_status 手动构造 data dict
时用 key "account_uuid"，而 MLiveAccount.to_dict()（get/list/update 经此）统一用 "uuid"，
导致 create/update_status 响应与其余端点字段名不一致，前端需按模块特判。

注: service 方法 *参数名* account_uuid（validate_account/update_account 等）是内部契约，
保留不动；本测试只钉 *响应 data 字段名* 必须为 "uuid"。
"""
import pytest
from unittest.mock import Mock

from ginkgo.data.services.live_account_service import LiveAccountService
from ginkgo.data.models.model_live_account import (
    MLiveAccount,
    ExchangeType,
    AccountStatusType,
)


class TestAccountResponseUuidField:
    """#5633: Account 响应 data 必须用 "uuid" 字段（非 "account_uuid"）。"""

    @pytest.fixture
    def mock_crud_create(self):
        mock = Mock()
        account = Mock(spec=MLiveAccount)
        account.uuid = "acc-uuid-123"
        mock.add_live_account.return_value = account
        mock.get_live_account_by_user_id.return_value = []
        return mock

    @pytest.fixture
    def mock_crud_update_status(self):
        mock = Mock()
        existing = Mock(spec=MLiveAccount)
        mock.get_live_account_by_uuid.return_value = existing
        updated = Mock(spec=MLiveAccount)
        updated.uuid = "acc-uuid-456"
        updated.status = AccountStatusType.ENABLED
        mock.update_status.return_value = updated
        return mock

    @pytest.mark.unit
    def test_create_account_returns_uuid_field(self, mock_crud_create):
        """create_account 响应 data 含 'uuid' key，不含 'account_uuid'。"""
        service = LiveAccountService(live_account_crud=mock_crud_create)
        result = service.create_account(
            user_id="u1",
            exchange=ExchangeType.OKX,
            name="n",
            api_key="k",
            api_secret="s",
            passphrase="p",
            environment="testnet",
            auto_validate=False,
        )
        assert result["success"] is True
        assert result["data"]["uuid"] == "acc-uuid-123"
        assert "account_uuid" not in result["data"], "不应再用 account_uuid 字段名"

    @pytest.mark.unit
    def test_update_account_status_returns_uuid_field(self, mock_crud_update_status):
        """update_account_status 响应 data 含 'uuid' key。

        注意调用 kwarg account_uuid 是 service 签名参数名（内部契约，保留），
        响应字段才统一为 uuid。
        """
        service = LiveAccountService(live_account_crud=mock_crud_update_status)
        result = service.update_account_status(
            account_uuid="acc-uuid-456",
            status=AccountStatusType.ENABLED,
        )
        assert result["success"] is True
        assert result["data"]["uuid"] == "acc-uuid-456"
        assert "account_uuid" not in result["data"]
