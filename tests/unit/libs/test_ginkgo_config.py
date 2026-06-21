"""
TDD tests for GinkgoConfig fixes (batch: #5510 #5875 #5447 #5507 #5508 #5569).

Tests verify behavior through the public interface of GinkgoConfig.
Each test targets one root cause fix.
"""

import os
import pytest


@pytest.fixture(autouse=True)
def _reset_singleton():
    """Ensure clean singleton state between tests."""
    from ginkgo.libs.core.config import GinkgoConfig

    if hasattr(GinkgoConfig, "_instance"):
        del GinkgoConfig._instance
    yield
    if hasattr(GinkgoConfig, "_instance"):
        del GinkgoConfig._instance


# ---------------------------------------------------------------------------
# Root Cause A: Singleton __init__ resets cache (#5510)
# ---------------------------------------------------------------------------


class TestSingletonCachePersistence:
    """Second GinkgoConfig() call should NOT reset the config cache."""

    def test_second_init_preserves_cache(self):
        """
        #5510: GinkgoConfig.__init__ resets _config_cache on every call
        despite singleton __new__. Two instantiations should share cache.
        """
        from ginkgo.libs.core.config import GinkgoConfig

        cfg1 = GinkgoConfig()
        # Simulate a cached value
        cfg1._config_cache = {"test_key": "test_value"}
        cfg1._config_mtime = 12345

        cfg2 = GinkgoConfig()
        # Second instantiation must NOT clear the cache
        assert cfg2._config_cache == {"test_key": "test_value"}
        assert cfg2._config_mtime == 12345
        # Same instance
        assert cfg1 is cfg2

    def test_second_init_preserves_secure_cache(self):
        """Secure cache should also survive re-instantiation."""
        from ginkgo.libs.core.config import GinkgoConfig

        cfg1 = GinkgoConfig()
        cfg1._secure_cache = {"secret": True}
        cfg1._secure_mtime = 99999

        cfg2 = GinkgoConfig()
        assert cfg2._secure_cache == {"secret": True}
        assert cfg2._secure_mtime == 99999


# ---------------------------------------------------------------------------
# Root Cause B: Config priority inversion (#5875)
# ---------------------------------------------------------------------------


class TestEnvVarPriority:
    """Docker env vars should take priority over secure.yml values."""

    def test_env_vars_not_overwritten_by_secure_yml(self):
        """
        #5875: _ensure_env_vars should NOT overwrite existing env vars.
        If GINKGO_MYSQL_HOST is already set (e.g. by Docker), keep it.
        """
        from ginkgo.libs.core.config import GinkgoConfig

        os.environ["GINKGO_MYSQL_HOST"] = "mysql-test-docker"
        try:
            cfg = GinkgoConfig()
            cfg._has_local_secure = False  # skip file loading
            cfg._ensure_env_vars()
            # The Docker-provided value must be preserved
            assert os.environ["GINKGO_MYSQL_HOST"] == "mysql-test-docker"
        finally:
            os.environ.pop("GINKGO_MYSQL_HOST", None)

    def test_env_vars_set_when_missing(self):
        """If env var is not set, secure.yml default should be used."""
        from unittest.mock import patch
        from ginkgo.libs.core.config import GinkgoConfig

        os.environ.pop("GINKGO_REDIS_HOST", None)
        os.environ.pop("GINKGO_REDIS_PORT", None)
        try:
            cfg = GinkgoConfig()
            # Re-trigger _ensure_env_vars with mocked secure data
            cfg._env_vars_initialized = False
            cfg._has_local_secure = True
            fake_secure = {
                "database": {"redis": {"host": "redis-from-yaml", "port": 6379}}
            }
            with patch.object(cfg, "_read_secure", return_value=fake_secure):
                cfg._ensure_env_vars()
            # Should be set from config file since it was missing
            assert os.environ.get("GINKGO_REDIS_HOST") == "redis-from-yaml"
        finally:
            os.environ.pop("GINKGO_REDIS_HOST", None)
            os.environ.pop("GINKGO_REDIS_PORT", None)


# ---------------------------------------------------------------------------
# Root Cause E: TTL type safety (#5507)
# ---------------------------------------------------------------------------


class TestTTLTypeSafety:
    """TTL properties must return int, not str."""

    def test_ttl_backtest_returns_int_from_env(self):
        """#5507: LOGGING_TTL_BACKTEST should return int even when set via env var."""
        from ginkgo.libs.core.config import GinkgoConfig

        os.environ["GINKGO_LOGGING_TTL_BACKTEST"] = "7200"
        try:
            cfg = GinkgoConfig()
            result = cfg.LOGGING_TTL_BACKTEST
            assert isinstance(result, int)
            assert result == 7200
        finally:
            os.environ.pop("GINKGO_LOGGING_TTL_BACKTEST", None)

    def test_ttl_component_returns_int_from_env(self):
        from ginkgo.libs.core.config import GinkgoConfig

        os.environ["GINKGO_LOGGING_TTL_COMPONENT"] = "3600"
        try:
            cfg = GinkgoConfig()
            result = cfg.LOGGING_TTL_COMPONENT
            assert isinstance(result, int)
            assert result == 3600
        finally:
            os.environ.pop("GINKGO_LOGGING_TTL_COMPONENT", None)

    def test_ttl_performance_returns_int_from_env(self):
        from ginkgo.libs.core.config import GinkgoConfig

        os.environ["GINKGO_LOGGING_TTL_PERFORMANCE"] = "1800"
        try:
            cfg = GinkgoConfig()
            result = cfg.LOGGING_TTL_PERFORMANCE
            assert isinstance(result, int)
            assert result == 1800
        finally:
            os.environ.pop("GINKGO_LOGGING_TTL_PERFORMANCE", None)


