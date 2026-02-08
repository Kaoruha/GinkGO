#!/usr/bin/env python3
"""
Saga 事务管理器集成测试

无需依赖外部服务的简单集成测试。
"""
import sys
from pathlib import Path

# 添加项目路径
current_dir = Path(__file__).parent
project_root = current_dir.parent
sys.path.insert(0, str(current_dir))  # 添加 apiserver 目录
sys.path.insert(0, str(project_root / "src"))  # 添加 ginkgo 源码目录


def test_saga_step_creation():
    """测试 SagaStep 创建"""
    # 直接导入，不使用 apiserver 包前缀
    import services.saga_transaction as st

    step = st.SagaStep(
        name="test_step",
        execute=lambda: "result",
        compensate=lambda r: None
    )

    assert step.name == "test_step"
    assert step.execute is not None
    assert step.compensate is not None
    assert not step.executed
    assert not step.compensated
    print("✓ SagaStep 创建测试通过")


def test_saga_transaction_creation():
    """测试 SagaTransaction 创建"""
    import services.saga_transaction as st

    saga = st.SagaTransaction("test_transaction")

    assert saga.name == "test_transaction"
    assert saga.transaction_id is not None
    assert len(saga.steps) == 0
    assert not saga.failed
    print("✓ SagaTransaction 创建测试通过")


def test_add_step():
    """测试添加步骤"""
    import services.saga_transaction as st

    saga = st.SagaTransaction("test")

    result = saga.add_step(
        "step1",
        lambda: "result",
        lambda r: None
    )

    assert result is saga  # 链式调用
    assert len(saga.steps) == 1
    assert saga.steps[0].name == "step1"
    print("✓ 添加步骤测试通过")


def test_saga_to_record():
    """测试转换为事务记录"""
    import services.saga_transaction as st
    import models.transaction as mt

    saga = st.SagaTransaction("test")
    saga.add_step("step1", lambda: "result", lambda r: None)

    record = saga.to_record()

    assert isinstance(record, mt.TransactionRecord)
    assert record.transaction_id == saga.transaction_id
    assert len(record.steps) == 1
    print("✓ 转换为事务记录测试通过")


def test_transaction_model():
    """测试事务模型"""
    import models.transaction as mt
    from datetime import datetime

    step = mt.TransactionStep(
        name="test_step",
        status="completed",
        result={"data": "test"},
        error=None,
        executed_at=datetime.now(),
        compensated_at=None
    )

    assert step.name == "test_step"
    assert step.status == "completed"

    record = mt.TransactionRecord(
        transaction_id="test-id",
        entity_type="portfolio",
        entity_id="portfolio-uuid",
        status="completed",
        steps=[step],
        error=None,
        created_at=datetime.now(),
        completed_at=datetime.now()
    )

    assert record.transaction_id == "test-id"
    assert record.entity_type == "portfolio"
    assert len(record.steps) == 1
    print("✓ 事务模型测试通过")


def test_portfolio_saga_factory_structure():
    """测试 Portfolio Saga 工厂结构"""
    import services.saga_transaction as st

    saga = st.PortfolioSagaFactory.create_portfolio_saga(
        name="Test Portfolio",
        is_live=False,
        selectors=[{"component_uuid": "sel-1", "config": {}}],
        sizer=None,
        strategies=[{"component_uuid": "str-1", "config": {}}],
        risk_managers=[],
        analyzers=[]
    )

    # 验证步骤数量（create_portfolio + selector + strategy）
    assert len(saga.steps) >= 2
    assert saga.steps[0].name == "create_portfolio"

    # 验证步骤名称包含组件信息
    step_names = [step.name for step in saga.steps]
    assert any("selector" in name for name in step_names)
    assert any("strategy" in name for name in step_names)

    print("✓ Portfolio Saga 工厂结构测试通过")


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("Saga 事务管理器集成测试")
    print("=" * 60)
    print()

    tests = [
        test_saga_step_creation,
        test_saga_transaction_creation,
        test_add_step,
        test_saga_to_record,
        test_transaction_model,
        test_portfolio_saga_factory_structure
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ {test.__name__} 失败: {e}")
            failed += 1
            import traceback
            traceback.print_exc()

    print()
    print("=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
