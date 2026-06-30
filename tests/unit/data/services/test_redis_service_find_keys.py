"""
#2592: RedisService.find_keys 契约测试。

根因：cache_cli 直调 redis_service.crud_repo.keys(...)，但 crud_repo 不是公共属性
（BaseService 只暴露私有 _crud_repo），生产环境 AttributeError 被 try/except 吞。
本测试覆盖新增的 find_keys service 方法（包装 _crud_repo.keys，返 ServiceResult）。

不依赖真实 Redis：注入 mock redis_crud。
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

project_root = Path(__file__).parent.parent.parent.parent
_src = str(project_root / "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

from ginkgo.data.services.redis_service import RedisService
from ginkgo.data.services.base_service import ServiceResult


class TestFindKeys:
    """RedisService.find_keys 契约"""

    def test_find_keys_wraps_crud_keys_and_returns_serviceresult(self):
        """find_keys 调 _crud_repo.keys(pattern)，返 ServiceResult 含 keys 列表"""
        mock_crud = MagicMock()
        mock_crud.keys.return_value = ["ginkgo:func_cache:a", "ginkgo:func_cache:b"]
        svc = RedisService(redis_crud=mock_crud)

        result = svc.find_keys("ginkgo:func_cache:*")

        mock_crud.keys.assert_called_once_with("ginkgo:func_cache:*")
        assert isinstance(result, ServiceResult)
        assert result.is_success()
        assert result.data["keys"] == ["ginkgo:func_cache:a", "ginkgo:func_cache:b"]

    def test_find_keys_default_pattern_is_star(self):
        """无参数时默认 pattern=*（对齐 RedisCRUD.keys 签名）"""
        mock_crud = MagicMock()
        mock_crud.keys.return_value = []
        svc = RedisService(redis_crud=mock_crud)

        svc.find_keys()

        mock_crud.keys.assert_called_once_with("*")

    def test_find_keys_empty_result_still_success(self):
        """keys 返空列表时仍 success（空缓存非错误）"""
        mock_crud = MagicMock()
        mock_crud.keys.return_value = []
        svc = RedisService(redis_crud=mock_crud)

        result = svc.find_keys("ginkgo:func_cache:*")

        assert result.is_success()
        assert result.data["keys"] == []

    def test_find_keys_crud_error_returns_service_error(self):
        """_crud_repo.keys 抛异常时返 ServiceResult.error，不向上传播"""
        mock_crud = MagicMock()
        mock_crud.keys.side_effect = RuntimeError("redis down")
        svc = RedisService(redis_crud=mock_crud)

        result = svc.find_keys("ginkgo:func_cache:*")

        assert not result.is_success()
        assert "redis down" in (result.error or "")
