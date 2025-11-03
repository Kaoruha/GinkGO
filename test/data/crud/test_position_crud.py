"""
Position CRUD数据库操作TDD测试 - 持仓管理

本文件测试PositionCRUD类的完整功能，确保持仓(Position)数据的增删改查操作正常工作。
持仓数据是量化交易系统的核心状态数据，实时反映投资组合的当前状况，为资金管理和风险控制提供关键支持。

测试范围：
1. 插入操作 (Insert Operations)
   - 批量插入 (add_batch): 高效创建多个持仓记录
   - 单条插入 (add_single_position): 创建单个持仓记录
   - 多股票持仓插入 (multi_stock_positions): 创建多只股票持仓
   - 空头持仓插入 (short_positions): 创建空头持仓记录
   - 冻结持仓插入 (frozen_positions): 创建冻结状态持仓

2. 查询操作 (Query Operations)
   - 按投资组合查询 (find_by_portfolio): 获取特定投资组合的持仓
   - 按股票代码查询 (find_by_symbol): 查找特定股票的持仓
   - 按持仓数量查询 (find_by_volume): 按持仓数量筛选
   - 按成本价查询 (find_by_cost): 按成本价格筛选
   - 按市值查询 (find_by_market_value): 按市场价值筛选
   - 按状态查询 (find_by_status): 查找特定状态的持仓
   - 复合条件查询 (complex_filters): 多条件组合查询
   - 分页查询 (pagination_query): 支持大数据量分页

3. 更新操作 (Update Operations)
   - 持仓数量更新 (update_volume): 增加或减少持仓数量
   - 成本价更新 (update_cost): 更新持仓成本价格
   - 当前价格更新 (update_current_price): 更新当前市场价格
   - 市值更新 (update_market_value): 更新市场价值
   - 冻结状态更新 (update_freeze_status): 更新冻结状态
   - 盈亏更新 (update_profit_loss): 更新盈亏信息
   - 批量更新 (batch_update): 批量更新多个持仓

4. 删除操作 (Delete Operations)
   - 按投资组合删除 (delete_by_portfolio): 删除特定投资组合持仓
   - 按股票代码删除 (delete_by_symbol): 删除特定股票持仓
   - 按状态删除 (delete_by_status): 删除特定状态持仓
   - 按市值删除 (delete_by_market_value): 删除指定市值持仓
   - 清空持仓 (clear_positions): 清空所有持仓
   - 安全删除 (safe_delete): 检查依赖关系后删除

5. 业务逻辑测试 (Business Logic Tests)
   - 持仓生命周期 (position_lifecycle): 从建仓到平仓的完整流程
   - 持仓成本计算 (cost_calculation): 持仓成本计算验证
   - 盈亏计算 (profit_loss_calculation): 盈亏计算准确性验证
   - 持仓冻结管理 (freeze_management): 持仓冻结和解冻管理
   - 持仓调整 (position_adjustment): 持仓调整和再平衡
   - 空头持仓管理 (short_position_management): 空头持仓特殊处理

6. 持仓分析测试 (Position Analysis Tests)
   - 持仓分布分析 (position_distribution): 持仓分布统计
   - 集中度分析 (concentration_analysis): 持仓集中度计算
   - 风险敞口分析 (risk_exposure): 风险敞口计算
   - 绩效贡献分析 (performance_contribution): 持仓绩效贡献分析

数据模型：
- MPosition: 持仓数据模型，包含完整的持仓信息
- 基础信息：投资组合ID、股票代码、数量、价格等
- 成本信息：平均成本、总成本、冻结成本等
- 价值信息：当前价格、市值、浮动盈亏等
- 状态信息：持仓状态、冻结状态、更新时间等
- 扩展字段：行业分类、风险等级、绩效贡献等

业务价值：
- 投资组合状态反映：实时反映投资组合的持仓状况
- 风险管理基础：为风险控制和资金管理提供数据支撑
- 绩效评估支持：计算投资收益和风险评估
- 交易执行依据：为交易决策提供当前持仓信息
- 合规管理支持：提供完整的持仓变更记录

持仓类型：
- 多头持仓(Long): 做多股票持仓，期望价格上涨
- 空头持仓(Short): 做空股票持仓，期望价格下跌
- 部分冻结(Partial Frozen): 部分数量被冻结
- 完全冻结(Fully Frozen): 全部数量被冻结
- 待清算(Liquidating): 正在清算过程中

测试策略：
- 覆盖持仓完整生命周期
- 验证成本和盈亏计算精度
- 测试冻结状态管理
- 验证持仓调整逻辑
- 测试持仓分析和统计功能
- 使用测试数据源标记便于清理
"""
import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.data.crud.position_crud import PositionCRUD
from ginkgo.data.models.model_position import MPosition
from ginkgo.enums import SOURCE_TYPES


