#!/usr/bin/env python3
"""
验证AdjustfactorService前后复权因子计算功能的测试
"""

import sys
import os
sys.path.insert(0, '/home/kaoru/Ginkgo/src')

from ginkgo.data.services import AdjustfactorService
from ginkgo.libs import GLOG, GCONF
from datetime import datetime

def test_adjustfactor_calculation():
    """测试复权因子计算功能"""

    print("=== 验证AdjustfactorService前后复权因子计算 ===\n")

    # 设置调试模式
    GCONF.set_debug(True)

    try:
        # 直接使用data容器初始化服务
        from ginkgo.data.containers import Container
        container = Container()
        service = container.adjustfactor_service()
        print("✅ AdjustfactorService初始化成功")
    except Exception as e:
        print(f"❌ AdjustfactorService初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 测试股票代码
    test_code = "000001.SZ"

    print(f"\n🎯 测试股票代码: {test_code}")

    # 清理可能存在的测试数据
    try:
        service.crud_repo.remove(filters={"code": test_code})
        print("🧹 清理现有测试数据")
    except:
        pass  # 忽略清理错误

    # 首先同步一些基础数据
    print("\n📥 同步基础复权因子数据...")
    try:
        sync_result = service.sync_for_code(test_code, fast_mode=True)
        print(f"同步结果: {sync_result.success}")
        if sync_result.success:
            print(f"处理记录数: {sync_result.data.get('records_processed', 0)}")
            print(f"同步记录数: {sync_result.data.get('records_added', 0)}")

            # 检查数据库中是否真的有数据
            existing_factors = service.crud_repo.find(filters={"code": test_code})
            print(f"数据库中现有复权因子记录数: {len(existing_factors)}")

            if len(existing_factors) == 0:
                print("⚠️ 同步成功但数据库中没有数据，可能存在问题")
                return False
        else:
            print(f"同步错误: {sync_result.error}")
            return False
    except Exception as e:
        print(f"❌ 同步数据失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 测试前后复权因子计算
    print("\n🔬 计算前后复权因子...")
    try:
        calc_result = service.calculate_precomputed_factors_for_code(test_code)

        print(f"计算结果状态: {calc_result.success}")

        if calc_result.success:
            data = calc_result.data
            print(f"✅ 计算成功!")
            print(f"原始记录数: {data.get('original_records', 0)}")
            print(f"处理记录数: {data.get('processed_records', 0)}")
            print(f"前复权因子范围: {data.get('fore_factor_range', 'N/A')}")
            print(f"后复权因子范围: {data.get('back_factor_range', 'N/A')}")
            print(f"原始因子范围: {data.get('original_factor_range', 'N/A')}")
            print(f"处理时间: {data.get('processing_time_seconds', 0):.3f}秒")

            # 验证计算结果
            original_records = data.get('original_records', 0)
            processed_records = data.get('processed_records', 0)

            if processed_records > 0:
                print("✅ 成功计算出前后复权因子")

                # 获取计算后的数据进行验证
                factors = service.crud_repo.find(filters={"code": test_code})
                print(f"数据库中复权因子记录数: {len(factors)}")

                if len(factors) > 0:
                    # 显示前几条记录的详细信息
                    print("\n📊 计算结果样例:")
                    for i, factor in enumerate(factors[:5]):
                        print(f"  {i+1}. {factor.timestamp}: "
                              f"fore={factor.foreadjustfactor:.6f}, "
                              f"back={factor.backadjustfactor:.6f}, "
                              f"adjust={factor.adjustfactor:.6f}")

                    # 验证因子计算的合理性
                    fore_factors = [f.foreadjustfactor for f in factors if f.foreadjustfactor is not None]
                    back_factors = [f.backadjustfactor for f in factors if f.backadjustfactor is not None]

                    if fore_factors:
                        print(f"\n🔍 前复权因子验证:")
                        print(f"  最小值: {min(fore_factors):.6f}")
                        print(f"  最大值: {max(fore_factors):.6f}")
                        print(f"  是否单调递增: {all(fore_factors[i] <= fore_factors[i+1] for i in range(len(fore_factors)-1))}")

                    if back_factors:
                        print(f"\n🔍 后复权因子验证:")
                        print(f"  最小值: {min(back_factors):.6f}")
                        print(f"  最大值: {max(back_factors):.6f}")
                        print(f"  是否单调递减: {all(back_factors[i] >= back_factors[i+1] for i in range(len(back_factors)-1))}")

            else:
                print("⚠️ 没有处理到任何记录")
                return False
        else:
            print(f"❌ 计算失败: {calc_result.error}")
            if calc_result.data:
                print(f"错误详情: {calc_result.data}")
            return False

    except Exception as e:
        print(f"❌ 计算前后复权因子失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n🎉 前后复权因子计算验证完成！")
    return True

if __name__ == "__main__":
    try:
        success = test_adjustfactor_calculation()
        if success:
            print(f"\n✅ AdjustfactorService前后复权因子计算验证成功！")
        else:
            print(f"\n❌ AdjustfactorService前后复权因子计算验证失败！")
        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n⚠️ 用户中断测试")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)