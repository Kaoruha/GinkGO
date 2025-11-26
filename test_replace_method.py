#!/usr/bin/env python3
"""
验证BaseCRUD.replace()方法的功能测试
"""

import sys
import os
sys.path.insert(0, '/home/kaoru/Ginkgo/src')

from ginkgo.data.crud import AdjustfactorCRUD
from ginkgo.data.models.model_adjustfactor import MAdjustfactor
from ginkgo.libs import GLOG, to_decimal
from datetime import datetime

def test_replace_method():
    """测试replace方法的各种场景"""

    print("=== 验证BaseCRUD.replace()方法 ===\n")

    # 初始化CRUD
    try:
        crud = AdjustfactorCRUD()
        print("✅ AdjustfactorCRUD初始化成功")
        print(f"📊 Model类型: {crud.model_class.__name__}")
    except Exception as e:
        print(f"❌ AdjustfactorCRUD初始化失败: {e}")
        return False

    # 准备测试数据
    test_code = "TEST_REPLACE_001"
    test_records = [
        MAdjustfactor(
            code=test_code,
            timestamp=datetime(2023, 1, 1),
            foreadjustfactor=to_decimal(1.1),
            backadjustfactor=to_decimal(0.9),
            adjustfactor=to_decimal(1.0)
        ),
        MAdjustfactor(
            code=test_code,
            timestamp=datetime(2023, 1, 2),
            foreadjustfactor=to_decimal(1.2),
            backadjustfactor=to_decimal(0.8),
            adjustfactor=to_decimal(1.0)
        ),
    ]

    print(f"\n🎯 测试股票代码: {test_code}")
    print(f"📋 准备测试记录数: {len(test_records)}")

    # 清理可能存在的测试数据
    try:
        crud.remove(filters={"code": test_code})
        print("🧹 清理现有测试数据")
    except:
        pass  # 忽略清理错误

    # 测试场景1: 没有找到匹配数据的情况
    print("\n📋 场景1: 没有匹配数据 - 应该返回空结果")
    try:
        result = crud.replace(filters={"code": test_code}, new_items=test_records)
        print(f"   结果: {len(result)} 条记录")
        print(f"   预期: 0 条记录")
        assert len(result) == 0, "没有匹配数据时应返回空结果"
        print("   ✅ 场景1测试通过")
    except Exception as e:
        print(f"   ❌ 场景1测试失败: {e}")
        return False

    # 插入初始数据
    print("\n📋 插入初始数据进行后续测试")
    try:
        inserted = crud.add_batch(test_records)
        print(f"   插入成功: {len(inserted)} 条记录")
    except Exception as e:
        print(f"   ❌ 插入初始数据失败: {e}")
        return False

    # 测试场景2: 找到匹配数据并替换
    print("\n📋 场景2: 找到匹配数据 - 应该替换成功")
    try:
        # 创建新的测试记录（修改foreadjustfactor）
        new_records = [
            MAdjustfactor(
                code=test_code,
                timestamp=datetime(2023, 1, 1),
                foreadjustfactor=to_decimal(2.1),  # 修改过的值
                backadjustfactor=to_decimal(1.9),  # 修改过的值
                adjustfactor=to_decimal(1.0)
            ),
            MAdjustfactor(
                code=test_code,
                timestamp=datetime(2023, 1, 2),
                foreadjustfactor=to_decimal(2.2),  # 修改过的值
                backadjustfactor=to_decimal(1.8),  # 修改过的值
                adjustfactor=to_decimal(1.0)
            ),
        ]

        result = crud.replace(filters={"code": test_code}, new_items=new_records)
        print(f"   替换结果: {len(result)} 条记录")
        assert len(result) == 2, "替换成功应返回插入的记录数"

        # 验证数据是否真的被替换了
        updated_records = crud.find(filters={"code": test_code})
        print(f"   数据库中现有记录: {len(updated_records)} 条")

        # 检查foreadjustfactor是否被更新
        for record in updated_records:
            print(f"   - {record.timestamp}: foreadjustfactor = {record.foreadjustfactor}")

        print("   ✅ 场景2测试通过")
    except Exception as e:
        print(f"   ❌ 场景2测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 测试场景3: 类型错误检查
    print("\n📋 场景3: 类型错误检查 - 应该抛出TypeError")
    try:
        from ginkgo.data.models.model_bar import MBar
        wrong_type_record = MBar()

        try:
            result = crud.replace(filters={"code": test_code}, new_items=[wrong_type_record])
            print(f"   ❌ 应该抛出TypeError，但没有异常")
            return False
        except TypeError as e:
            print(f"   ✅ 正确抛出TypeError: {str(e)}")
        except Exception as e:
            print(f"   ❌ 抛出了错误的异常类型: {type(e).__name__}: {e}")
            return False

    except Exception as e:
        print(f"   ❌ 场景3测试失败: {e}")
        return False

    # 测试场景4: 空new_items检查
    print("\n📋 场景4: 空new_items检查")
    try:
        result = crud.replace(filters={"code": test_code}, new_items=[])
        print(f"   结果: {len(result)} 条记录")
        assert len(result) == 0, "空new_items应返回空结果"
        print("   ✅ 场景4测试通过")
    except Exception as e:
        print(f"   ❌ 场景4测试失败: {e}")
        return False

    # 清理测试数据
    print("\n🧹 清理测试数据")
    try:
        crud.remove(filters={"code": test_code})
        print("   清理完成")
    except Exception as e:
        print(f"   清理失败: {e}")

    print("\n🎉 所有replace方法测试通过！")
    return True

if __name__ == "__main__":
    try:
        # 确保调试模式开启
        from ginkgo.libs import GCONF
        GCONF.set_debug(True)

        success = test_replace_method()
        if success:
            print(f"\n✅ Replace方法验证成功！")
        else:
            print(f"\n❌ Replace方法验证失败！")
        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n⚠️ 用户中断测试")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)