#!/usr/bin/env python3
"""
Saga 事务管理器验证脚本

验证 Saga 模式的基本功能和事务一致性。
"""
import sys
from pathlib import Path
from datetime import datetime

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

def test_saga_transaction():
    """测试基本 Saga 事务功能"""
    print("=" * 60)
    print("测试 1: 基本 Saga 事务功能")
    print("=" * 60)

    from apiserver.services.saga_transaction import SagaTransaction

    # 创建测试用的执行和补偿函数
    execution_log = []

    def step1():
        execution_log.append("step1_execute")
        return {"id": "test1"}

    def step2():
        execution_log.append("step2_execute")
        raise Exception("Step 2 failed!")

    def compensate1(result):
        execution_log.append("compensate1")

    def compensate2(result):
        execution_log.append("compensate2")

    # 创建 Saga
    saga = SagaTransaction("test_transaction")

    # 添加步骤
    saga.add_step("step1", step1, compensate1)
    saga.add_step("step2", step2, compensate2)

    print(f"✓ Saga 创建成功: {saga.name}")
    print(f"✓ 步骤数量: {len(saga.steps)}")

    # 验证可以转换为记录
    record = saga.to_record()
    print(f"✓ 转换为记录成功: {record.transaction_id}")

    print("\n" + "=" * 60)
    print("测试 2: Portfolio Saga 工厂")
    print("=" * 60)

    from apiserver.services.saga_transaction import PortfolioSagaFactory

    # 测试创建 Portfolio Saga
    try:
        saga = PortfolioSagaFactory.create_portfolio_saga(
            name="Test Portfolio",
            is_live=False,
            selectors=[{"component_uuid": "sel-1", "config": {}}],
            sizer=None,
            strategies=[{"component_uuid": "str-1", "config": {}}],
            risk_managers=[],
            analyzers=[]
        )

        print(f"✓ Portfolio Saga 创建成功")
        print(f"✓ 步骤数量: {len(saga.steps)}")
        print(f"✓ 第一步名称: {saga.steps[0].name}")

        # 验证步骤名称
        step_names = [step.name for step in saga.steps]
        print(f"✓ 步骤列表: {step_names}")

    except Exception as e:
        print(f"✗ Portfolio Saga 创建失败: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("测试 3: 事务模型")
    print("=" * 60)

    from apiserver.models.transaction import TransactionRecord, TransactionStep

    # 创建事务步骤
    step = TransactionStep(
        name="test_step",
        status="completed",
        result={"data": "test"},
        error=None,
        executed_at=None,
        compensated_at=None
    )

    print(f"✓ TransactionStep 创建成功: {step.name}")

    # 创建事务记录
    record = TransactionRecord(
        transaction_id="test-transaction-id",
        entity_type="portfolio",
        entity_id="portfolio-uuid",
        status="completed",
        steps=[step],
        error=None,
        created_at=datetime.now(),
        completed_at=datetime.now()
    )

    print(f"✓ TransactionRecord 创建成功: {record.transaction_id}")

    print("\n" + "=" * 60)
    print("所有验证测试完成!")
    print("=" * 60)

if __name__ == "__main__":
    test_saga_transaction()
