#!/usr/bin/env python
"""
Simple test to verify analyzer binding during engine assembly.
"""
import sys
import os

# Setup paths
sys.path.insert(0, '/home/kaoru/Ginkgo/src')
sys.path.insert(0, '/home/kaoru/Ginkgo/test/backtest')

os.environ['GINKGO_TEST_MODE'] = '1'

def test_analyzer_binding():
    """Test that analyzers are properly bound during assembly."""
    from test_backtest_workflow_integration import BacktestWorkflowIntegrationTest
    from ginkgo.trading.core.containers import container as trading_container

    test = BacktestWorkflowIntegrationTest()
    test.setUpClass()
    test.setUp()

    # Run tests in order to set up the environment
    print("Running test_01_create_engine...")
    test.test_01_create_engine()
    print("Running test_02_create_portfolio...")
    test.test_02_create_portfolio()
    print("Running test_03_bind_engine_portfolio...")
    test.test_03_bind_engine_portfolio()
    print("Running test_04_unbind_rebind_engine_portfolio...")
    test.test_04_unbind_rebind_engine_portfolio()
    print("Running test_05_get_available_components...")
    test.test_05_get_available_components()
    print("Running test_06_bind_components...")
    test.test_06_bind_components()

    # Now assemble the engine (without running the full backtest)
    print("Assembling engine...")
    assembly_service = trading_container.services.engine_assembly_service()
    assemble_result = assembly_service.assemble_backtest_engine(
        engine_id=BacktestWorkflowIntegrationTest.test_engine_uuid
    )

    if not assemble_result.success:
        print(f"❌ FAIL: Engine assembly failed: {assemble_result.error}")
        return False

    engine = assemble_result.data
    BacktestWorkflowIntegrationTest.test_engine_instance = engine

    # Check the portfolio for analyzer bindings
    if hasattr(engine, '_portfolios'):
        # _portfolios can be a dict or list
        if isinstance(engine._portfolios, dict):
            portfolios = list(engine._portfolios.values())
        else:
            portfolios = engine._portfolios
        if portfolios:
            portfolio = portfolios[0]
            print(f"\n=== ANALYZER BINDING RESULTS ===")
            print(f"Portfolio analyzers: {list(portfolio.analyzers.keys())}")
            print(f"Number of analyzers: {len(portfolio.analyzers)}")

            # Check hooks
            from ginkgo.enums import RECORDSTAGE_TYPES
            newday_activate_count = len(portfolio._analyzer_activate_hook.get(RECORDSTAGE_TYPES.NEWDAY, []))
            newday_record_count = len(portfolio._analyzer_record_hook.get(RECORDSTAGE_TYPES.NEWDAY, []))
            print(f"NEWDAY activate hooks: {newday_activate_count}")
            print(f"NEWDAY record hooks: {newday_record_count}")

            if newday_activate_count > 0 and newday_record_count > 0:
                print("✅ SUCCESS: Analyzers are properly bound!")
                return True
            else:
                print("❌ FAIL: No analyzer hooks found!")
                return False

    print("❌ FAIL: No portfolio instance found!")
    return False

if __name__ == "__main__":
    try:
        success = test_analyzer_binding()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

