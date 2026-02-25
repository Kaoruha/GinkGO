"""
组件参数保存详细验证测试

测试场景：
1. 空config - 验证所有参数使用默认值
2. 部分参数 - 验证未指定的参数使用默认值
3. 完整参数 - 验证所有参数正确保存
4. 索引连续性 - 验证索引从0开始连续
5. 组件实例化 - 验证参数对齐正确
"""

import pytest
import requests
from ginkgo import services

API_BASE = "http://192.168.50.12:8000"


@pytest.fixture(scope="module")
def api_client():
    """API客户端"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    yield session
    session.close()


@pytest.fixture(scope="module")
def cleanup_portfolio():
    """测试后清理创建的Portfolio"""
    created_uuids = []
    yield created_uuids
    
    for uuid in created_uuids:
        try:
            requests.delete(f"{API_BASE}/api/v1/portfolio/{uuid}")
        except:
            pass


def get_component_with_params(component_type, name_filter=None):
    """获取有参数定义的组件"""
    resp = requests.get(f"{API_BASE}/api/v1/components/{component_type}")
    components = resp.json().get("data", [])
    
    # 优先找有参数的组件
    with_params = [c for c in components if c.get("params")]
    if with_params:
        if name_filter:
            filtered = [c for c in with_params if name_filter in c["name"].lower()]
            return filtered[0] if filtered else with_params[0]
        return with_params[0]
    
    return components[0] if components else None


@pytest.mark.e2e
def test_empty_config_uses_defaults(api_client, cleanup_portfolio):
    """测试空config时所有参数使用默认值"""
    print("\n" + "=" * 60)
    print("测试1: 空config使用默认值")
    print("=" * 60)
    
    # 获取有参数的选股器
    selector = get_component_with_params("selectors", "fixed")
    assert selector, "需要选股器"
    
    portfolio_name = f"EmptyConfig_{import_time()}"
    config = {
        "name": portfolio_name,
        "initial_cash": 100000.0,
        "mode": "BACKTEST",
        "selectors": [{
            "component_uuid": selector["uuid"],
            "config": {}  # 空config
        }],
        "risk_managers": [],
        "analyzers": [],
    }
    
    print(f"\n创建Portfolio: {portfolio_name}")
    print(f"选股器: {selector['name']}")
    print(f"  参数定义: {len(selector.get('params', []))} 个")
    for p in selector.get("params", []):
        print(f"    - {p['name']}: {p.get('default', 'N/A')}")
    
    resp = api_client.post(f"{API_BASE}/api/v1/portfolio", json=config)
    assert resp.status_code == 200
    
    portfolio_uuid = resp.json()["uuid"]
    cleanup_portfolio.append(portfolio_uuid)
    
    # 验证参数保存
    param_crud = services.data.cruds.param()
    mapping_crud = services.data.cruds.portfolio_file_mapping()
    
    mappings = mapping_crud.find(filters={"portfolio_id": portfolio_uuid})
    assert len(mappings) > 0, "应该有组件映射"
    
    for m in mappings:
        params = param_crud.find(filters={"mapping_id": m.uuid})
        params_sorted = sorted(params, key=lambda p: p.index)
        indices = [p.index for p in params_sorted]
        
        print(f"\n保存的参数:")
        print(f"  数量: {len(params_sorted)}")
        print(f"  索引: {indices}")
        
        # 验证索引从0连续
        expected_indices = list(range(len(selector.get("params", []))))
        assert indices == expected_indices, f"索引应连续从0开始，期望{expected_indices}，实际{indices}"
        
        # 验证值都是默认值
        for i, p in enumerate(params_sorted):
            param_def = selector["params"][i]
            expected_default = str(param_def.get('default', ''))
            assert p.value == expected_default, f"参数[{i}]应该是默认值'{expected_default}'，实际'{p.value}'"
            print(f"  [{i}] {p.value} (默认值) ✅")
    
    print("\n✅ 空config测试通过")


@pytest.mark.e2e
def test_partial_config_uses_defaults(api_client, cleanup_portfolio):
    """测试部分参数时，其他使用默认值"""
    print("\n" + "=" * 60)
    print("测试2: 部分参数使用默认值")
    print("=" * 60)
    
    # 获取有多个参数的组件
    selector = get_component_with_params("selectors", "fixed")
    assert selector and len(selector.get("params", [])) >= 2, "需要至少2个参数的组件"
    
    # 只设置第二个参数
    second_param = selector["params"][1]
    test_value = "000001.SZ,000002.SZ"
    
    portfolio_name = f"PartialConfig_{import_time()}"
    config = {
        "name": portfolio_name,
        "initial_cash": 100000.0,
        "mode": "BACKTEST",
        "selectors": [{
            "component_uuid": selector["uuid"],
            "config": {second_param["name"]: test_value}  # 只设置第二个
        }],
        "risk_managers": [],
        "analyzers": [],
    }
    
    print(f"\n创建Portfolio: {portfolio_name}")
    print(f"  Config只包含: {second_param['name']} = {test_value}")
    print(f"  期望: 第一个参数使用默认值")
    
    resp = api_client.post(f"{API_BASE}/api/v1/portfolio", json=config)
    assert resp.status_code == 200
    
    portfolio_uuid = resp.json()["uuid"]
    cleanup_portfolio.append(portfolio_uuid)
    
    # 验证参数
    param_crud = services.data.cruds.param()
    mapping_crud = services.data.cruds.portfolio_file_mapping()
    
    mappings = mapping_crud.find(filters={"portfolio_id": portfolio_uuid})
    
    for m in mappings:
        params = param_crud.find(filters={"mapping_id": m.uuid})
        params_sorted = sorted(params, key=lambda p: p.index)
        
        # 验证第一个参数是默认值
        p0 = params_sorted[0]
        expected_default = str(selector["params"][0].get('default', ''))
        assert p0.value == expected_default, f"参数[0]应为默认值'{expected_default}'，实际'{p0.value}'"
        print(f"  [0] {p0.value} (默认值) ✅")
        
        # 验证第二个参数是设置的值
        p1 = params_sorted[1]
        assert p1.value == test_value, f"参数[1]应为'{test_value}'，实际'{p1.value}'"
        print(f"  [1] {p1.value} (设置值) ✅")
    
    print("\n✅ 部分参数测试通过")


@pytest.mark.e2e
def test_all_components_save_params(api_client, cleanup_portfolio):
    """测试所有组件类型都正确保存参数"""
    print("\n" + "=" * 60)
    print("测试3: 所有组件类型参数保存")
    print("=" * 60)
    
    # 获取各类型组件
    selector = get_component_with_params("selectors", "fixed")
    
    resp_siz = api_client.get(f"{API_BASE}/api/v1/components/sizers")
    sizers = [s for s in resp_siz.json().get("data", []) if "fixed" in s["name"].lower()]
    
    resp_str = api_client.get(f"{API_BASE}/api/v1/components/strategies")
    strategies = [s for s in resp_str.json().get("data", []) if s.get("params")]
    
    if not all([selector, sizers, strategies]):
        pytest.skip("缺少必要组件")
    
    portfolio_name = f"AllComponents_{import_time()}"
    config = {
        "name": portfolio_name,
        "initial_cash": 100000.0,
        "mode": "BACKTEST",
        "selectors": [{
            "component_uuid": selector["uuid"],
            "config": {"codes": "000001.SZ"}
        }],
        "sizer_uuid": sizers[0]["uuid"],
        "sizer_config": {"volume": 1000},
        "strategies": [{
            "component_uuid": strategies[0]["uuid"],
            "weight": 1.0,
            "config": {"short_window": 5}
        }],
        "risk_managers": [],
        "analyzers": [],
    }
    
    print(f"\n创建Portfolio: {portfolio_name}")
    print(f"  选股器: {selector['name']}")
    print(f"  Sizer: {sizers[0]['name']}")
    print(f"  策略: {strategies[0]['name']}")
    
    resp = api_client.post(f"{API_BASE}/api/v1/portfolio", json=config)
    assert resp.status_code == 200
    
    portfolio_uuid = resp.json()["uuid"]
    cleanup_portfolio.append(portfolio_uuid)
    
    # 验证所有组件参数
    param_crud = services.data.cruds.param()
    mapping_crud = services.data.cruds.portfolio_file_mapping()
    
    mappings = mapping_crud.find(filters={"portfolio_id": portfolio_uuid})
    type_map = {4: "选股器", 5: "Sizer", 6: "策略"}
    
    results = {}
    for m in mappings:
        params = param_crud.find(filters={"mapping_id": m.uuid})
        params_sorted = sorted(params, key=lambda p: p.index)
        indices = [p.index for p in params_sorted]
        
        type_name = type_map.get(m.type, f"Type{m.type}")
        results[type_name] = {
            "count": len(params_sorted),
            "indices": indices,
            "params": params_sorted
        }
        
        # 验证索引连续
        expected = list(range(len(params_sorted)))
        is_continuous = (indices == expected)
        
        print(f"\n{type_name}:")
        print(f"  参数数量: {len(params_sorted)}")
        print(f"  索引: {indices}")
        print(f"  连续性: {'✅' if is_continuous else '❌'}")
        
        for p in params_sorted[:3]:
            print(f"    [{p.index}] {p.value}")
        
        assert is_continuous, f"{type_name}索引不连续"
    
    assert "选股器" in results and results["选股器"]["count"] >= 2
    assert "Sizer" in results and results["Sizer"]["count"] >= 2
    assert "策略" in results and results["策略"]["count"] >= 1
    
    print("\n✅ 所有组件测试通过")


@pytest.mark.e2e
def test_portfolio_load_with_params(api_client, cleanup_portfolio):
    """测试Portfolio加载时参数正确对齐"""
    print("\n" + "=" * 60)
    print("测试4: Portfolio加载参数对齐")
    print("=" * 60)
    
    selector = get_component_with_params("selectors", "fixed")
    assert selector, "需要选股器"
    
    test_codes = "000001.SZ,000002.SZ,000003.SZ"
    
    portfolio_name = f"LoadTest_{import_time()}"
    config = {
        "name": portfolio_name,
        "initial_cash": 100000.0,
        "mode": "BACKTEST",
        "selectors": [{
            "component_uuid": selector["uuid"],
            "config": {"codes": test_codes}
        }],
        "risk_managers": [],
        "analyzers": [],
    }
    
    print(f"\n创建Portfolio: {portfolio_name}")
    print(f"  Config codes: {test_codes}")
    
    resp = api_client.post(f"{API_BASE}/api/v1/portfolio", json=config)
    assert resp.status_code == 200
    
    portfolio_uuid = resp.json()["uuid"]
    cleanup_portfolio.append(portfolio_uuid)
    
    # 加载Portfolio
    portfolio_service = services.data.portfolio_service()
    load_result = portfolio_service.load_portfolio_with_components(portfolio_uuid)
    
    assert load_result.is_success(), "Portfolio加载失败"
    portfolio = load_result.data
    
    print(f"\nPortfolio加载成功:")
    print(f"  选股器类型: {portfolio.selectors[0].__class__.__name__}")
    
    # 验证选股器参数对齐
    selector_obj = portfolio.selectors[0]
    print(f"  _interested: {selector_obj._interested}")
    
    expected_codes = [c.strip() for c in test_codes.split(',')]
    for code in expected_codes:
        assert code in selector_obj._interested, f"股票池应包含{code}"
    
    print(f"  ✅ 参数对齐正确，股票池包含{len(selector_obj._interested)}只股票")
    
    print("\n✅ Portfolio加载测试通过")


def import_time():
    import time
    return str(int(time.time()))


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
