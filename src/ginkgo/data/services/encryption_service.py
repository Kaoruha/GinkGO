# Upstream: LiveAccountService, BrokerManager (API凭证加密存储)
# Downstream: cryptography.Fernet (对称加密)
# Role: API凭证加密解密服务，使用Fernet对称加密保护敏感信息


import base64
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken

from ginkgo.libs import GLOG, GCONF
from ginkgo.data.services.base_service import ServiceResult


class EncryptionService:
    """
    API凭证加密服务

    使用Fernet对称加密算法保护API Key、Secret等敏感信息。
    加密密钥存储在~/.ginkgo/secure.yml的encryption_key字段。
    """

    def __init__(self, encryption_key: Optional[str | bytes] = None):
        """
        初始化加密服务，加载加密密钥

        Args:
            encryption_key: 可选的加密密钥（用于测试），如果不提供则从配置加载
        """
        self._key: Optional[str] = None
        self._fernet: Optional[Fernet] = None
        if encryption_key:
            self._init_with_key(encryption_key)
        else:
            self._load_encryption_key()

    def _init_with_key(self, encryption_key: str | bytes) -> None:
        """使用指定密钥初始化（用于测试）"""
        try:
            # 确保密钥是有效的base64编码字符串
            if isinstance(encryption_key, bytes):
                key_str = encryption_key.decode('utf-8')
            else:
                key_str = encryption_key

            # 补齐base64 padding
            if not key_str.endswith('='):
                key_str += '=' * (4 - len(key_str) % 4)

            self._key = key_str
            self._fernet = Fernet(key_str.encode('utf-8'))
        except Exception as e:
            GLOG.ERROR(f"[Encryption] Failed to initialize with provided key: {e}")
            raise

    def _load_encryption_key(self) -> None:
        """
        从配置文件加载加密密钥

        优先级：
        1. secure.yml中的encryption_key字段
        2. 环境变量GINKGO_ENCRYPTION_KEY
        3. 自动生成新密钥（仅用于开发环境）
        """
        try:
            # 从secure.yml读取
            secure_data = GCONF._read_secure()
            self._key = secure_data.get("encryption_key")

            if self._key:
                # 确保密钥是有效的base64编码
                if not self._key.endswith('='):
                    # 补齐base64 padding
                    self._key += '=' * (4 - len(self._key) % 4)
                self._fernet = Fernet(self._key.encode())
                GLOG.INFO(f"[Encryption] Encryption key loaded from secure.yml")
            else:
                GLOG.ERROR(f"[Encryption] encryption_key not found in secure.yml")
                raise ValueError("encryption_key not configured")

        except Exception as e:
            GLOG.ERROR(f"[Encryption] Failed to load encryption key: {e}")
            raise

    def encrypt_credential(self, credential: str) -> ServiceResult:
        """
        加密API凭证

        Args:
            credential: 明文凭证（API Key、Secret等）

        Returns:
            ServiceResult: 成功时data.encrypted_credential包含密文
        """
        if not self._fernet:
            return ServiceResult.error(
                error="Encryption service not initialized",
                message="Encryption key not loaded"
            )

        try:
            # Fernet要求输入为bytes
            credential_bytes = credential.encode('utf-8')
            encrypted = self._fernet.encrypt(credential_bytes)
            # Fernet已经返回base64编码的bytes，直接转为字符串
            encrypted_str = encrypted.decode('utf-8')

            return ServiceResult.success(
                data={"encrypted_credential": encrypted_str},
                message="Credential encrypted successfully"
            )

        except Exception as e:
            GLOG.ERROR(f"[Encryption] Encryption failed: {e}")
            return ServiceResult.error(
                error=str(e),
                message="Failed to encrypt credential"
            )

    def decrypt_credential(self, encrypted_credential: str) -> ServiceResult:
        """
        解密API凭证

        Args:
            encrypted_credential: 加密的凭证字符串

        Returns:
            ServiceResult: 成功时data.credential包含明文
        """
        if not self._fernet:
            return ServiceResult.error(
                error="Encryption service not initialized",
                message="Encryption key not loaded"
            )

        try:
            # Fernet token已经是base64格式，直接转为bytes解密
            encrypted_bytes = encrypted_credential.encode('utf-8')
            # Fernet解密
            decrypted = self._fernet.decrypt(encrypted_bytes)
            credential = decrypted.decode('utf-8')

            return ServiceResult.success(
                data={"credential": credential},
                message="Credential decrypted successfully"
            )

        except InvalidToken:
            GLOG.ERROR(f"[Encryption] Decryption failed: Invalid token (wrong key or corrupted data)")
            return ServiceResult.error(
                error="Invalid token",
                message="Decryption failed - invalid encrypted data or wrong key"
            )

        except Exception as e:
            GLOG.ERROR(f"[Encryption] Decryption failed: {e}")
            return ServiceResult.error(
                error=str(e),
                message="Failed to decrypt credential"
            )

    def verify_encryption_key(self) -> bool:
        """
        验证加密密钥是否有效

        Returns:
            bool: 密钥是否可用
        """
        return self._fernet is not None

    # 测试辅助方法
    def encrypt(self, plaintext: str) -> str:
        """
        直接加密（用于测试）

        Args:
            plaintext: 明文字符串

        Returns:
            str: base64编码的密文字符串（Fernet格式）
        """
        if not self._fernet:
            raise RuntimeError("Encryption service not initialized")
        credential_bytes = plaintext.encode('utf-8')
        encrypted = self._fernet.encrypt(credential_bytes)
        # Fernet.encrypt已经返回base64编码的bytes，直接转为字符串
        return encrypted.decode('utf-8')

    def decrypt(self, encrypted_credential: str) -> str:
        """
        直接解密（用于测试）

        Args:
            encrypted_credential: base64编码的密文字符串（Fernet格式）

        Returns:
            str: 解密后的明文

        Raises:
            InvalidToken: 如果密钥错误或数据损坏
        """
        if not self._fernet:
            raise RuntimeError("Encryption service not initialized")
        try:
            # Fernet token已经是base64格式，直接转为bytes解密
            encrypted_bytes = encrypted_credential.encode('utf-8')
            decrypted = self._fernet.decrypt(encrypted_bytes)
            return decrypted.decode('utf-8')
        except (InvalidToken, ValueError) as e:
            # 重新抛出InvalidToken以保持一致的异常类型
            raise InvalidToken("Invalid encrypted data")

    def rotate_encryption_key(self, new_key: str) -> ServiceResult:
        """
        轮换加密密钥（未来功能）

        Args:
            new_key: 新的加密密钥（base64编码）

        Returns:
            ServiceResult: 轮换结果
        """
        try:
            # 验证新密钥格式
            if not new_key.endswith('='):
                new_key += '=' * (4 - len(new_key) % 4)
            Fernet(new_key.encode())  # 验证密钥有效性

            # TODO: 实现密钥轮换逻辑
            # 1. 使用旧密钥解密所有数据
            # 2. 使用新密钥重新加密
            # 3. 更新secure.yml中的encryption_key

            return ServiceResult.error(
                error="Not implemented",
                message="Key rotation is not yet implemented"
            )

        except Exception as e:
            return ServiceResult.error(
                error=str(e),
                message="Invalid new encryption key"
            )


# 全局单例实例
_encryption_service_instance: Optional[EncryptionService] = None


def get_encryption_service() -> EncryptionService:
    """
    获取加密服务单例

    Returns:
        EncryptionService: 加密服务实例
    """
    global _encryption_service_instance
    if _encryption_service_instance is None:
        _encryption_service_instance = EncryptionService()
    return _encryption_service_instance
