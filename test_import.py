#!/usr/bin/env python3
"""
测试新的导入结构是否正常工作
验证向后兼容性和新模块化结构
"""

import sys
import traceback

def test_core_imports():
    """测试核心模块导入"""
    print("=" * 50)
    print("测试核心模块导入...")
    try:
        # 测试新的模块化导入
        from ginkgo.libs.core import GinkgoConfig, GinkgoLogger, GinkgoThreadManager
        print("✓ 新的模块化导入成功")
        
        # 测试向后兼容的导入
        from ginkgo.libs import GCONF, GLOG, GTM
        print("✓ 向后兼容导入成功")
        
        # 测试实例是否正常创建
        print(f"  - GCONF类型: {type(GCONF)}")
        print(f"  - GLOG类型: {type(GLOG)}")
        print(f"  - GTM类型: {type(GTM)}")
        
        return True
    except Exception as e:
        print(f"✗ 核心模块导入失败: {e}")
        traceback.print_exc()
        return False

def test_data_imports():
    """测试数据处理模块导入"""
    print("=" * 50)
    print("测试数据处理模块导入...")
    try:
        # 测试新的模块化导入
        from ginkgo.libs.data import datetime_normalize, Number, to_decimal
        print("✓ 数据处理模块化导入成功")
        
        # 测试向后兼容的导入
        from ginkgo.libs import datetime_normalize as dt_norm, Number as Num
        print("✓ 数据处理向后兼容导入成功")
        
        # 测试函数是否可用
        result = dt_norm("20240101")
        print(f"  - datetime_normalize测试: {result}")
        
        return True
    except Exception as e:
        print(f"✗ 数据处理模块导入失败: {e}")
        traceback.print_exc()
        return False

def test_utils_imports():
    """测试工具模块导入"""
    print("=" * 50)
    print("测试工具模块导入...")
    try:
        # 测试新的模块化导入
        from ginkgo.libs.utils import try_wait_counter, pretty_repr, GinkgoColor
        print("✓ 工具模块化导入成功")
        
        # 测试向后兼容的导入
        from ginkgo.libs import try_wait_counter as twc, GinkgoColor as GC
        print("✓ 工具向后兼容导入成功")
        
        # 测试函数是否可用
        result = twc(5)
        print(f"  - try_wait_counter测试: {result}")
        
        color = GC()
        colored_text = color.red("测试文本")
        print(f"  - GinkgoColor测试: {colored_text}")
        
        return True
    except Exception as e:
        print(f"✗ 工具模块导入失败: {e}")
        traceback.print_exc()
        return False

def test_display_module():
    """测试显示模块功能"""
    print("=" * 50)
    print("测试显示模块功能...")
    try:
        from ginkgo.libs.utils.display import pretty_repr, chinese_count, GinkgoColor
        
        # 测试中文字符计数
        count = chinese_count("测试中文字符计数功能")
        print(f"  - 中文字符计数: {count}")
        
        # 测试格式化输出
        test_msg = ["消息1", "Message 2", "测试消息3"]
        formatted = pretty_repr("测试类", test_msg)
        print(f"  - 格式化输出测试:")
        print(formatted)
        
        return True
    except Exception as e:
        print(f"✗ 显示模块测试失败: {e}")
        traceback.print_exc()
        return False

def test_backward_compatibility():
    """测试向后兼容性"""
    print("=" * 50)
    print("测试向后兼容性...")
    try:
        # 测试原有的导入方式是否仍然有效
        from ginkgo.libs import GCONF, GLOG, GTM
        from ginkgo.libs import datetime_normalize, try_wait_counter
        from ginkgo.libs import pretty_repr, chinese_count
        
        # 测试 __all__ 中的主要函数
        expected_funcs = [
            'GinkgoLogger', 'GinkgoConfig', 'GinkgoThreadManager',
            'datetime_normalize', 'Number', 'to_decimal', 
            'try_wait_counter', 'pretty_repr', 'chinese_count'
        ]
        
        import ginkgo.libs as libs
        missing_funcs = []
        for func_name in expected_funcs:
            if not hasattr(libs, func_name):
                missing_funcs.append(func_name)
        
        if missing_funcs:
            print(f"⚠ 缺失的函数: {missing_funcs}")
        else:
            print("✓ 所有期望的函数都可用")
        
        print("✓ 向后兼容性测试通过")
        return True
        
    except Exception as e:
        print(f"✗ 向后兼容性测试失败: {e}")
        traceback.print_exc()
        return False

def test_directory_structure():
    """测试目录结构"""
    print("=" * 50)
    print("测试目录结构...")
    try:
        import os
        base_path = "/container/path/src/ginkgo/libs"
        
        # 检查新目录是否存在
        required_dirs = [
            "core", "data", "utils"
        ]
        
        required_files = [
            "core/__init__.py", "core/config.py", "core/logger.py", "core/threading.py",
            "data/__init__.py", "data/normalize.py", "data/number.py", "data/statistics.py", "data/math.py",
            "utils/__init__.py", "utils/common.py", "utils/display.py", "utils/codes.py",
            "utils/links.py", "utils/process.py"
        ]
        
        missing_items = []
        for dir_name in required_dirs:
            dir_path = os.path.join(base_path, dir_name)
            if not os.path.isdir(dir_path):
                missing_items.append(f"目录: {dir_name}")
        
        for file_name in required_files:
            file_path = os.path.join(base_path, file_name)
            if not os.path.isfile(file_path):
                missing_items.append(f"文件: {file_name}")
        
        if missing_items:
            print(f"⚠ 缺失的项目: {missing_items}")
        else:
            print("✓ 目录结构完整")
            
        # 检查备份是否存在
        backup_path = "/container/path/src/ginkgo/libs.backup"
        if os.path.isdir(backup_path):
            print("✓ 备份目录存在")
        else:
            print("⚠ 备份目录不存在")
            
        return len(missing_items) == 0
        
    except Exception as e:
        print(f"✗ 目录结构测试失败: {e}")
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("开始 libs 目录重构验证测试...")
    print("Python版本:", sys.version)
    
    tests = [
        ("目录结构", test_directory_structure),
        ("核心模块导入", test_core_imports),
        ("数据处理模块", test_data_imports),
        ("工具模块导入", test_utils_imports),
        ("显示模块功能", test_display_module),
        ("向后兼容性", test_backward_compatibility)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n执行测试: {test_name}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"测试 {test_name} 出现异常: {e}")
            results.append((test_name, False))
    
    # 输出测试结果总结
    print("\n" + "=" * 60)
    print("测试结果总结:")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for test_name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{test_name:20s} : {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print("-" * 60)
    print(f"总计: {len(results)} 个测试, {passed} 个通过, {failed} 个失败")
    
    if failed == 0:
        print("\n🎉 所有测试通过！libs 目录重构成功！")
        return 0
    else:
        print(f"\n❌ {failed} 个测试失败，请检查问题")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)