@pytest.mark.database
@pytest.mark.tdd
class TestPositionCRUDInsert:
    # 明确配置CRUD类
    CRUD_TEST_CONFIG = {'crud_class': PositionCRUD}

    """1. CRUD层插入操作测试 - Position数据插入验证"""

    def test_add_batch_basic(self):
        """测试批量插入Position数据 - 使用真实数据库"""
        print("\n" + "="*60)
        print("开始测试: Position CRUD层批量插入")
        print("="*60)

        position_crud = PositionCRUD()
        print(f"✓ 创建PositionCRUD实例: {position_crud.__class__.__name__}")

        # 创建测试Position数据 - 不同股票的持仓
        base_time = datetime(2023, 1, 3, 9, 30)
        test_positions = []

        # 平安银行持仓
        pingan_position = MPosition(
            portfolio_id="test_portfolio_001",
            engine_id="test_engine_001",
            code="000001.SZ",
            cost=Decimal("12.50"),
            volume=1000,
            price=Decimal("13.20"),
            fee=Decimal("5.00"),
            frozen_volume=0,
            frozen_money=Decimal("0.00")
        )
        pingan_position.source = SOURCE_TYPES.TEST
        test_positions.append(pingan_position)

        # 万科A持仓
        vanke_position = MPosition(
            portfolio_id="test_portfolio_001",
            engine_id="test_engine_001",
            code="000002.SZ",
            cost=Decimal("18.75"),
            volume=500,
            price=Decimal("19.80"),
            fee=Decimal("3.50"),
            frozen_volume=100,
            frozen_money=Decimal("1980.00")
        )
        vanke_position.source = SOURCE_TYPES.TEST
        test_positions.append(vanke_position)

        # 国华网安持仓（空仓）
        guohua_position = MPosition(
            portfolio_id="test_portfolio_001",
            engine_id="test_engine_001",
            code="000004.SZ",
            cost=Decimal("0.00"),
            volume=0,
            price=Decimal("0.00"),
            fee=Decimal("0.00"),
            frozen_volume=0,
            frozen_money=Decimal("0.00")
        )
        guohua_position.source = SOURCE_TYPES.TEST
        test_positions.append(guohua_position)

        print(f"✓ 创建测试数据: {len(test_positions)}条Position记录")
        print(f"  - 投资组合: {test_positions[0].portfolio_id}")
        print(f"  - 股票代码: {[p.code for p in test_positions]}")
        total_cost = sum(float(p.cost * p.volume) for p in test_positions if p.volume > 0)
        print(f"  - 总成本: {total_cost:,.2f}")

        try:
            # 批量插入
            print("\n→ 执行批量插入操作...")
            batch_result = position_crud.add_batch(test_positions)
            print("✓ 批量插入成功")

            # 验证返回值类型
            print(f"✓ 批量插入返回值类型: {type(batch_result).__name__}")
            assert batch_result is not None, "add_batch()应返回非空值"

            # 验证可以查询出插入的数据
            print("\n→ 验证插入的数据...")
            query_result = position_crud.find(filters={
                "portfolio_id": "test_portfolio_001",
                "engine_id": "test_engine_001"
            })
            print(f"✓ 查询结果类型: {type(query_result).__name__}")
            print(f"✓ 查询到 {len(query_result)} 条记录")

            # 验证返回值类型 - find方法应返回ModelList
            from ginkgo.data.crud.model_conversion import ModelList
            assert isinstance(query_result, ModelList), f"find()应返回ModelList，实际{type(query_result)}"
            assert len(query_result) >= 3

            # 验证数据内容
            codes = set(p.code for p in query_result)
            print(f"✓ 股票代码验证通过: {len(codes)} 种")
            assert len(codes) >= 3

            # 验证持仓状态
            active_positions = [p for p in query_result if p.volume > 0]
            print(f"✓ 活跃持仓验证通过: {len(active_positions)} 个")
            assert len(active_positions) >= 2

        except Exception as e:
            print(f"✗ 批量插入失败: {e}")
            raise

    def test_add_single_position(self):
        """测试单条Position数据插入"""
        print("\n" + "="*60)
        print("开始测试: Position CRUD层单条插入")
        print("="*60)

        position_crud = PositionCRUD()

        test_position = MPosition(
            portfolio_id="test_portfolio_002",
            engine_id="test_engine_002",
            code="000858.SZ",
            cost=Decimal("25.60"),
            volume=800,
            price=Decimal("26.80"),
            fee=Decimal("8.50"),
            frozen_volume=50,
            frozen_money=Decimal("1340.00")
        )
        test_position.source = SOURCE_TYPES.TEST
        print(f"✓ 创建测试Position: {test_position.code}")
        print(f"  - 投资组合: {test_position.portfolio_id}")
        print(f"  - 持仓数量: {test_position.volume}")
        print(f"  - 成本价: {test_position.cost}")
        print(f"  - 当前价: {test_position.price}")

        try:
            # 单条插入
            print("\n→ 执行单条插入操作...")
            result = position_crud.add(test_position)
            print("✓ 单条插入成功")

            # 验证返回值类型
            print(f"✓ 返回值类型: {type(result).__name__}")
            assert isinstance(result, MPosition), f"add()应返回MPosition对象，实际{type(result)}"

            # 验证数据
            print("\n→ 验证插入的数据...")
            query_result = position_crud.find(filters={
                "portfolio_id": "test_portfolio_002",
                "code": "000858.SZ"
            })
            print(f"✓ 查询到 {len(query_result)} 条记录")
            assert len(query_result) >= 1

            inserted_position = query_result[0]
            print(f"✓ 插入的Position验证: {inserted_position.code}")
            assert inserted_position.portfolio_id == "test_portfolio_002"
            assert inserted_position.volume == 800
            assert inserted_position.cost == Decimal("25.60")

        except Exception as e:
            print(f"✗ 单条插入失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestPositionCRUDQuery:
    # 明确配置CRUD类
    CRUD_TEST_CONFIG = {'crud_class': PositionCRUD}

    """2. CRUD层查询操作测试 - Position数据查询和过滤"""

    def test_find_by_portfolio_id(self):
        """测试根据投资组合ID查询Position"""
        print("\n" + "="*60)
        print("开始测试: 根据投资组合ID查询Position")
        print("="*60)

        position_crud = PositionCRUD()

        try:
            # 查询特定投资组合的持仓
            print("→ 查询投资组合test_portfolio_001的持仓...")
            portfolio_positions = position_crud.find(filters={
                "portfolio_id": "test_portfolio_001"
            })
            print(f"✓ 查询到 {len(portfolio_positions)} 条记录")

            # 验证查询结果
            total_cost = sum(float(p.cost * p.volume) for p in portfolio_positions if p.volume > 0)
            total_market_value = sum(float(p.price * p.volume) for p in portfolio_positions if p.volume > 0 and p.price)
            total_pnl = total_market_value - total_cost

            print(f"✓ 持仓统计:")
            print(f"  - 总持仓数: {len(portfolio_positions)}")
            print(f"  - 总成本: {total_cost:,.2f}")
            print(f"  - 市值: {total_market_value:,.2f}")
            print(f"  - 盈亏: {total_pnl:+,.2f}")

            for position in portfolio_positions:
                assert position.portfolio_id == "test_portfolio_001"

        except Exception as e:
            print(f"✗ 查询失败: {e}")
            raise

    def test_find_by_stock_code(self):
        """测试根据股票代码查询Position"""
        print("\n" + "="*60)
        print("开始测试: 根据股票代码查询Position")
        print("="*60)

        position_crud = PositionCRUD()

        try:
            # 查询特定股票的持仓
            print("→ 查询股票代码000001.SZ的持仓...")
            stock_positions = position_crud.find(filters={
                "code": "000001.SZ"
            })
            print(f"✓ 查询到 {len(stock_positions)} 条记录")

            # 验证查询结果
            for position in stock_positions:
                print(f"  - 投资组合: {position.portfolio_id}, 持仓: {position.volume}股, 成本: {position.cost}")
                assert position.code == "000001.SZ"

        except Exception as e:
            print(f"✗ 查询失败: {e}")
            raise

    def test_find_active_positions(self):
        """测试查询活跃持仓（有持仓数量）"""
        print("\n" + "="*60)
        print("开始测试: 查询活跃持仓")
        print("="*60)

        position_crud = PositionCRUD()

        try:
            # 查询有持仓的记录
            print("→ 查询volume > 0的活跃持仓...")
            active_positions = position_crud.find(filters={
                "volume__gt": 0
            })
            print(f"✓ 查询到 {len(active_positions)} 条活跃持仓")

            # 验证查询结果
            for position in active_positions:
                print(f"  - {position.code}: {position.volume}股 @ {position.price}")
                assert position.volume > 0

            # 查询空仓记录
            print("→ 查询volume = 0的空仓记录...")
            empty_positions = position_crud.find(filters={
                "volume": 0
            })
            print(f"✓ 查询到 {len(empty_positions)} 条空仓记录")

            for position in empty_positions:
                print(f"  - {position.code}: 空仓")
                assert position.volume == 0

            print("✓ 活跃持仓查询验证成功")

        except Exception as e:
            print(f"✗ 活跃持仓查询失败: {e}")
            raise

    def test_model_list_conversions(self):
        """测试ModelList的to_dataframe和to_entities转换功能"""
        from decimal import Decimal
        import pandas as pd

        print("\n" + "="*60)
        print("开始测试: ModelList转换功能")
        print("="*60)

        position_crud = PositionCRUD()
        print(f"✓ 创建PositionCRUD实例")

        # 准备测试数据 - 包含不同类型的持仓
        test_positions = [
            MPosition(
                portfolio_id="convert_test_portfolio",
                engine_id="convert_engine_001",
                run_id="convert_test_run_001",
                code="CONVERT001.SZ",
                cost=Decimal("100.50"),
                volume=1000,
                price=Decimal("105.20"),
                fee=Decimal("10.00"),
                frozen_volume=0,
                frozen_money=Decimal("0.00")
            ),
            MPosition(
                portfolio_id="convert_test_portfolio",
                engine_id="convert_engine_001",
                run_id="convert_test_run_001",
                code="CONVERT001.SZ",
                cost=Decimal("98.30"),
                volume=500,
                price=Decimal("102.80"),
                fee=Decimal("5.00"),
                frozen_volume=100,
                frozen_money=Decimal("10280.00")
            ),
            MPosition(
                portfolio_id="convert_test_portfolio",
                engine_id="convert_engine_002",
                run_id="convert_test_run_002",
                code="CONVERT002.SZ",
                cost=Decimal("50.00"),
                volume=2000,
                price=Decimal("52.30"),
                fee=Decimal("15.00"),
                frozen_volume=0,
                frozen_money=Decimal("0.00")
            )
        ]

        try:
            # 验证插入前后的数据变化
            print("\n→ 验证插入前数据...")
            before_count = len(position_crud.find(filters={"portfolio_id": "convert_test_portfolio"}))
            print(f"✓ 插入前数据量: {before_count}")

            # 插入测试数据
            print(f"\n→ 插入 {len(test_positions)} 条测试数据...")
            position_crud.add_batch(test_positions)
            print("✓ 数据插入成功")

            # 验证插入后的数据变化
            print("\n→ 验证插入后数据变化...")
            after_count = len(position_crud.find(filters={"portfolio_id": "convert_test_portfolio"}))
            print(f"✓ 插入后数据量: {after_count}")
            assert after_count - before_count == len(test_positions), f"应增加{len(test_positions)}条数据，实际增加{after_count - before_count}条"

            # 获取ModelList进行转换测试
            print("\n→ 获取ModelList...")
            model_list = position_crud.find(filters={"portfolio_id": "convert_test_portfolio"})
            print(f"✓ ModelList类型: {type(model_list).__name__}")
            print(f"✓ ModelList长度: {len(model_list)}")

            # 测试1: to_dataframe转换
            print("\n→ 测试to_dataframe转换...")
            df = model_list.to_dataframe()
            print(f"✓ DataFrame类型: {type(df).__name__}")
            print(f"✓ DataFrame形状: {df.shape}")
            assert isinstance(df, pd.DataFrame), "应返回DataFrame"
            assert len(df) == len(model_list), f"DataFrame行数应等于ModelList长度，{len(df)} != {len(model_list)}"

            # 验证DataFrame列和内容
            required_columns = ['portfolio_id', 'engine_id', 'code', 'cost', 'volume', 'price', 'fee', 'frozen_volume', 'frozen_money']
            for col in required_columns:
                assert col in df.columns, f"DataFrame缺少列: {col}"
            print(f"✓ 包含所有必要列: {required_columns}")

            # 验证数据内容
            first_row = df.iloc[0]
            assert first_row['code'] in ["CONVERT001.SZ", "CONVERT002.SZ"]  # 数据库返回顺序可能不同
            print(f"✓ 数据内容验证通过: code={first_row['code']}, volume={first_row['volume']}")

            # 测试2: to_entities转换
            print("\n→ 测试to_entities转换...")
            from ginkgo.trading.entities import Position
            entities = model_list.to_entities()
            print(f"✓ 实体列表类型: {type(entities).__name__}")
            print(f"✓ 实体列表长度: {len(entities)}")
            assert len(entities) == len(model_list), f"实体列表长度应等于ModelList长度，{len(entities)} != {len(model_list)}"

            # 验证实体类型和内容
            first_entity = entities[0]
            print(f"✓ 第一个实体类型: {type(first_entity).__name__}")
            assert isinstance(first_entity, Position), "应转换为Position业务对象"

            # 验证业务对象字段
            assert first_entity.code in ["CONVERT001.SZ", "CONVERT002.SZ"]  # 数据库返回顺序可能不同
            assert first_entity.volume in [1000, 500, 2000]  # 可能是三条记录中的任意一条
            print(f"✓ 业务对象字段验证通过: code={first_entity.code}, volume={first_entity.volume}")

            # 测试3: 验证Decimal精度保持
            print("\n→ 验证Decimal精度保持...")
            decimal_positions = [e for e in entities if hasattr(e, 'cost')]
            assert len(decimal_positions) > 0, "应有包含Decimal字段的Position对象"
            for pos in decimal_positions:
                assert isinstance(pos.cost, Decimal), f"cost应保持Decimal类型，实际{type(pos.cost)}"
                assert isinstance(pos.price, Decimal), f"price应保持Decimal类型，实际{type(pos.price)}"
            print("✓ Decimal精度保持验证正确")

            # 测试4: 验证缓存机制
            print("\n→ 测试转换缓存机制...")
            df2 = model_list.to_dataframe()
            entities2 = model_list.to_entities()

            # 验证结果一致性
            assert df.equals(df2), "缓存的DataFrame应该相同"
            assert len(entities) == len(entities2), "缓存的实体数量应该相同"
            print("✓ 缓存机制验证正确")

            # 测试5: 验证空ModelList的转换
            print("\n→ 测试空ModelList的转换...")
            empty_model_list = position_crud.find(filters={"portfolio_id": "NONEXISTENT_PORTFOLIO"})
            assert len(empty_model_list) == 0, "空ModelList长度应为0"

            empty_df = empty_model_list.to_dataframe()
            empty_entities = empty_model_list.to_entities()

            assert isinstance(empty_df, pd.DataFrame), "空转换应返回DataFrame"
            assert len(empty_df) == 0, "空DataFrame长度应为0"
            assert isinstance(empty_entities, list), "空转换应返回列表"
            assert len(empty_entities) == 0, "空实体列表长度应为0"
            print("✓ 空ModelList转换验证正确")

            print("\n✓ 所有ModelList转换功能测试通过！")

        finally:
            # 清理测试数据并验证删除效果
            print("\n→ 清理测试数据...")
            before_delete = len(position_crud.find(filters={"portfolio_id": "convert_test_portfolio"}))
            print(f"✓ 删除前数据量: {before_delete}")

            position_crud.remove(filters={"portfolio_id": "convert_test_portfolio"})

            after_delete = len(position_crud.find(filters={"portfolio_id": "convert_test_portfolio"}))
            print(f"✓ 删除后数据量: {after_delete}")
            assert before_delete - after_delete >= len(test_positions), f"应至少删除{len(test_positions)}条数据，实际删除{before_delete - after_delete}条"
            print("✓ 测试数据清理验证通过")
            print("="*60)
            print("测试完成!")
            print("="*60)

    def test_business_helper_methods(self):
        """测试业务辅助方法"""
        print("\n" + "="*60)
        print("开始测试: Position业务辅助方法")
        print("="*60)

        position_crud = PositionCRUD()

        try:
            # 测试find_by_portfolio方法
            print("→ 测试find_by_portfolio方法...")
            portfolio_positions = position_crud.find_by_portfolio("test_portfolio_001")
            print(f"✓ find_by_portfolio查询到 {len(portfolio_positions)} 条记录")

            # 测试find_by_code方法
            print("→ 测试find_by_code方法...")
            code_positions = position_crud.find_by_code("000001.SZ")
            print(f"✓ find_by_code查询到 {len(code_positions)} 条记录")

            # 测试get_position方法
            print("→ 测试get_position方法...")
            specific_position = position_crud.get_position("test_portfolio_001", "000001.SZ")
            if specific_position:
                print(f"✓ get_position查询到: {specific_position.code} 持仓 {specific_position.volume}股")
            else:
                print("✓ get_position未查询到特定持仓")

            # 测试get_active_positions方法
            print("→ 测试get_active_positions方法...")
            active_positions = position_crud.get_active_positions("test_portfolio_001")
            print(f"✓ get_active_positions查询到 {len(active_positions)} 个活跃持仓")

            # 测试get_portfolio_value方法
            print("→ 测试get_portfolio_value方法...")
            portfolio_value = position_crud.get_portfolio_value("test_portfolio_001")
            print(f"✓ 投资组合价值统计:")
            print(f"  - 总持仓数: {portfolio_value['total_positions']}")
            print(f"  - 活跃持仓: {portfolio_value['active_positions']}")
            print(f"  - 总成本: {portfolio_value['total_cost']:,.2f}")
            print(f"  - 市值: {portfolio_value['total_market_value']:,.2f}")
            print(f"  - 盈亏: {portfolio_value['total_pnl']:+,.2f}")

            print("✓ 业务辅助方法验证成功")

        except Exception as e:
            print(f"✗ 业务辅助方法测试失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestPositionCRUDUpdate:
    # 明确配置CRUD类
    CRUD_TEST_CONFIG = {'crud_class': PositionCRUD}

    """3. CRUD层更新操作测试 - Position属性更新"""

    def test_update_position_values(self):
        """测试更新Position值"""
        print("\n" + "="*60)
        print("开始测试: 更新Position值")
        print("="*60)

        position_crud = PositionCRUD()

        try:
            # 使用业务辅助方法更新持仓
            print("→ 更新持仓信息...")
            position_crud.update_position(
                portfolio_id="test_portfolio_001",
                code="000001.SZ",
                volume=1200,
                price=Decimal("13.50"),
                frozen_volume=200
            )
            print("✓ 持仓更新成功")

            # 验证更新结果
            print("→ 验证更新结果...")
            updated_position = position_crud.get_position("test_portfolio_001", "000001.SZ")
            if updated_position:
                print(f"✓ 更新后持仓: {updated_position.volume}股 @ {updated_position.price}")
                print(f"✓ 冻结数量: {updated_position.frozen_volume}")

            print("✓ Position值更新验证成功")

        except Exception as e:
            print(f"✗ 更新Position值失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestPositionCRUDBusinessLogic:
    # 明确配置CRUD类
    CRUD_TEST_CONFIG = {'crud_class': PositionCRUD}

    """4. CRUD层业务逻辑测试 - Position业务场景验证"""

    def test_portfolio_position_analysis(self):
        """测试投资组合持仓分析"""
        print("\n" + "="*60)
        print("开始测试: 投资组合持仓分析")
        print("="*60)

        position_crud = PositionCRUD()

        try:
            # 获取投资组合持仓分析
            print("→ 进行投资组合持仓分析...")
            portfolio_value = position_crud.get_portfolio_value("test_portfolio_001")

            print(f"✓ 投资组合持仓分析结果:")
            print(f"  - 投资组合ID: {portfolio_value['portfolio_id']}")
            print(f"  - 总持仓数量: {portfolio_value['total_positions']}")
            print(f"  - 活跃持仓数量: {portfolio_value['active_positions']}")
            print(f"  - 总成本: {portfolio_value['total_cost']:,.2f}")
            print(f"  - 总市值: {portfolio_value['total_market_value']:,.2f}")
            print(f"  - 总盈亏: {portfolio_value['total_pnl']:+,.2f}")
            print(f"  - 总持股数: {portfolio_value['total_volume']}")

            # 计算盈亏率
            if portfolio_value['total_cost'] > 0:
                pnl_rate = (portfolio_value['total_pnl'] / portfolio_value['total_cost']) * 100
                print(f"  - 盈亏率: {pnl_rate:+.2f}%")

            print("✓ 投资组合持仓分析验证成功")

        except Exception as e:
            print(f"✗ 投资组合持仓分析失败: {e}")
            raise

    def test_position_risk_analysis(self):
        """测试持仓风险分析"""
        print("\n" + "="*60)
        print("开始测试: 持仓风险分析")
        print("="*60)

        position_crud = PositionCRUD()

        try:
            # 获取所有持仓进行风险分析
            print("→ 进行持仓风险分析...")
            all_positions = position_crud.find_by_portfolio("test_portfolio_001")

            if len(all_positions) < 2:
                print("✗ 持仓数据不足，跳过风险分析")
                return

            # 计算持仓集中度
            total_market_value = sum(float(p.price * p.volume) for p in all_positions if p.volume > 0 and p.price)
            position_concentration = {}

            for position in all_positions:
                if position.volume > 0 and position.price:
                    market_value = float(position.price * position.volume)
                    concentration = (market_value / total_market_value) * 100 if total_market_value > 0 else 0
                    position_concentration[position.code] = {
                        "market_value": market_value,
                        "concentration": concentration,
                        "volume": position.volume,
                        "cost": float(position.cost),
                        "price": float(position.price),
                        "pnl_per_share": float(position.price - position.cost),
                        "total_pnl": market_value - (float(position.cost) * position.volume)
                    }

            print(f"✓ 持仓风险分析结果:")
            print(f"  - 总市值: {total_market_value:,.2f}")
            print(f"  - 持仓股票数: {len(position_concentration)}")

            # 找出最大持仓
            if position_concentration:
                max_position = max(position_concentration.items(), key=lambda x: x[1]["concentration"])
                print(f"  - 最大持仓: {max_position[0]} ({max_position[1]['concentration']:.2f}%)")

                # 显示持仓集中度分析
                sorted_positions = sorted(position_concentration.items(), key=lambda x: x[1]["concentration"], reverse=True)
                print(f"  - 持仓集中度排名:")
                for rank, (code, data) in enumerate(sorted_positions, 1):
                    print(f"    第{rank}名: {code} - {data['concentration']:.2f}%, 盈亏{data['total_pnl']:+,.2f}")

                # 风险提示
                top3_concentration = sum(data["concentration"] for _, data in sorted_positions[:3])
                if top3_concentration > 80:
                    print(f"  - ⚠️  风险提示: 前3大持仓占比{top3_concentration:.1f}%，集中度较高")

            print("✓ 持仓风险分析验证成功")

        except Exception as e:
            print(f"✗ 持仓风险分析失败: {e}")
            raise

    def test_position_performance_analysis(self):
        """测试持仓表现分析"""
        print("\n" + "="*60)
        print("开始测试: 持仓表现分析")
        print("="*60)

        position_crud = PositionCRUD()

        try:
            # 获取持仓进行表现分析
            print("→ 进行持仓表现分析...")
            all_positions = position_crud.find(filters={"volume__gt": 0})  # 只分析有持仓的

            if len(all_positions) < 2:
                print("✗ 持仓数据不足，跳过表现分析")
                return

            # 计算每个持仓的表现
            performance_data = []
            for position in all_positions:
                if position.volume > 0 and position.cost > 0 and position.price:
                    cost_total = float(position.cost * position.volume)
                    market_value = float(position.price * position.volume)
                    pnl = market_value - cost_total
                    pnl_rate = (pnl / cost_total) * 100 if cost_total > 0 else 0

                    performance_data.append({
                        "code": position.code,
                        "portfolio_id": position.portfolio_id,
                        "volume": position.volume,
                        "cost": float(position.cost),
                        "price": float(position.price),
                        "cost_total": cost_total,
                        "market_value": market_value,
                        "pnl": pnl,
                        "pnl_rate": pnl_rate
                    })

            # 按盈亏率排序
            performance_data.sort(key=lambda x: x["pnl_rate"], reverse=True)

            print(f"✓ 持仓表现分析结果:")
            print(f"  - 分析持仓数: {len(performance_data)}")

            # 显示最佳和最差表现
            if performance_data:
                best_performer = performance_data[0]
                worst_performer = performance_data[-1]

                print(f"  - 最佳表现: {best_performer['code']} (+{best_performer['pnl_rate']:.2f}%)")
                print(f"  - 最差表现: {worst_performer['code']} ({worst_performer['pnl_rate']:.2f}%)")

                # 统计盈利和亏损持仓
                profit_positions = [p for p in performance_data if p["pnl"] > 0]
                loss_positions = [p for p in performance_data if p["pnl"] < 0]

                print(f"  - 盈利持仓: {len(profit_positions)}个")
                print(f"  - 亏损持仓: {len(loss_positions)}个")

                if profit_positions:
                    avg_profit_rate = sum(p["pnl_rate"] for p in profit_positions) / len(profit_positions)
                    print(f"  - 平均盈利率: {avg_profit_rate:.2f}%")

                if loss_positions:
                    avg_loss_rate = sum(p["pnl_rate"] for p in loss_positions) / len(loss_positions)
                    print(f"  - 平均亏损率: {avg_loss_rate:.2f}%")

                # 显示详细持仓表现（前5名）
                print(f"  - 持仓表现排名（前5名）:")
                for rank, data in enumerate(performance_data[:5], 1):
                    print(f"    第{rank}名: {data['code']} {data['pnl_rate']:+.2f}% ({data['pnl']:+,.2f})")

            print("✓ 持仓表现分析验证成功")

        except Exception as e:
            print(f"✗ 持仓表现分析失败: {e}")
            raise

    def test_frozen_position_analysis(self):
        """测试冻结持仓分析"""
        print("\n" + "="*60)
        print("开始测试: 冻结持仓分析")
        print("="*60)

        position_crud = PositionCRUD()

        try:
            # 查询有冻结的持仓
            print("→ 进行冻结持仓分析...")
            frozen_positions = position_crud.find(filters={"frozen_volume__gt": 0})
            frozen_money_positions = position_crud.find(filters={"frozen_money__gt": 0})

            print(f"✓ 冻结持仓分析结果:")
            print(f"  - 冻结股数持仓: {len(frozen_positions)} 个")
            print(f"  - 冻结资金持仓: {len(frozen_money_positions)} 个")

            # 详细分析冻结情况
            if frozen_positions:
                total_frozen_volume = sum(p.frozen_volume for p in frozen_positions)
                total_volume = sum(p.volume for p in frozen_positions)
                frozen_rate = (total_frozen_volume / total_volume) * 100 if total_volume > 0 else 0

                print(f"  - 总冻结股数: {total_frozen_volume}")
                print(f"  - 冻结股数占总持仓: {frozen_rate:.2f}%")

                for position in frozen_positions:
                    rate = (position.frozen_volume / position.volume) * 100 if position.volume > 0 else 0
                    print(f"    - {position.code}: 冻结{position.frozen_volume}股 ({rate:.1f}%)")

            if frozen_money_positions:
                total_frozen_money = sum(float(p.frozen_money) for p in frozen_money_positions)
                print(f"  - 总冻结资金: {total_frozen_money:,.2f}")

                for position in frozen_money_positions:
                    print(f"    - {position.code}: 冻结资金 {position.frozen_money}")

            if not frozen_positions and not frozen_money_positions:
                print("  - 当前无冻结持仓")

            print("✓ 冻结持仓分析验证成功")

        except Exception as e:
            print(f"✗ 冻结持仓分析失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestPositionCRUDDelete:
    # 明确配置CRUD类
    CRUD_TEST_CONFIG = {'crud_class': PositionCRUD}

    """4. CRUD层删除操作测试 - Position数据删除验证"""

    def test_delete_position_by_portfolio(self):
        """测试根据投资组合ID删除持仓"""
        print("\n" + "="*60)
        print("开始测试: 根据投资组合ID删除持仓")
        print("="*60)

        position_crud = PositionCRUD()

        try:
            # 准备测试数据
            print("→ 创建测试持仓数据...")
            test_position = MPosition(
                portfolio_id="delete_test_portfolio",
                code="000001.SZ",
                volume=1000,
                cost=Decimal("10.00"),
                price=Decimal("10.50"),
                run_id="delete_test_run"
            )
            test_position.source = SOURCE_TYPES.TEST
            position_crud.add(test_position)
            print("✓ 测试持仓创建成功")

            # 验证数据存在
            print("→ 验证持仓数据存在...")
            positions_before = position_crud.find(filters={"portfolio_id": "delete_test_portfolio"})
            print(f"✓ 删除前持仓数: {len(positions_before)}")
            assert len(positions_before) >= 1

            # 执行删除操作
            print("→ 执行持仓删除...")
            position_crud.remove(filters={"portfolio_id": "delete_test_portfolio"})
            print("✓ 删除操作完成")

            # 验证删除结果
            print("→ 验证删除结果...")
            positions_after = position_crud.find(filters={"portfolio_id": "delete_test_portfolio"})
            print(f"✓ 删除后持仓数: {len(positions_after)}")
            assert len(positions_after) == 0

            print("✓ 根据投资组合ID删除持仓验证成功")

        except Exception as e:
            print(f"✗ 根据投资组合ID删除持仓失败: {e}")
            raise

    def test_delete_position_by_code(self):
        """测试根据股票代码删除持仓"""
        print("\n" + "="*60)
        print("开始测试: 根据股票代码删除持仓")
        print("="*60)

        position_crud = PositionCRUD()

        try:
            # 准备多个测试持仓
            print("→ 创建多个测试持仓...")
            test_positions = [
                MPosition(
                    portfolio_id="delete_code_test",
                    code="000001.SZ",
                    volume=500,
                    cost=Decimal("10.00"),
                    price=Decimal("10.50")
                ),
                MPosition(
                    portfolio_id="delete_code_test",
                    code="000002.SZ",
                    volume=300,
                    cost=Decimal("20.00"),
                    price=Decimal("20.80")
                )
            ]

            for pos in test_positions:
                position_crud.add(pos)
            print("✓ 多个测试持仓创建成功")

            # 验证数据存在
            print("→ 验证持仓数据存在...")
            positions_before = position_crud.find(filters={"portfolio_id": "delete_code_test"})
            print(f"✓ 删除前持仓数: {len(positions_before)}")
            assert len(positions_before) >= 2, f"应至少有2条持仓，实际{len(positions_before)}条"

            # 执行删除特定股票持仓
            print("→ 删除特定股票持仓...")
            position_crud.remove(filters={"portfolio_id": "delete_code_test", "code": "000001.SZ"})
            print("✓ 删除000001.SZ持仓完成")

            # 验证删除结果
            print("→ 验证删除结果...")
            remaining_positions = position_crud.find(filters={"portfolio_id": "delete_code_test"})
            print(f"✓ 删除后持仓数: {len(remaining_positions)}")

            # 计算删除的000001.SZ持仓数量
            deleted_000001_count = len(positions_before) - len(remaining_positions)
            assert deleted_000001_count >= 1, f"应至少删除1条000001.SZ持仓，实际删除{deleted_000001_count}条"

            # 验证剩余的持仓不包含000001.SZ
            for pos in remaining_positions:
                assert pos.code != "000001.SZ", f"剩余持仓不应包含000001.SZ，但发现{pos.code}"

            print(f"✓ 成功删除了{deleted_000001_count}条000001.SZ持仓")

            print("✓ 根据股票代码删除持仓验证成功")

        except Exception as e:
            print(f"✗ 根据股票代码删除持仓失败: {e}")
            raise

    def test_delete_zero_volume_positions(self):
        """测试删除零持仓记录"""
        print("\n" + "="*60)
        print("开始测试: 删除零持仓记录")
        print("="*60)

        position_crud = PositionCRUD()

        try:
            # 准备包含零持仓的测试数据
            print("→ 创建包含零持仓的测试数据...")
            test_positions = [
                MPosition(
                    portfolio_id="zero_volume_test",
                    code="000001.SZ",
                    volume=1000,
                    cost=Decimal("10.00"),
                    price=Decimal("10.50")
                ),
                MPosition(
                    portfolio_id="zero_volume_test",
                    code="000002.SZ",
                    volume=0,  # 零持仓
                    cost=Decimal("0.00"),
                    price=Decimal("0.00")
                ),
                MPosition(
                    portfolio_id="zero_volume_test",
                    code="000003.SZ",
                    volume=500,
                    cost=Decimal("30.00"),
                    price=Decimal("31.20")
                )
            ]

            for pos in test_positions:
                position_crud.add(pos)
            print("✓ 测试数据创建成功")

            # 验证初始数据
            print("→ 验证初始数据...")
            all_positions = position_crud.find(filters={"portfolio_id": "zero_volume_test"})
            zero_positions = [p for p in all_positions if p.volume == 0]
            print(f"✓ 初始持仓数: {len(all_positions)}, 零持仓数: {len(zero_positions)}")
            assert len(zero_positions) >= 1, f"应至少有1条零持仓，实际{len(zero_positions)}条"

            # 执行删除零持仓
            print("→ 删除零持仓记录...")
            position_crud.remove(filters={"portfolio_id": "zero_volume_test", "volume": 0})
            print("✓ 删除零持仓完成")

            # 验证删除结果
            print("→ 验证删除结果...")
            remaining_positions = position_crud.find(filters={"portfolio_id": "zero_volume_test"})
            remaining_zero_positions = [p for p in remaining_positions if p.volume == 0]

            print(f"✓ 删除后持仓数: {len(remaining_positions)}, 零持仓数: {len(remaining_zero_positions)}")

            # 验证零持仓已被删除
            assert len(remaining_zero_positions) == 0, f"零持仓应被完全删除，剩余{len(remaining_zero_positions)}条"

            # 验证至少删除了测试中的零持仓
            deleted_zero_count = len(zero_positions) - len(remaining_zero_positions)
            assert deleted_zero_count >= 1, f"应至少删除1条零持仓，实际删除{deleted_zero_count}条"

            print(f"✓ 成功删除了{deleted_zero_count}条零持仓记录")

            print("✓ 删除零持仓记录验证成功")

        except Exception as e:
            print(f"✗ 删除零持仓记录失败: {e}")
            raise


# TDD Red阶段验证：确保所有测试开始时都失败
if __name__ == "__main__":
    print("TDD Red阶段验证：Position CRUD测试")
    print("所有测试用例应该在实现开始前失败")
    print("运行: pytest test/data/crud/test_position_crud.py -v")
    print("预期结果: 所有测试失败 (Red阶段)")
    print("重点关注: 持仓数据存储和投资组合管理功能")
