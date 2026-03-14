# Upstream: LiveAccountService (实盘账号业务服务)
# Downstream: BaseCRUD (继承提供标准CRUD能力)、MLiveAccount (MySQL实盘账号模型)、EncryptionService (API凭证加密)
# Role: LiveAccountCRUD实盘账号CRUD操作提供加密存储和账号管理功能


from typing import List, Optional, Union, Any, Dict
import pandas as pd
from datetime import datetime
from sqlalchemy import and_, or_, update

from ginkgo.data.crud.base_crud import BaseCRUD
from ginkgo.data.models.model_live_account import MLiveAccount, ExchangeType, EnvironmentType, AccountStatusType
from ginkgo.enums import SOURCE_TYPES
from ginkgo.libs import GLOG
from ginkgo.data.access_control import restrict_crud_access


@restrict_crud_access
class LiveAccountCRUD(BaseCRUD[MLiveAccount]):
    """
    实盘账号CRUD操作

    支持API凭证加密存储、账号管理和状态更新：
    - 创建账号时自动加密API凭证
    - 查询账号时返回脱敏信息
    - 更新账号状态和验证信息
    """

    _model_class = MLiveAccount

    def __init__(self):
        super().__init__(MLiveAccount)
        self._encryption_service = None

    def _get_encryption_service(self):
        """延迟加载加密服务"""
        if self._encryption_service is None:
            from ginkgo.data.services.encryption_service import get_encryption_service
            self._encryption_service = get_encryption_service()
        return self._encryption_service

    def _get_enum_mappings(self) -> Dict[str, Any]:
        """定义字段到枚举的映射"""
        return {
            'source': SOURCE_TYPES,
        }

    def _get_field_config(self) -> dict:
        """定义LiveAccount数据的字段配置"""
        return {
            # 交易所类型 - 字符串
            'exchange': {
                'type': 'string',
                'min': 2,
                'max': 20
            },
            # 环境类型 - 字符串
            'environment': {
                'type': 'string',
                'min': 5,
                'max': 20
            },
            # 账号名称 - 非空字符串
            'name': {
                'type': 'string',
                'min': 1,
                'max': 100
            },
            # API凭证 - 加密存储
            'api_key': {
                'type': 'string',
                'min': 1,
                'max': 500
            },
            'api_secret': {
                'type': 'string',
                'min': 1,
                'max': 500
            },
            'passphrase': {
                'type': 'string',
                'min': 0,
                'max': 500,
                'required': False
            },
            # 状态字段
            'status': {
                'type': 'string',
                'min': 5,
                'max': 20
            }
        }

    def _create_from_params(self, **kwargs) -> MLiveAccount:
        """从参数创建MLiveAccount实例"""
        return MLiveAccount(**kwargs)

    def _convert_input_item(self, item: Any) -> Optional[MLiveAccount]:
        """转换对象为MLiveAccount"""
        if isinstance(item, MLiveAccount):
            return item
        return None

    def _convert_models_to_business_objects(self, models: List) -> List:
        """转换模型为业务对象"""
        return models

    def _convert_output_items(self, items: List[MLiveAccount], output_type: str = "model") -> List[Any]:
        """转换MLiveAccount对象供业务层使用"""
        return items

    def _process_dataframe_output(self, df: pd.DataFrame) -> pd.DataFrame:
        """处理DataFrame输出，隐藏敏感信息"""
        # 隐藏API凭证列
        sensitive_columns = ['api_key', 'api_secret', 'passphrase']
        for col in sensitive_columns:
            if col in df.columns:
                df[col] = '***HIDDEN***'
        return df

    # ==================== 实盘账号专用CRUD操作 ====================

    def add_live_account(
        self,
        user_id: str,
        exchange: str,
        name: str,
        api_key: str,
        api_secret: str,
        passphrase: Optional[str] = None,
        environment: str = "testnet",
        description: Optional[str] = None
    ) -> MLiveAccount:
        """
        添加实盘账号（自动加密API凭证）

        Args:
            user_id: 用户ID
            exchange: 交易所类型 (okx/binance)
            name: 账号名称
            api_key: API Key（明文，将自动加密）
            api_secret: API Secret（明文，将自动加密）
            passphrase: Passphrase（明文，将自动加密，OKX需要）
            environment: 环境 (production/testnet)
            description: 账号描述

        Returns:
            MLiveAccount: 创建的账号对象

        Raises:
            ValueError: 当加密失败或参数无效时
        """
        # 加密API凭证
        encryption_service = self._get_encryption_service()

        # 加密api_key
        key_result = encryption_service.encrypt_credential(api_key)
        if not key_result.success:
            raise ValueError(f"Failed to encrypt api_key: {key_result.error}")
        encrypted_key = key_result.data["encrypted_credential"]

        # 加密api_secret
        secret_result = encryption_service.encrypt_credential(api_secret)
        if not secret_result.success:
            raise ValueError(f"Failed to encrypt api_secret: {secret_result.error}")
        encrypted_secret = secret_result.data["encrypted_credential"]

        # 加密passphrase（如果提供）
        encrypted_passphrase = None
        if passphrase:
            passphrase_result = encryption_service.encrypt_credential(passphrase)
            if passphrase_result.success:
                encrypted_passphrase = passphrase_result.data["encrypted_credential"]

        # 创建账号对象
        account = MLiveAccount(
            user_id=user_id,
            exchange=ExchangeType.from_str(exchange),
            name=name,
            api_key=encrypted_key,
            api_secret=encrypted_secret,
            passphrase=encrypted_passphrase,
            environment=EnvironmentType.from_str(environment),
            description=description,
            status=AccountStatusType.DISABLED,  # 新账号默认禁用，需验证后启用
            source=SOURCE_TYPES.LIVE
        )

        # 保存到数据库
        return self.add(account)

    def get_live_account_by_user_id(
        self,
        user_id: str,
        exchange: Optional[str] = None,
        environment: Optional[str] = None,
        status: Optional[str] = None,
        include_deleted: bool = False
    ) -> List[MLiveAccount]:
        """
        获取用户的实盘账号列表

        Args:
            user_id: 用户ID
            exchange: 过滤交易所类型
            environment: 过滤环境类型
            status: 过滤账号状态
            include_deleted: 是否包含已删除的账号

        Returns:
            List[MLiveAccount]: 账号列表
        """
        filters = {"user_id": user_id}
        if not include_deleted:
            filters["is_del"] = False

        results = self.find(filters=filters, as_dataframe=False)

        # 应用额外过滤
        filtered_results = []
        for account in results:
            if exchange and account.exchange != exchange:
                continue
            if environment and account.environment != environment:
                continue
            if status and account.status != status:
                continue
            filtered_results.append(account)

        return filtered_results

    def get_live_account_by_uuid(self, uuid: str, include_credentials: bool = False) -> Optional[MLiveAccount]:
        """
        根据UUID获取账号

        Args:
            uuid: 账号UUID
            include_credentials: 是否包含加密的凭证信息

        Returns:
            MLiveAccount or None: 账号对象
        """
        results = self.find(filters={"uuid": uuid, "is_del": False}, as_dataframe=False)
        if not results:
            return None
        return results[0]

    def update_live_account(
        self,
        uuid: str,
        name: Optional[str] = None,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        passphrase: Optional[str] = None,
        description: Optional[str] = None,
        encrypt_new_credentials: bool = True
    ) -> Optional[MLiveAccount]:
        """
        更新实盘账号信息

        Args:
            uuid: 账号UUID
            name: 新的账号名称
            api_key: 新的API Key（明文，将自动加密）
            api_secret: 新的API Secret（明文，将自动加密）
            passphrase: 新的Passphrase（明文，将自动加密）
            description: 新的描述
            encrypt_new_credentials: 是否加密新凭证

        Returns:
            MLiveAccount or None: 更新后的账号对象
        """
        account = self.get_live_account_by_uuid(uuid)
        if not account:
            GLOG.WARN(f"Account not found: {uuid}")
            return None

        # 准备更新字典
        updates = {}
        if name is not None:
            updates["name"] = name
        if description is not None:
            updates["description"] = description

        # 更新加密凭证
        if encrypt_new_credentials:
            encryption_service = self._get_encryption_service()

            if api_key is not None:
                result = encryption_service.encrypt_credential(api_key)
                if result.success:
                    updates["api_key"] = result.data["encrypted_credential"]

            if api_secret is not None:
                result = encryption_service.encrypt_credential(api_secret)
                if result.success:
                    updates["api_secret"] = result.data["encrypted_credential"]

            if passphrase is not None:
                result = encryption_service.encrypt_credential(passphrase)
                if result.success:
                    updates["passphrase"] = result.data["encrypted_credential"]

        if updates:
            self.modify(filters={"uuid": uuid}, updates=updates)

        return self.get_live_account_by_uuid(uuid)

    def update_status(
        self,
        uuid: str,
        status: str,
        validation_message: Optional[str] = None
    ) -> Optional[MLiveAccount]:
        """
        更新账号状态

        Args:
            uuid: 账号UUID
            status: 新状态 (enabled/disabled/connecting/disconnected/error)
            validation_message: 验证消息

        Returns:
            MLiveAccount or None: 更新后的账号对象
        """
        account = self.get_live_account_by_uuid(uuid)
        if not account:
            GLOG.WARN(f"Account not found: {uuid}")
            return None

        # 准备更新字典
        updates = {"status": status}

        if validation_message:
            updates["validation_status"] = validation_message
        if status == AccountStatusType.ENABLED:
            updates["last_validated_at"] = datetime.now()

        self.modify(filters={"uuid": uuid}, updates=updates)
        return self.get_live_account_by_uuid(uuid)

    def delete_live_account(self, uuid: str, cascade: bool = True) -> bool:
        """
        删除实盘账号（软删除）

        Args:
            uuid: 账号UUID
            cascade: 是否级联删除相关记录

        Returns:
            bool: 是否删除成功

        Note:
            级联删除时会检查是否有Portfolio绑定
        """
        account = self.get_live_account_by_uuid(uuid)
        if not account:
            GLOG.WARN(f"Account not found: {uuid}")
            return False

        # 检查是否有Portfolio绑定
        if cascade:
            from ginkgo.data.models.model_portfolio import MPortfolio
            # TODO: 检查是否有Portfolio使用此账号
            # 如果有，需要先解绑或提示用户
            pass

        # 软删除
        self.modify(filters={"uuid": uuid}, updates={"is_del": True})
        GLOG.INFO(f"Live account soft deleted: {uuid}")
        return True

    def get_decrypted_credentials(self, uuid: str) -> Optional[Dict[str, str]]:
        """
        获取解密后的API凭证（谨慎使用）

        Args:
            uuid: 账号UUID

        Returns:
            Dict with keys: api_key, api_secret, passphrase (optional) or None
        """
        account = self.get_live_account_by_uuid(uuid, include_credentials=True)
        if not account:
            return None

        encryption_service = self._get_encryption_service()

        # 解密api_key
        key_result = encryption_service.decrypt_credential(account.api_key)
        if not key_result.success:
            GLOG.ERROR(f"Failed to decrypt api_key: {key_result.error}")
            return None

        # 解密api_secret
        secret_result = encryption_service.decrypt_credential(account.api_secret)
        if not secret_result.success:
            GLOG.ERROR(f"Failed to decrypt api_secret: {secret_result.error}")
            return None

        credentials = {
            "api_key": key_result.data["credential"],
            "api_secret": secret_result.data["credential"],
        }

        # 解密passphrase（如果存在）
        if account.passphrase:
            passphrase_result = encryption_service.decrypt_credential(account.passphrase)
            if passphrase_result.success:
                credentials["passphrase"] = passphrase_result.data["credential"]

        return credentials

    def get_live_accounts_by_user(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        exchange: Optional[str] = None,
        environment: Optional[str] = None,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        分页获取用户的实盘账号列表

        Args:
            user_id: 用户ID
            page: 页码（从1开始）
            page_size: 每页数量
            exchange: 过滤交易所类型
            environment: 过滤环境类型
            status: 过滤账号状态

        Returns:
            Dict with keys: accounts (List), total (int), page (int), page_size (int)
        """
        filters = {"user_id": user_id, "is_del": False}
        all_accounts = self.find(filters=filters, as_dataframe=False)

        # 应用过滤
        filtered_accounts = []
        for account in all_accounts:
            if exchange and account.exchange != exchange:
                continue
            if environment and account.environment != environment:
                continue
            if status and account.status != status:
                continue
            filtered_accounts.append(account)

        # 分页
        total = len(filtered_accounts)
        start = (page - 1) * page_size
        end = start + page_size
        paged_accounts = filtered_accounts[start:end]

        return {
            "accounts": paged_accounts,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
