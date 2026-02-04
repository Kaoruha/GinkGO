"""
API Server配置管理
从.env文件或环境变量读取配置
"""

import os
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """API Server配置"""

    # API服务配置
    API_HOST: str = Field(default="0.0.0.0", description="API服务监听地址")
    API_PORT: int = Field(default=8000, description="API服务端口")

    # JWT配置
    SECRET_KEY: str = Field(default="your-secret-key-change-in-production", description="JWT密钥")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=1440, description="Token过期时间（分钟）")

    # CORS配置
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:5173", "http://localhost:3000"],
        description="允许的跨域来源"
    )

    # 调试模式
    DEBUG: bool = Field(default=False, description="调试模式")

    # Ginkgo配置路径
    GINKGO_CONFIG_PATH: str = Field(default="/home/kaoru/Ginkgo/.conf/.env", description="Ginkgo配置文件路径")

    # 数据库配置（从Ginkgo配置读取）
    GINKGO_MYSQLHOST: str = Field(default="localhost", description="MySQL主机")
    GINKGO_MYSQLPORT: int = Field(default=3306, description="MySQL端口")
    GINKGO_MYSQLUSER: str = Field(default="ginkgoadm", description="MySQL用户")
    GINKGO_MYSQLPASSWD: str = Field(default="hellomysql", description="MySQL密码")
    GINKGO_MYSQLDATABASE: str = Field(default="ginkgo", description="MySQL数据库")

    # MongoDB配置
    GINKGO_MONGOHOST: str = Field(default="localhost", description="MongoDB主机")
    GINKGO_MONGOPORT: int = Field(default=27017, description="MongoDB端口")
    GINKGO_MONGODATABASE: str = Field(default="ginkgo", description="MongoDB数据库")

    # ClickHouse配置
    GINKGO_CLICKHOUSEHOST: str = Field(default="localhost", description="ClickHouse主机")
    GINKGO_CLICKHOUSEPORT: int = Field(default=9000, description="ClickHouse端口")

    # Redis配置
    GINKGO_REDISHOST: str = Field(default="localhost", description="Redis主机")
    GINKGO_REDISPORT: int = Field(default=6379, description="Redis端口")

    # Kafka配置
    GINKGO_KAFKA_HOST: str = Field(default="localhost", description="Kafka主机")
    GINKGO_KAFKA_PORT: int = Field(default=9092, description="Kafka端口")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# 全局配置实例
settings = Settings()


def load_ginkgo_config():
    """加载Ginkgo核心配置"""
    try:
        from dotenv import load_dotenv

        if os.path.exists(settings.GINKGO_CONFIG_PATH):
            load_dotenv(settings.GINKGO_CONFIG_PATH, override=True)
            return True
        return False
    except Exception:
        return False
