#!/usr/bin/env python3
"""
Ginkgo装饰器优化系统验证脚本
快速检验所有优化功能是否正常工作
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def verify_smart_logging():
    """验证智能日志功能"""
    print("🔍 验证智能日志流量控制...")
    
    from ginkgo.libs import GLOG
    
    # 测试错误去重
    for i in range(3):
        GLOG.ERROR("Test error message")
    
    # 获取统计
    stats = GLOG.get_error_stats()
    
    assert stats['total_error_patterns'] >= 1, "错误模式追踪失败"
    assert stats['total_error_count'] >= 3, "错误计数失败"
    
    print("  ✅ 智能日志流量控制正常")
    return True

def verify_datasource_retry():
    """验证数据源重试配置"""
    print("🔍 验证数据源重试策略...")
    
    from ginkgo.libs import GCONF
    from ginkgo.libs.utils import datasource_retry
    
    # 验证配置读取
    tushare_config = GCONF.get_tushare_retry_config()
    assert tushare_config['retry_max_attempts'] == 8, "TuShare重试次数配置错误"
    assert tushare_config['retry_backoff_factor'] == 1.5, "TuShare退避因子配置错误"
    
    baostock_config = GCONF.get_baostock_retry_config()
    assert baostock_config['retry_max_attempts'] == 5, "BaoStock重试次数配置错误"
    assert baostock_config['retry_backoff_factor'] == 2.0, "BaoStock退避因子配置错误"
    
    # 验证装饰器创建
    @datasource_retry('tushare')
    def test_tushare_function():
        return "success"
    
    result = test_tushare_function()
    assert result == "success", "TuShare装饰器应用失败"
    
    print("  ✅ 数据源重试策略正常")
    return True

def verify_performance_monitoring():
    """验证性能监控功能"""
    print("🔍 验证智能性能监控...")
    
    from ginkgo.libs.utils import time_logger
    from ginkgo.libs import GCONF
    import time
    
    # 验证配置读取
    assert hasattr(GCONF, 'DECORATOR_TIME_LOGGER_ENABLED'), "性能监控配置缺失"
    assert hasattr(GCONF, 'DECORATOR_TIME_LOGGER_THRESHOLD'), "阈值配置缺失"
    
    # 验证装饰器功能
    @time_logger(threshold=0.01)
    def test_monitored_function():
        time.sleep(0.005)  # 5ms，低于阈值
        return "monitored"
    
    result = test_monitored_function()
    assert result == "monitored", "性能监控装饰器失败"
    
    print("  ✅ 智能性能监控正常")
    return True

def verify_configuration_management():
    """验证配置管理功能"""
    print("🔍 验证配置管理系统...")
    
    from ginkgo.libs import GCONF
    
    # 验证基础配置属性
    required_attrs = [
        'DECORATOR_TIME_LOGGER_ENABLED',
        'DECORATOR_TIME_LOGGER_THRESHOLD', 
        'DECORATOR_RETRY_ENABLED',
        'DECORATOR_RETRY_MAX_ATTEMPTS',
        'DECORATOR_RETRY_BACKOFF_FACTOR'
    ]
    
    for attr in required_attrs:
        assert hasattr(GCONF, attr), f"配置属性 {attr} 缺失"
    
    # 验证数据源配置方法
    config_methods = [
        'get_tushare_retry_config',
        'get_baostock_retry_config', 
        'get_tdx_retry_config',
        'get_yahoo_retry_config'
    ]
    
    for method in config_methods:
        assert hasattr(GCONF, method), f"配置方法 {method} 缺失"
        config = getattr(GCONF, method)()
        assert 'retry_enabled' in config, f"{method} 返回配置不完整"
        assert 'retry_max_attempts' in config, f"{method} 返回配置不完整"
        assert 'retry_backoff_factor' in config, f"{method} 返回配置不完整"
    
    print("  ✅ 配置管理系统正常")
    return True

def verify_backward_compatibility():
    """验证向后兼容性"""
    print("🔍 验证向后兼容性...")
    
    from ginkgo.libs.utils import time_logger, retry
    
    # 测试原有装饰器语法仍然有效
    @time_logger
    def old_style_time_logger():
        return "old_time"
    
    @retry
    def old_style_retry():
        return "old_retry"
    
    @retry(max_try=2)
    def old_style_retry_with_params():
        return "old_retry_params"
    
    # 执行测试
    result1 = old_style_time_logger()
    result2 = old_style_retry()
    result3 = old_style_retry_with_params()
    
    assert result1 == "old_time", "旧式time_logger兼容性失败"
    assert result2 == "old_retry", "旧式retry兼容性失败"
    assert result3 == "old_retry_params", "旧式retry参数兼容性失败"
    
    print("  ✅ 向后兼容性正常")
    return True

def main():
    """主验证流程"""
    print("🚀 Ginkgo装饰器优化系统验证")
    print("=" * 50)
    
    verifications = [
        verify_smart_logging,
        verify_datasource_retry,
        verify_performance_monitoring,
        verify_configuration_management,
        verify_backward_compatibility
    ]
    
    results = []
    for verify_func in verifications:
        try:
            result = verify_func()
            results.append(result)
        except Exception as e:
            print(f"  ❌ 验证失败: {e}")
            results.append(False)
    
    # 汇总结果
    print("\n📊 验证结果汇总:")
    print("=" * 30)
    
    success_count = sum(results)
    total_count = len(results)
    
    if success_count == total_count:
        print(f"🎉 所有验证通过! ({success_count}/{total_count})")
        print("\n✅ Ginkgo装饰器优化系统已完全就绪！")
        print("💡 建议: 可以开始在生产环境中使用优化功能")
        return True
    else:
        print(f"⚠️ 部分验证失败 ({success_count}/{total_count})")
        print("🔧 建议: 检查配置文件和依赖项是否正确安装")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)