# ---------------------------------------------------------------------------
# Root Cause F: Decorator key mismatch (#5508)
# ---------------------------------------------------------------------------


class TestDecoratorKeySymmetry:
    """Setter and getter must use the same env var key."""

    def test_decorator_time_logger_env_roundtrip(self):
        """
        #5508: Setting the env var that the getter reads via _get_config
        should return the expected value.  The getter constructs
        key as GINKGO_{key.upper()}, so "time_logger_enabled" →
        GINKGO_TIME_LOGGER_ENABLED.
        """
        from ginkgo.libs.core.config import GinkgoConfig

        os.environ["GINKGO_TIME_LOGGER_ENABLED"] = "False"
        try:
            cfg = GinkgoConfig()
            # The getter reads GINKGO_TIME_LOGGER_ENABLED (via _get_config)
            result = cfg.DECORATOR_TIME_LOGGER_ENABLED
            assert result is False
        finally:
            os.environ.pop("GINKGO_TIME_LOGGER_ENABLED", None)


# ---------------------------------------------------------------------------
# Root Cause C: Base64 is not encryption (#5569)
# ---------------------------------------------------------------------------


class TestPasswordEncryption:
    """_decode_password should use Fernet encryption, not Base64."""

    def test_fernet_encrypted_password_decodes(self):
        """
        #5569: Password encrypted with Fernet should be decrypted correctly.
        """
        from cryptography.fernet import Fernet
        from ginkgo.libs.core.config import GinkgoConfig

        key = Fernet.generate_key()
        f = Fernet(key)
        encrypted = f.encrypt(b"my_secret_password").decode("utf-8")

        os.environ["GINKGO_SECRET_KEY"] = key.decode("utf-8")
        try:
            cfg = GinkgoConfig()
            result = cfg._decode_password(encrypted)
            assert result == "my_secret_password"
        finally:
            os.environ.pop("GINKGO_SECRET_KEY", None)

    def test_base64_backward_compat(self):
        """
        #5569: Existing Base64-encoded passwords should still decode
        (backward compatibility during migration).
        """
        import base64
        from ginkgo.libs.core.config import GinkgoConfig

        encoded = base64.b64encode(b"legacy_password").decode("utf-8")
        # Ensure no Fernet key so it falls back to Base64
        os.environ.pop("GINKGO_SECRET_KEY", None)
        cfg = GinkgoConfig()
        result = cfg._decode_password(encoded)
        assert result == "legacy_password"

    def test_plain_text_passthrough(self):
        """Non-encoded plain text password should pass through unchanged."""
        from ginkgo.libs.core.config import GinkgoConfig

        os.environ.pop("GINKGO_SECRET_KEY", None)
        cfg = GinkgoConfig()
        result = cfg._decode_password("plain_text_pwd")
        assert result == "plain_text_pwd"


# ---------------------------------------------------------------------------
# Root Cause G: Missing set_quiet setter (#5936)
# ---------------------------------------------------------------------------


class TestQuietSetter:
    """#5936: config reset / `config set quiet` crash because GinkgoConfig has
    no set_quiet (QUIET is a read-only property). The setter must exist, persist
    to config.yml, and sync env so the QUIET getter observes the new value."""

    def test_set_quiet_persists_to_config_and_env(self, tmp_path):
        """set_quiet(True) writes `quiet` to config.yml and syncs GINKGO_QUIET."""
        import yaml
        from ginkgo.libs.core.config import GinkgoConfig

        os.environ["GINKGO_DIR"] = str(tmp_path)
        os.environ.pop("GINKGO_QUIET", None)
        config_file = tmp_path / "config.yml"
        config_file.write_text("debug: false\nquiet: false\n")
        try:
            cfg = GinkgoConfig()
            cfg._has_local_config = True  # skip generate_config_file copy logic

            # Must not raise AttributeError (the #5936 crash)
            cfg.set_quiet(True)

            # Persisted to config.yml
            data = yaml.safe_load(config_file.read_text())
            assert data["quiet"] is True
            # Env synced so the read-only QUIET getter observes it immediately
            assert os.environ["GINKGO_QUIET"] == str(True)
            assert cfg.QUIET is True
        finally:
            os.environ.pop("GINKGO_DIR", None)
            os.environ.pop("GINKGO_QUIET", None)
