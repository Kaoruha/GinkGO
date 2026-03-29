"""
Unit Tests for EncryptionService

Tests for Fernet-based encryption service used to secure API credentials.
"""

import pytest
from cryptography.fernet import Fernet
from ginkgo.data.services.encryption_service import EncryptionService, get_encryption_service


class TestEncryptionService:
    """EncryptionService单元测试"""

    @pytest.fixture
    def encryption_service(self):
        """创建EncryptionService实例"""
        # 使用测试密钥
        test_key = b'Z7vW9yX1kP3mQ8sT2nR4vL6wO5iU8jA1fB3dG6hJ9kM='
        return EncryptionService(encryption_key=test_key)

    def test_encrypt_decrypt_success(self, encryption_service):
        """测试加密解密成功"""
        plaintext = "my-api-secret-key-12345"

        # 加密
        encrypted = encryption_service.encrypt(plaintext)
        assert encrypted is not None
        assert encrypted != plaintext
        assert isinstance(encrypted, str)

        # 解密
        decrypted = encryption_service.decrypt(encrypted)
        assert decrypted == plaintext

    def test_encrypt_different_results(self, encryption_service):
        """测试相同明文多次加密产生不同结果（由于IV）"""
        plaintext = "test-secret"

        encrypted1 = encryption_service.encrypt(plaintext)
        encrypted2 = encryption_service.encrypt(plaintext)

        # 加密结果应该不同（因为Fernet使用随机IV）
        assert encrypted1 != encrypted2

        # 但解密后应该相同
        assert encryption_service.decrypt(encrypted1) == plaintext
        assert encryption_service.decrypt(encrypted2) == plaintext

    def test_decrypt_invalid_token(self, encryption_service):
        """测试解密无效token"""
        invalid_token = "invalid-encrypted-token"

        with pytest.raises(Exception) as exc_info:
            encryption_service.decrypt(invalid_token)
        assert "Invalid" in str(exc_info.value) or "Fernet" in str(exc_info.value)

    def test_decrypt_tampered_data(self, encryption_service):
        """测试解密被篡改的数据"""
        plaintext = "original-secret"
        encrypted = encryption_service.encrypt(plaintext)

        # 篡改加密数据
        tampered = encrypted[:-5] + "XXXXX"

        with pytest.raises(Exception):
            encryption_service.decrypt(tampered)

    def test_encrypt_empty_string(self, encryption_service):
        """测试加密空字符串"""
        encrypted = encryption_service.encrypt("")
        assert encrypted is not None
        assert encryption_service.decrypt(encrypted) == ""

    def test_encrypt_special_characters(self, encryption_service):
        """测试加密特殊字符"""
        special_chars = "!@#$%^&*()_+-=[]{}|;':\",./<>?"
        encrypted = encryption_service.encrypt(special_chars)
        assert encryption_service.decrypt(encrypted) == special_chars

    def test_encrypt_unicode(self, encryption_service):
        """测试加密Unicode字符"""
        unicode_text = "测试中文🚀💻🔒"
        encrypted = encryption_service.encrypt(unicode_text)
        assert encryption_service.decrypt(encrypted) == unicode_text

    def test_encrypt_api_credentials(self, encryption_service):
        """测试加密API凭证（实际使用场景）"""
        credentials = {
            "api_key": "okx-live-api-key-12345",
            "api_secret": "secret-key-abcde-67890-fghij",
            "passphrase": "my-passphrase-123"
        }

        # 加密各字段
        encrypted_key = encryption_service.encrypt(credentials["api_key"])
        encrypted_secret = encryption_service.encrypt(credentials["api_secret"])
        encrypted_pass = encryption_service.encrypt(credentials["passphrase"])

        # 解密验证
        assert encryption_service.decrypt(encrypted_key) == credentials["api_key"]
        assert encryption_service.decrypt(encrypted_secret) == credentials["api_secret"]
        assert encryption_service.decrypt(encrypted_pass) == credentials["passphrase"]


class TestEncryptionServiceSingleton:
    """EncryptionService单例测试"""

    def test_get_encryption_service_singleton(self):
        """测试get_encryption_service返回单例"""
        service1 = get_encryption_service()
        service2 = get_encryption_service()

        assert service1 is service2

    def test_get_encryption_service_persistent_key(self):
        """测试单例使用持久化密钥"""
        service = get_encryption_service()

        # 测试加密解密
        plaintext = "singleton-test"
        encrypted = service.encrypt(plaintext)
        decrypted = service.decrypt(encrypted)

        assert decrypted == plaintext


class TestEncryptionServiceErrorHandling:
    """EncryptionService错误处理测试"""

    def test_encrypt_with_invalid_key(self):
        """测试使用无效密钥初始化"""
        with pytest.raises(Exception):
            EncryptionService(encryption_key=b"invalid-key")

    def test_decrypt_with_wrong_key(self):
        """测试使用错误密钥解密"""
        # 使用Fernet生成的有效密钥
        key1 = Fernet.generate_key()
        key2 = Fernet.generate_key()

        service1 = EncryptionService(encryption_key=key1)
        service2 = EncryptionService(encryption_key=key2)

        plaintext = "secret-data"
        encrypted = service1.encrypt(plaintext)

        # 使用不同的密钥解密应该失败
        with pytest.raises(Exception):
            service2.decrypt(encrypted)
