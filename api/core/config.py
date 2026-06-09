"""
API Server 配置管理

只包含 API Server 特定的配置（端口、JWT、CORS等）
数据库和其他配置直接从 Ginkgo GCONF 读取
"""

import sys
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field, model_validator

# 添加 Ginkgo 源码路径
ginkgo_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(ginkgo_path))

# #5464: 已知的默认 SECRET_KEY，禁止在生产使用
_INSECURE_DEFAULT_KEY = "your-secret-key-change-in-production"


class Settings(BaseSettings):
    """API Server 特定配置"""

    # API 服务配置
    API_HOST: str = Field(default="0.0.0.0", description="API服务监听地址")
    API_PORT: int = Field(default=8000, description="API服务端口")

    # JWT 配置
    # #5464: SECRET_KEY 必须通过环境变量设置，不提供安全默认值
    SECRET_KEY: str = Field(default=_INSECURE_DEFAULT_KEY, description="JWT密钥（必须通过环境变量 SECRET_KEY 设置）")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=1440, description="Token过期时间（分钟）")

    # CORS 配置
    CORS_ORIGINS: List[str] = Field(
        default=[
            "http://localhost:5173",
            "http://localhost:3000",
            "http://192.168.50.12:5173",
            "http://192.168.50.12:3000"
        ],
        description="允许的跨域来源"
    )

    # 调试模式
    DEBUG: bool = Field(default=False, description="调试模式")

    @model_validator(mode="after")
    def _validate_secret_key(self) -> "Settings":
        """#5464: 拒绝不安全的默认 SECRET_KEY"""
        if self.SECRET_KEY == _INSECURE_DEFAULT_KEY:
            raise ValueError(
                "SECRET_KEY must be set via environment variable and cannot use "
                f"the default value '{_INSECURE_DEFAULT_KEY}'. "
                "Generate a secure key with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
            )
        return self

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


# 全局配置实例（需要 SECRET_KEY 环境变量）
settings = Settings()


# 数据库配置直接从 GCONF 读取（不维护副本）
def get_db_config():
    """获取数据库配置（从 GCONF）

    GCONF 会根据 DEBUG 模式自动选择正确的端口：
    - DEBUG=True: 13306 (测试环境)
    - DEBUG=False: 3306 (生产环境)
    """
    from ginkgo.libs import GCONF
    return {
        "host": GCONF.MYSQLHOST,
        "port": GCONF.MYSQLPORT,
        "user": GCONF.MYSQLUSER,
        "password": GCONF.MYSQLPWD,
        "database": GCONF.MYSQLDB,
    }
