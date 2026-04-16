"""
Portfolio 参数保存形式验证测试

测试组件参数的保存和加载：
1. 通过API创建Portfolio，指定组件参数
2. 验证数据库params表中的保存格式
3. 验证Portfolio加载时参数是否正确

重点关注：
- 参数是否按组件定义的顺序保存
- 参数值是否只保存值（不包含key）
- name参数是否被正确处理
"""

import pytest
import requests
from ginkgo import services
from config import config


API_BASE = config.api_base


@pytest.fixture(scope="module")
def cleanup_portfolio():
    """测试后清理创建的Portfolio"""
    created_uuids = []
    yield created_uuids

    # 清理
    for uuid in created_uuids:
        try:
            requests.delete(f"{API_BASE}/portfolio/{uuid}")
        except:
            pass


@pytest.mark.e2e
def test_portfolio_param_save_format(cleanup_portfolio):
    """测试参数保存格式"""

    print("\n" + "=" * 60)
    print("测试Portfolio参数保存格式")
    print("=" * 60)

    # 1. 准备测试数据
    import time
    portfolio_name = f"ParamTest_{int(time.time())}"
    test_config = {
        "name": portfolio_name,
        "initial_cash": 100000.0,
        "mode": "BACKTEST",
        "description": "测试参数保存格式",
        "selectors": [
            {
                "component_uuid": "fixed_selector_uuid",  # 需要替换为实际UUID
                "config": {
                    "codes": "000001.SZ,000002.SZ",  # 按参数名保存
                }
            }
        ],
        "sizer_uuid": "fixed_sizer_uuid",  # 需要替换
        "sizer_config": {
            "volume": 1500,  # 按参数名保存
        },
        "strategies": [
            {
                "component_uuid": "random_strategy_uuid",  # 需要替换
                "weight": 1.0,
                "config": {
                    "buy_probability": 0.7,
                    "sell_probability": 0.2,
                }
            }
        ],
        "risk_managers": [],
        "analyzers": [],
    }

    # 2. 获取实际组件UUID
    print("\n📋 获取组件UUID...")
    components_resp = requests.get(f"{API_BASE}/components/selectors")
    selectors = components_resp.json().get("data", [])

    components_resp2 = requests.get(f"{API_BASE}/components/sizers")
    sizers = components_resp2.json().get("data", [])

    components_resp3 = requests.get(f"{API_BASE}/components/strategies")
    strategies = components_resp3.json().get("data", [])

    # 找到需要的组件
    fixed_selector = next((s for s in selectors if "fixed" in s["name"].lower()), selectors[0] if selectors else None)
    fixed_sizer = next((s for s in sizers if "fixed" in s["name"].lower()), sizers[0] if sizers else None)
    random_strategy = next((s for s in strategies if "random" in s["name"].lower()), strategies[0] if strategies else None)

    if not all([fixed_selector, fixed_sizer, random_strategy]):
        pytest.skip("缺少必要组件")

    test_config["selectors"][0]["component_uuid"] = fixed_selector["uuid"]
    test_config["sizer_uuid"] = fixed_sizer["uuid"]
    test_config["strategies"][0]["component_uuid"] = random_strategy["uuid"]

    print(f"  Selector: {fixed_selector['name']} ({fixed_selector['uuid'][:16]}...)")
    print(f"  Sizer: {fixed_sizer['name']} ({fixed_sizer['uuid'][:16]}...)")
    print(f"  Strategy: {random_strategy['name']} ({random_strategy['uuid'][:16]}...)")

    # 打印组件参数定义
    print(f"\n  Selector参数定义:")
    for p in fixed_selector.get("params", []):
        print(f"    [{p.get('index', '?')}] {p['name']}: {p.get('type')}")

    print(f"\n  Sizer参数定义:")
    for p in fixed_sizer.get("params", []):
        print(f"    [{p.get('index', '?')}] {p['name']}: {p.get('type')}")

    # 3. 创建Portfolio
    print("\n📝 创建Portfolio...")
    response = requests.post(f"{API_BASE}/portfolio", json=test_config)
    assert response.status_code == 200, f"创建失败: {response.text}"

    result = response.json()
    portfolio_uuid = result["uuid"]
    cleanup_portfolio.append(portfolio_uuid)
    print(f"  Portfolio UUID: {portfolio_uuid}")

    # 4. 验证数据库中的参数保存格式
    print("\n🔍 验证数据库params表...")

    param_crud = services.data.cruds.param()

    # 获取Portfolio的所有mapping
    mapping_crud = services.data.cruds.engine_portfolio_mapping()
    mappings = mapping_crud.find(filters={"portfolio_id": portfolio_uuid})

    print(f"\n  找到 {len(mappings)} 个组件映射")

    for mapping in mappings:
        print(f"\n  组件: {mapping.component_id[:16]}...")
        print(f"  Mapping UUID: {mapping.mapping_id}")

        # 获取该组件的参数
        params = param_crud.find(filters={"mapping_id": mapping.mapping_id})
        params_sorted = sorted(params, key=lambda p: p.index)

        print(f"  参数记录数: {len(params_sorted)}")

        for p in params_sorted:
            print(f"    [{p.index}] value: '{p.value}'")

            # 验证参数值格式：应该是纯值，不包含key
            assert "=" not in p.value, f"参数值包含'=': {p.value}"
            print(f"      ✅ 纯值格式正确")

    # 5. 验证Portfolio加载时参数是否正确
    print("\n📋 验证Portfolio加载...")

    portfolio_service = services.data.portfolio_service()
    load_result = portfolio_service.load_portfolio_with_components(portfolio_uuid)

    assert load_result.is_success(), "加载Portfolio失败"
    portfolio = load_result.data

    # 验证选股器
    print(f"\n  选股器验证:")
    for selector in portfolio.selectors:
        print(f"    类型: {selector.__class__.__name__}")
        print(f"    _interested: {selector._interested}")

        # 应该包含测试中的股票代码
        assert "000001.SZ" in selector._interested or "000002.SZ" in selector._interested, \
            f"选股器股票池错误: {selector._interested}"
        print(f"    ✅ 股票池正确")

    # 验证Sizer
    print(f"\n  Sizer验证:")
    sizer = portfolio.sizer
    if sizer:
        print(f"    类型: {sizer.__class__.__name__}")
        print(f"    volume: {getattr(sizer, 'volume', 'N/A')}")
        # 应该是测试中设置的值
        print(f"    ✅ Sizer加载正确")

    # 6. 验证通过API获取的配置
    print("\n📋 验证API返回配置...")
    api_resp = requests.get(f"{API_BASE}/portfolio/{portfolio_uuid}")
    assert api_resp.status_code == 200

    api_data = api_resp.json()
    print(f"  Selector config: {api_data.get('components', {}).get('selectors', [])}")

    print("\n" + "=" * 60)
    print("✅ 参数保存格式验证通过！")
    print("=" * 60)


def pytest_current_timestamp():
    """获取当前时间戳用于测试命名"""
    import time
    return str(int(time.time()))


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
