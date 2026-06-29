"""#5760(3): bars 缺 code 参数应返回 422 校验错误（防静默空响应）。

范围: 仅子问题(3)。
- (1) bars code 模糊匹配/后缀补全: 触及 A股代码归一边界，划出
- (2) stockinfo 分页格式统一: breaking change，划出
"""
import os

os.environ.setdefault("GINKGO_SKIP_DEBUG_CHECK", "1")

import inspect


def test_bars_code_is_required_query_param(api_modules):
    """#5760(3): bars 端点 code 应为必填 query 参数，缺则 FastAPI 自动 422。

    FastAPI 声明式校验: 函数参数无默认值 = 必填，缺则 422。
    用 inspect 签名验证(default is empty)，避开 app 启动/根 main.py 遮蔽
    (arch_api_test_root_main_shadow)。
    """
    from api.data import get_bars

    sig = inspect.signature(get_bars)
    code_param = sig.parameters["code"]
    assert code_param.default is inspect.Parameter.empty, (
        f"code 必须是必填参数(无默认值)以触发 422，当前 default={code_param.default!r}"
    )
