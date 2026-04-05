"""
PortfolioConfigCRUD 集成测试

注意：需要运行中的 MongoDB 服务，默认跳过。
PortfolioConfigCRUD 用于组合配置的 CRUD 操作，
依赖外部 MongoDB 基础设施，无法在标准集成测试环境中运行。
"""
import pytest
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))


@pytest.mark.integration
@pytest.mark.skip(reason="需要运行中的 MongoDB 服务，无法在标准测试环境中执行")
class TestPortfolioConfigCRUDIntegration:
    """PortfolioConfigCRUD 集成测试（需要 MongoDB 服务）"""

    def test_placeholder(self):
        """占位测试 - 需要配置 MongoDB 后实现"""
        assert True
