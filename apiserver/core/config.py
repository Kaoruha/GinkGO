"""
API Server 配置管理

只包含 API Server 特定的配置（端口、JWT、CORS等）
数据库和其他配置直接从 Ginkgo GCONF 读取
"""

import sys
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field

# 添加 Ginkgo 源码路径
ginkgo_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(ginkgo_path))


class Settings(BaseSettings):
    """API Server 特定配置"""

    # API 服务配置
    API_HOST: str = Field(default="0.0.0.0", description="API服务监听地址")
    API_PORT: int = Field(default=8000, description="API服务端口")

    # JWT 配置
    SECRET_KEY: str = Field(default="your-secret-key-change-in-production", description="JWT密钥")
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

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# 全局配置实例
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
