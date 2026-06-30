"""
#5645: node-graphs files 端点 file_id 校验测试

验证 _validate_file_id 能拒绝空值（空串 / None / 纯空白），
避免 add_file_to_portfolio 对空 file_id 静默返回成功。

直接导入 api/api/_file_type.py（无模块级副作用）进行测试，与 #5578 同模式。
"""

import sys
from pathlib import Path

import pytest

# _file_type.py 无 FastAPI/core 依赖，安全加入 sys.path
_api_api_dir = str(Path(__file__).parent.parent.parent / "api" / "api")
if _api_api_dir not in sys.path:
    sys.path.insert(0, _api_api_dir)

from _file_type import _validate_file_id  # noqa: E402


class TestFileIdValidation:
    """file_id 非空校验 — #5645"""

    @pytest.mark.unit
    def test_empty_string_rejected(self):
        """#5645: 空字符串 file_id 应 raise ValueError（不应静默成功）"""
        with pytest.raises(ValueError, match="file_id"):
            _validate_file_id("")

    @pytest.mark.unit
    def test_none_rejected(self):
        """#5645: None file_id 应 raise ValueError"""
        with pytest.raises(ValueError, match="file_id"):
            _validate_file_id(None)

    @pytest.mark.unit
    def test_whitespace_only_rejected(self):
        """#5645: 纯空白 file_id 应 raise ValueError（等价于空）"""
        with pytest.raises(ValueError, match="file_id"):
            _validate_file_id("   ")

    @pytest.mark.unit
    def test_valid_id_returned(self):
        """#5645: 合法 file_id 原样返回（向后兼容）"""
        assert _validate_file_id("abc-123") == "abc-123"
