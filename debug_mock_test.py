#!/usr/bin/env python3
"""
调试Mock数据源是否生效的测试脚本
"""
import os
import sys

# 确保能找到test模块
test_dir = os.path.join(os.path.dirname(__file__), 'test')
sys.path.insert(0, test_dir)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_conftest_fixture():
    """测试conftest.py中的fixture是否工作"""
    print("=== 测试conftest.py中的Mock fixture ===")

    # 导入必要的模块
    from test.mock_data.mock_ginkgo_tushare import MockGinkgoTushare
    from ginkgo import service_hub

    # 获取BarService实例
    bar_service = service_hub.data.bar_service()
    print(f'1. 初始数据源类型: {type(bar_service.data_source)}')

    # 手动替换数据源（模拟conftest.py应该做的事情）
    mock_source = MockGinkgoTushare()
    bar_service.data_source = mock_source
    print(f'2. 手动替换后数据源类型: {type(bar_service.data_source)}')

    # 测试Mock数据源功能
    if hasattr(bar_service.data_source, 'mock_data_dir'):
        print("3. ✅ Mock数据源属性存在")

        # 测试获取数据
        try:
            result = bar_service.data_source.fetch_cn_stock_daybar()
            print(f"4. ✅ Mock数据源返回数据: {len(result)} 条记录")
        except Exception as e:
            print(f"4. ❌ Mock数据源调用失败: {e}")
    else:
        print("3. ❌ Mock数据源属性不存在")

def test_with_pytest():
    """使用pytest运行测试来验证fixture"""
    print("\n=== 使用pytest测试fixture ===")

    # 创建测试内容
    test_content = '''
import pytest
from ginkgo import service_hub

def test_autouse_fixture():
    """测试autouse fixture是否生效"""
    bar_service = service_hub.data.bar_service()
    print(f"数据源类型: {type(bar_service.data_source)}")

    # 检查是否是Mock数据源
    is_mock = hasattr(bar_service.data_source, 'mock_data_dir')
    print(f"是否为Mock数据源: {is_mock}")

    if is_mock:
        print("✅ Mock数据源已生效")
    else:
        print("❌ Mock数据源未生效")
        pytest.fail("Mock数据源未生效")
'''

    # 写入测试文件
    test_file = os.path.join(test_dir, 'debug_mock_fixture.py')
    with open(test_file, 'w') as f:
        f.write(test_content)

    print(f"创建测试文件: {test_file}")

    # 运行pytest
    import subprocess
    result = subprocess.run([
        'python', '-m', 'pytest',
        test_file,
        '-v', '-s',
        '--tb=short'
    ], capture_output=True, text=True)

    print("pytest输出:")
    print(result.stdout)
    if result.stderr:
        print("pytest错误:")
        print(result.stderr)

    print(f"pytest返回码: {result.returncode}")

    # 清理测试文件
    if os.path.exists(test_file):
        os.remove(test_file)
        print("已清理临时测试文件")

if __name__ == '__main__':
    test_conftest_fixture()
    test_with_pytest()