"""
#5393 SegmentStabilityRequest n_segments 接受 int（归一化为 [int]）

字段名 n_segments 暗示单个整数，但类型声明为 list[int] → 传 int 报 422
"Input should be a valid list"。服务层 segment_stability(n_segments_list)
循环 for n in n_segments_list 证实设计意图是「多分段数列表」，故不能简单改 int。
修复：Union[int, list[int]] + field_validator(mode="before") 归一化 int→[int]，
默认 [2,4,8] 保留，list 输入不变。

纯模型测试（避开 api/main.py 遮蔽陷阱，走 api_modules fixture 延迟导入）。
"""
import pytest


def _make_request(api_modules):
    from api.validation import SegmentStabilityRequest
    return SegmentStabilityRequest


class TestSegmentStabilityNAcceptsInt:
    """#5393: n_segments 接受 int 并归一化为单元素 list"""

    def test_int_normalized_to_singleton_list(self, api_modules):
        """传 n_segments=4（int）应归一化为 [4]，不报 422"""
        SegmentStabilityRequest = _make_request(api_modules)
        req = SegmentStabilityRequest(task_id="t", portfolio_id="p", n_segments=4)
        assert req.n_segments == [4]

    def test_list_input_preserved(self, api_modules):
        """list 输入原样保留（不破坏多分段分析能力）"""
        SegmentStabilityRequest = _make_request(api_modules)
        req = SegmentStabilityRequest(task_id="t", portfolio_id="p", n_segments=[2, 4, 8])
        assert req.n_segments == [2, 4, 8]

    def test_default_remains_multi_segment(self, api_modules):
        """缺省仍为 [2,4,8]（多分段默认）"""
        SegmentStabilityRequest = _make_request(api_modules)
        req = SegmentStabilityRequest(task_id="t", portfolio_id="p")
        assert req.n_segments == [2, 4, 8]

    def test_invalid_string_still_rejected(self, api_modules):
        """非法类型（字符串）仍被拒，证明归一化是选择性的（非放开一切）"""
        from pydantic import ValidationError
        SegmentStabilityRequest = _make_request(api_modules)
        with pytest.raises(ValidationError):
            SegmentStabilityRequest(task_id="t", portfolio_id="p", n_segments="four")
