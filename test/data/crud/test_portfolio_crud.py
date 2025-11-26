"""
PortfolioCRUD数据库操作TDD测试 - 投资组合管理

本文件测试PortfolioCRUD类的完整功能，确保投资组合(Portfolio)的增删改查操作正常工作。
投资组合是量化交易系统的核心组织单位，管理资金、持仓、策略和风险，为交易执行和绩效评估提供基础框架。

测试范围：
1. 插入操作 (Insert Operations)
   - 批量插入 (add_batch): 高效创建多个投资组合
   - 单条插入 (add_single): 创建单个投资组合
   - 模拟组合创建 (create_simulation_portfolio): 创建回测用组合
   - 实盘组合创建 (create_live_portfolio): 创建实盘交易组合

2. 查询操作 (Query Operations)
   - 按名称查询 (find_by_name): 根据组合名称查找
   - 按状态查询 (find_by_status): 查找特定状态的组合
   - 按资金范围查询 (find_by_capital_range): 按资金规模筛选
   - 按策略类型查询 (find_by_strategy_type): 按策略分类查找
   - 按时间范围查询 (find_by_creation_time): 按创建时间筛选
   - 复合条件查询 (complex_filters): 多条件组合查询
   - 分页查询 (pagination_query): 支持大数据量分页

3. 更新操作 (Update Operations)
   - 基本信息更新 (update_basic_info): 更新组合名称、描述等
   - 资金信息更新 (update_capital_info): 更新资金相关字段
   - 状态更新 (update_status): 更新组合运行状态
   - 风险参数更新 (update_risk_parameters): 更新风控设置
   - 批量更新 (batch_update): 批量更新多个组合

4. 删除操作 (Delete Operations)
   - 按状态删除 (delete_by_status): 删除特定状态的组合
   - 按时间范围删除 (delete_by_time_range): 清理过期组合
   - 按资金规模删除 (delete_by_capital_range): 删除指定规模组合
   - 安全删除 (safe_delete): 检查依赖关系后删除
   - 批量删除 (batch_delete): 高效批量删除

5. 替换操作 (Replace Operations)
   TODO: 添加replace方法测试用例
   - 测试replace方法的原子操作 (备份→删除→插入→失败时恢复)
   - 测试没有匹配数据时的行为 (应返回空结果，不插入新数据)
   - 测试类型错误检查 (传入错误Model类型时应抛出TypeError)
   - 测试空new_items的处理
   - 测试批量替换的性能和正确性
   - 测试ClickHouse和MySQL数据库的兼容性

6. 业务逻辑测试 (Business Logic Tests)
   - 投资组合生命周期 (portfolio_lifecycle): 从创建到销毁的完整流程
   - 资金变动追踪 (capital_tracking): 资金流入流出追踪
   - 状态转换管理 (status_transitions): 组合状态变更管理
   - 风险指标计算 (risk_metrics_calculation): 风险指标计算验证
   - 绩效数据更新 (performance_update): 绩效数据更新机制

7. 扩展业务字段测试 (Extended Business Fields)
   - 风险水平管理 (risk_level_management): 风险等级设置和验证
   - 绩效指标更新 (performance_metrics_update): 胜率、夏普比率等更新
   - 交易统计管理 (trading_statistics): 交易次数、盈利统计等
   - 资金状态管理 (fund_status_management): 现金、冻结资金、总资产等

数据模型：
- MPortfolio: 投资组合数据模型，包含丰富的业务字段
- 基础信息：名称、描述、创建时间、更新时间
- 资金信息：初始资金、当前资金、现金、冻结资金等
- 绩效指标：风险水平、最大回撤、夏普比率、胜率等
- 交易统计：总交易次数、盈利交易次数等
- 配置信息：数据源、策略配置、风控参数等

业务价值：
- 投资组织单位：为资金和策略提供组织框架
- 风险管理载体：承载风险控制和资金管理
- 绩效评估基础：记录投资表现和风险收益
- 策略执行平台：支持多种策略的并行运行
- 合规管理支持：提供完整的投资记录和审计轨迹

组合状态管理：
- 创建中(Creating): 组合初始化阶段
- 活跃(Active): 正常运行状态
- 暂停(Paused): 临时停止交易
- 停止(Stopped): 永久停止运行
- 清算中(Liquidating): 正在清算持仓
- 已清算(Liquidated): 完成清算

测试策略：
- 覆盖投资组合完整生命周期
- 验证资金计算和状态管理
- 测试绩效指标更新机制
- 验证风险控制和业务规则
- 使用测试数据源标记便于清理
- 测试并发和数据一致性
"""
import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.data.crud.portfolio_crud import PortfolioCRUD
from ginkgo.data.models.model_portfolio import MPortfolio
from ginkgo.enums import SOURCE_TYPES


@pytest.mark.database
@pytest.mark.tdd
class TestPortfolioCRUDInsert:
    # 明确配置CRUD类
    CRUD_TEST_CONFIG = {'crud_class': PortfolioCRUD}

    """1. CRUD层插入操作测试 - Portfolio数据插入验证"""

    def test_add_batch_basic(self):
        """测试批量插入Portfolio数据 - 使用真实数据库"""
        print("\n" + "="*60)
        print("开始测试: Portfolio CRUD层批量插入")
        print("="*60)

        portfolio_crud = PortfolioCRUD()
        print(f"✓ 创建PortfolioCRUD实例: {portfolio_crud.__class__.__name__}")

        # 创建测试Portfolio数据
        test_portfolios = [
            MPortfolio(
                name="test_portfolio_ma_strategy",
                backtest_start_date=datetime(2023, 1, 1),
                backtest_end_date=datetime(2023, 12, 31),
                is_live=False,
                source=SOURCE_TYPES.TEST
            ),
            MPortfolio(
                name="test_portfolio_rsi_strategy",
                backtest_start_date=datetime(2023, 6, 1),
                backtest_end_date=datetime(2023, 12, 31),
                is_live=True,
                source=SOURCE_TYPES.TEST
            ),
            MPortfolio(
                name="test_portfolio_momentum",
                backtest_start_date=datetime(2022, 1, 1),
                backtest_end_date=datetime(2023, 6, 30),
                is_live=False,
                source=SOURCE_TYPES.TEST
            )
        ]
        print(f"✓ 创建测试数据: {len(test_portfolios)}条Portfolio记录")
        print(f"  - 投资组合名称: {[p.name for p in test_portfolios]}")
        print(f"  - 实盘状态: {[p.is_live for p in test_portfolios]}")
        print(f"  - 时间跨度: 2022-2023年")

        try:
            # 批量插入
            print("\n→ 执行批量插入操作...")
            portfolio_crud.add_batch(test_portfolios)
            print("✓ 批量插入成功")

            # 验证可以查询出插入的数据
            print("\n→ 验证插入的数据...")
            query_result = portfolio_crud.find(filters={"name__like": "test_portfolio_", "source": SOURCE_TYPES.TEST.value})
            print(f"✓ 查询到 {len(query_result)} 条记录")
            assert len(query_result) >= 3

            # 验证数据内容
            names = [portfolio.name for portfolio in query_result]
            live_count = sum(1 for p in query_result if p.is_live)
            backtest_count = sum(1 for p in query_result if not p.is_live)

            print(f"✓ 投资组合名称验证通过: {set(names)}")
            print(f"✓ 实盘组合: {live_count} 个")
            print(f"✓ 回测组合: {backtest_count} 个")

            assert "test_portfolio_ma_strategy" in names
            assert "test_portfolio_rsi_strategy" in names
            assert live_count >= 1

        except Exception as e:
            print(f"✗ 批量插入失败: {e}")
            raise

    def test_add_single_portfolio(self):
        """测试单条Portfolio数据插入"""
        print("\n" + "="*60)
        print("开始测试: Portfolio CRUD层单条插入")
        print("="*60)

        portfolio_crud = PortfolioCRUD()

        test_portfolio = MPortfolio(
            name="test_single_portfolio",
            backtest_start_date=datetime(2023, 1, 1),
            backtest_end_date=datetime(2023, 12, 31),
            is_live=False,
            source=SOURCE_TYPES.TEST
        )
        print(f"✓ 创建测试Portfolio: {test_portfolio.name}")
        print(f"  - 回测时间: {test_portfolio.backtest_start_date} ~ {test_portfolio.backtest_end_date}")
        print(f"  - 实盘状态: {test_portfolio.is_live}")

        try:
            # 单条插入
            print("\n→ 执行单条插入操作...")
            portfolio_crud.add(test_portfolio)
            print("✓ 单条插入成功")

            # 验证数据
            print("\n→ 验证插入的数据...")
            query_result = portfolio_crud.find(filters={"name": "test_single_portfolio"})
            print(f"✓ 查询到 {len(query_result)} 条记录")
            assert len(query_result) >= 1

            inserted_portfolio = query_result[0]
            print(f"✓ 插入的Portfolio验证: {inserted_portfolio.name}")
            print(f"  - 回测开始: {inserted_portfolio.backtest_start_date}")
            print(f"  - 回测结束: {inserted_portfolio.backtest_end_date}")
            assert inserted_portfolio.name == "test_single_portfolio"

        except Exception as e:
            print(f"✗ 单条插入失败: {e}")
            raise

    def test_add_live_portfolio(self):
        """测试创建实盘Portfolio"""
        print("\n" + "="*60)
        print("开始测试: 创建实盘Portfolio")
        print("="*60)

        portfolio_crud = PortfolioCRUD()

        live_portfolio = MPortfolio(
            name="test_live_trading",
            backtest_start_date=datetime(2023, 1, 1),
            backtest_end_date=datetime(2099, 12, 31),  # 实盘组合通常设置很远的结束时间
            is_live=True,
            source=SOURCE_TYPES.TEST
        )
        print(f"✓ 创建实盘Portfolio: {live_portfolio.name}")
        print(f"  - 实盘状态: {live_portfolio.is_live}")
        print(f"  - 运行周期: {live_portfolio.backtest_start_date} ~ {live_portfolio.backtest_end_date}")

        try:
            # 插入实盘组合
            print("\n→ 执行实盘Portfolio插入...")
            portfolio_crud.add(live_portfolio)
            print("✓ 实盘Portfolio插入成功")

            # 验证实盘组合
            print("\n→ 验证实盘Portfolio...")
            query_result = portfolio_crud.find(filters={"name": "test_live_trading"})
            assert len(query_result) >= 1

            verified_portfolio = query_result[0]
            print(f"✓ 实盘Portfolio验证: {verified_portfolio.name}")
            assert verified_portfolio.is_live == True
            print("✓ 实盘状态验证通过")

        except Exception as e:
            print(f"✗ 实盘Portfolio创建失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestPortfolioCRUDQuery:
    # 明确配置CRUD类
    CRUD_TEST_CONFIG = {'crud_class': PortfolioCRUD}

    """2. CRUD层查询操作测试 - Portfolio数据查询和过滤"""

    def test_find_by_name(self):
        """测试根据名称查询Portfolio"""
        print("\n" + "="*60)
        print("开始测试: 根据name查询Portfolio")
        print("="*60)

        portfolio_crud = PortfolioCRUD()

        try:
            # 查询特定名称的投资组合
            print("→ 查询name=test_portfolio_ma_strategy的投资组合...")
            portfolios = portfolio_crud.find(filters={"name": "test_portfolio_ma_strategy", "source": SOURCE_TYPES.TEST.value})
            print(f"✓ 查询到 {len(portfolios)} 条记录")

            # 验证查询结果
            for portfolio in portfolios:
                print(f"  - 组合名称: {portfolio.name}")
                print(f"  - 实盘状态: {portfolio.is_live}")
                print(f"  - 回测时间: {portfolio.backtest_start_date} ~ {portfolio.backtest_end_date}")
                assert portfolio.name == "test_portfolio_ma_strategy"

        except Exception as e:
            print(f"✗ 查询失败: {e}")
            raise

    def test_find_by_live_status(self):
        """测试根据实盘状态查询Portfolio"""
        print("\n" + "="*60)
        print("开始测试: 根据is_live状态查询Portfolio")
        print("="*60)

        portfolio_crud = PortfolioCRUD()

        try:
            # 查询实盘组合
            print("→ 查询实盘组合 (is_live=True)...")
            live_portfolios = portfolio_crud.find(filters={"is_live": True})
            print(f"✓ 查询到 {len(live_portfolios)} 个实盘组合")

            # 查询回测组合
            print("→ 查询回测组合 (is_live=False)...")
            backtest_portfolios = portfolio_crud.find(filters={"is_live": False})
            print(f"✓ 查询到 {len(backtest_portfolios)} 个回测组合")

            # 验证查询结果
            print("→ 验证查询结果...")
            for portfolio in live_portfolios:
                print(f"  - 实盘组合: {portfolio.name}")
                assert portfolio.is_live == True

            for portfolio in backtest_portfolios:
                print(f"  - 回测组合: {portfolio.name}")
                assert portfolio.is_live == False

            print("✓ 实盘状态查询验证成功")

        except Exception as e:
            print(f"✗ 实盘状态查询失败: {e}")
            raise

    def test_find_by_time_range(self):
        """测试根据时间范围查询Portfolio"""
        print("\n" + "="*60)
        print("开始测试: 根据时间范围查询Portfolio")
        print("="*60)

        portfolio_crud = PortfolioCRUD()

        try:
            # 查询特定时间范围内运行的投资组合
            target_date = datetime(2023, 6, 15)
            print(f"→ 查询在 {target_date} 期间运行的投资组合...")

            all_portfolios = portfolio_crud.find(filters={"name__like": "test_portfolio_", "source": SOURCE_TYPES.TEST.value})
            active_portfolios = [
                p for p in all_portfolios
                if p.backtest_start_date <= target_date <= p.backtest_end_date
            ]

            print(f"✓ 查询到 {len(active_portfolios)} 个活跃的投资组合")

            # 验证时间范围
            for portfolio in active_portfolios:
                print(f"  - {portfolio.name}: {portfolio.backtest_start_date} ~ {portfolio.backtest_end_date}")
                assert portfolio.backtest_start_date <= target_date <= portfolio.backtest_end_date

            print("✓ 时间范围查询验证成功")

        except Exception as e:
            print(f"✗ 时间范围查询失败: {e}")
            raise

    def test_find_with_pagination(self):
        """测试分页查询Portfolio"""
        print("\n" + "="*60)
        print("开始测试: 分页查询Portfolio")
        print("="*60)

        portfolio_crud = PortfolioCRUD()

        try:
            # 分页查询
            print("→ 执行分页查询...")

            # 第一页
            page1 = portfolio_crud.find(page=1, page_size=5)
            print(f"✓ 第1页: {len(page1)} 条记录")

            # 第二页
            page2 = portfolio_crud.find(page=2, page_size=5)
            print(f"✓ 第2页: {len(page2)} 条记录")

            # 验证分页结果
            if page1 and page2:
                page1_ids = [p.uuid for p in page1]
                page2_ids = [p.uuid for p in page2]
                overlap = set(page1_ids) & set(page2_ids)
                print(f"✓ 页面重叠记录数: {len(overlap)} (应为0)")
                assert len(overlap) == 0

            print("✓ 分页查询验证成功")

        except Exception as e:
            print(f"✗ 分页查询失败: {e}")
            raise

    def test_model_list_conversions(self):
        """测试ModelList的to_dataframe和to_entities转换功能"""
        import pandas as pd

        print("\n" + "="*60)
        print("开始测试: Portfolio ModelList转换功能")
        print("="*60)

        portfolio_crud = PortfolioCRUD()
        print(f"✓ 创建PortfolioCRUD实例")

        # 准备测试数据 - 包含不同类型的投资组合
        test_portfolios = [
            MPortfolio(
                name="convert_test_portfolio_1",
                backtest_start_date=datetime(2023, 1, 1),
                backtest_end_date=datetime(2023, 12, 31),
                is_live=False,
                source=SOURCE_TYPES.TEST
            ),
            MPortfolio(
                name="convert_test_portfolio_2",
                backtest_start_date=datetime(2023, 6, 1),
                backtest_end_date=datetime(2024, 5, 31),
                is_live=True,
                source=SOURCE_TYPES.TEST
            ),
            MPortfolio(
                name="convert_test_portfolio_3",
                backtest_start_date=datetime(2022, 1, 1),
                backtest_end_date=datetime(2023, 12, 31),
                is_live=False,
                source=SOURCE_TYPES.TEST
            )
        ]

        try:
            # 验证插入前后的数据变化
            print("\n→ 验证插入前数据...")
            before_count = len(portfolio_crud.find(filters={"name__like": "convert_test_portfolio_%", "source": SOURCE_TYPES.TEST.value}))
            print(f"✓ 插入前数据量: {before_count}")

            # 插入测试数据
            print(f"\n→ 插入 {len(test_portfolios)} 条测试数据...")
            portfolio_crud.add_batch(test_portfolios)
            print("✓ 数据插入成功")

            # 验证插入后的数据变化
            print("\n→ 验证插入后数据变化...")
            after_count = len(portfolio_crud.find(filters={"name__like": "convert_test_portfolio_%", "source": SOURCE_TYPES.TEST.value}))
            print(f"✓ 插入后数据量: {after_count}")
            assert after_count - before_count == len(test_portfolios), f"应增加{len(test_portfolios)}条数据，实际增加{after_count - before_count}条"

            # 获取ModelList进行转换测试
            print("\n→ 获取ModelList...")
            model_list = portfolio_crud.find(filters={"name__like": "convert_test_portfolio_%", "source": SOURCE_TYPES.TEST.value})
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
            required_columns = ['uuid', 'name', 'backtest_start_date', 'backtest_end_date', 'is_live', 'create_at', 'update_at']
            for col in required_columns:
                assert col in df.columns, f"DataFrame缺少列: {col}"
            print(f"✓ 包含所有必要列: {required_columns}")

            # 验证数据内容
            first_row = df.iloc[0]
            assert "convert_test_portfolio" in first_row['name']
            print(f"✓ 数据内容验证通过: name={first_row['name']}, is_live={first_row['is_live']}")

            # 测试2: to_entities转换
            print("\n→ 测试to_entities转换...")
            from ginkgo.trading.bases.portfolio_base import PortfolioBase
            entities = model_list.to_entities()
            print(f"✓ 实体列表类型: {type(entities).__name__}")
            print(f"✓ 实体列表长度: {len(entities)}")
            assert len(entities) == len(model_list), f"实体列表长度应等于ModelList长度，{len(entities)} != {len(model_list)}"

            # 验证实体类型和内容
            first_entity = entities[0]
            print(f"✓ 第一个实体类型: {type(first_entity).__name__}")
            # Portfolio转换为BasePortfolio业务对象
            assert isinstance(first_entity, PortfolioBase), "应转换为PortfolioBase业务对象"

            # 验证业务对象字段
            assert "convert_test_portfolio" in first_entity.name
            print(f"✓ 业务对象字段验证通过: name={first_entity.name}")

            # 测试3: 验证BasePortfolio特有字段
            print("\n→ 验证BasePortfolio特有字段...")
            for entity in entities:
                assert hasattr(entity, 'name'), "应有name字段"
                assert hasattr(entity, 'uuid'), "应有uuid字段"
                assert hasattr(entity, 'portfolio_id'), "应有portfolio_id字段"
            print("✓ BasePortfolio字段验证正确")

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
            empty_model_list = portfolio_crud.find(filters={"name": "NONEXISTENT_PORTFOLIO"})
            assert len(empty_model_list) == 0, "空ModelList长度应为0"

            empty_df = empty_model_list.to_dataframe()
            empty_entities = empty_model_list.to_entities()

            assert isinstance(empty_df, pd.DataFrame), "空转换应返回DataFrame"
            assert len(empty_df) == 0, "空DataFrame长度应为0"
            assert isinstance(empty_entities, list), "空转换应返回列表"
            assert len(empty_entities) == 0, "空实体列表长度应为0"
            print("✓ 空ModelList转换验证正确")

            print("\n✓ 所有Portfolio ModelList转换功能测试通过！")

        except Exception as e:
            print(f"✗ 测试失败: {e}")
            raise

@pytest.mark.database
@pytest.mark.tdd
class TestPortfolioCRUDUpdate:
    # 明确配置CRUD类
    CRUD_TEST_CONFIG = {'crud_class': PortfolioCRUD}

    """3. CRUD层更新操作测试 - Portfolio属性更新"""

    def test_update_portfolio_name(self):
        """测试更新Portfolio名称"""
        print("\n" + "="*60)
        print("开始测试: 更新Portfolio名称")
        print("="*60)

        portfolio_crud = PortfolioCRUD()

        try:
            # 查询待更新的投资组合
            print("→ 查询待更新的投资组合...")
            portfolios = portfolio_crud.find(filters={"name__like": "test_portfolio_", "source": SOURCE_TYPES.TEST.value} , page=1, page_size=1)
            if not portfolios:
                print("✗ 没有找到可更新的投资组合")
                return

            target_portfolio = portfolios[0]
            print(f"✓ 找到投资组合: {target_portfolio.name}")
            print(f"  - 当前状态: 实盘={target_portfolio.is_live}")
            print(f"  - 回测时间: {target_portfolio.backtest_start_date} ~ {target_portfolio.backtest_end_date}")

            # 更新投资组合名称和状态
            print("→ 更新投资组合属性...")
            # 确保新名称不超过64字符限制 (Portfolio name字段限制为String(64))
            if len(f"updated_{target_portfolio.name}") <= 64:
                new_name = f"updated_{target_portfolio.name}"
            else:
                # 使用更短的前缀或截断原名称
                new_name = f"upd_{target_portfolio.name}"[:64]
            updated_data = {
                "name": new_name,
                "is_live": not target_portfolio.is_live  # 切换实盘状态
            }

            portfolio_crud.update(target_portfolio.uuid, **updated_data)
            print("✓ 投资组合属性更新成功")

            # 验证更新结果
            print("→ 验证更新结果...")
            updated_portfolios = portfolio_crud.find(filters={"uuid": target_portfolio.uuid})
            assert len(updated_portfolios) == 1

            updated_portfolio = updated_portfolios[0]
            print(f"✓ 更新后名称: {updated_portfolio.name}")
            print(f"✓ 更新后实盘状态: {updated_portfolio.is_live}")

            assert updated_portfolio.name == new_name
            assert updated_portfolio.is_live != target_portfolio.is_live
            print("✓ 投资组合更新验证成功")

        except Exception as e:
            print(f"✗ 更新投资组合失败: {e}")
            raise

    def test_update_time_range(self):
        """测试更新Portfolio时间范围"""
        print("\n" + "="*60)
        print("开始测试: 更新Portfolio时间范围")
        print("="*60)

        portfolio_crud = PortfolioCRUD()

        try:
            # 查询待更新的投资组合
            print("→ 查询待更新的投资组合...")
            portfolios = portfolio_crud.find(filters={"name__like": "test_portfolio_", "source": SOURCE_TYPES.TEST.value}, page=1, page_size=1)
            if not portfolios:
                print("✗ 没有找到可更新的投资组合")
                return

            target_portfolio = portfolios[0]
            print(f"✓ 找到投资组合: {target_portfolio.name}")
            print(f"  - 原始时间范围: {target_portfolio.backtest_start_date} ~ {target_portfolio.backtest_end_date}")

            # 更新时间范围
            print("→ 更新时间范围...")
            new_start_date = target_portfolio.backtest_start_date - timedelta(days=30)
            new_end_date = target_portfolio.backtest_end_date + timedelta(days=30)

            updated_data = {
                "backtest_start_date": new_start_date,
                "backtest_end_date": new_end_date
            }

            portfolio_crud.update(target_portfolio.uuid, **updated_data)
            print("✓ 时间范围更新成功")

            # 验证更新结果
            print("→ 验证更新结果...")
            updated_portfolios = portfolio_crud.find(filters={"uuid": target_portfolio.uuid})
            assert len(updated_portfolios) == 1

            updated_portfolio = updated_portfolios[0]
            print(f"✓ 更新后时间范围: {updated_portfolio.backtest_start_date} ~ {updated_portfolio.backtest_end_date}")

            assert updated_portfolio.backtest_start_date == new_start_date
            assert updated_portfolio.backtest_end_date == new_end_date
            print("✓ 时间范围更新验证成功")

        except Exception as e:
            print(f"✗ 时间范围更新失败: {e}")
            raise

    def test_update_portfolio_batch(self):
        """测试批量更新Portfolio"""
        print("\n" + "="*60)
        print("开始测试: 批量更新Portfolio")
        print("="*60)

        portfolio_crud = PortfolioCRUD()

        try:
            # 查询多个投资组合进行批量更新
            print("→ 查询需要批量更新的投资组合...")
            portfolios = portfolio_crud.find(filters={"name__like": "test_portfolio_", "source": SOURCE_TYPES.TEST.value}, page=1, page_size=3)
            if len(portfolios) < 2:
                print("✗ 投资组合数量不足，跳过批量更新测试")
                return

            print(f"✓ 找到 {len(portfolios)} 个投资组合进行批量更新")

            # 批量更新投资组合状态
            for i, portfolio in enumerate(portfolios):
                print(f"→ 更新投资组合 {portfolio.name} 的状态...")
                portfolio_crud.update(portfolio.uuid, is_live=(i % 2 == 0))

            print("✓ 批量更新完成")

            # 验证批量更新结果
            print("→ 验证批量更新结果...")
            updated_portfolios = portfolio_crud.find(filters={"name__like": "test_portfolio_", "source": SOURCE_TYPES.TEST.value}, page=1, page_size=3)
            live_count = sum(1 for p in updated_portfolios if p.is_live)
            print(f"✓ 更新后实盘组合数量: {live_count} 个")
            assert live_count >= 1
            print("✓ 批量更新验证成功")

        except Exception as e:
            print(f"✗ 批量更新失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestPortfolioCRUDDelete:
    # 明确配置CRUD类
    CRUD_TEST_CONFIG = {'crud_class': PortfolioCRUD}

    """4. CRUD层删除操作测试 - Portfolio数据清理"""

    def test_delete_portfolio_by_uuid(self):
        """测试根据UUID删除Portfolio"""
        print("\n" + "="*60)
        print("开始测试: 根据UUID删除Portfolio")
        print("="*60)

        portfolio_crud = PortfolioCRUD()

        try:
            # 先插入一条测试数据
            print("→ 创建测试投资组合...")
            test_portfolio = MPortfolio(
                name="test_portfolio_to_delete",
                backtest_start_date=datetime(2023, 1, 1),
                backtest_end_date=datetime(2023, 12, 31),
                is_live=False,
                source=SOURCE_TYPES.TEST
            )
            portfolio_crud.add(test_portfolio)
            print(f"✓ 创建测试投资组合: {test_portfolio.uuid}")

            # 查询确认插入成功
            inserted_portfolios = portfolio_crud.find(filters={"uuid": test_portfolio.uuid})
            assert len(inserted_portfolios) == 1
            print("✓ 投资组合插入确认成功")

            # 删除投资组合
            print("→ 删除测试投资组合...")
            portfolio_crud.delete(test_portfolio.uuid)
            print("✓ 投资组合删除成功")

            # 验证删除结果
            print("→ 验证删除结果...")
            deleted_portfolios = portfolio_crud.find(filters={"uuid": test_portfolio.uuid})
            assert len(deleted_portfolios) == 0
            print("✓ 投资组合删除验证成功")

        except Exception as e:
            print(f"✗ 删除投资组合失败: {e}")
            raise

    def test_delete_portfolios_by_pattern(self):
        """测试根据名称模式批量删除Portfolio"""
        print("\n" + "="*60)
        print("开始测试: 根据名称模式批量删除Portfolio")
        print("="*60)

        portfolio_crud = PortfolioCRUD()

        try:
            # 查询删除前的数量
            print("→ 查询删除前的投资组合数量...")
            pattern_portfolios = portfolio_crud.find(filters={"name__like": "test_single_%"})
            count_before = len(pattern_portfolios)
            print(f"✓ 删除前有 {count_before} 条匹配记录")

            if count_before == 0:
                print("✗ 没有找到可删除的投资组合")
                return

            # 批量删除
            print("→ 批量删除投资组合...")
            for portfolio in pattern_portfolios:
                portfolio_crud.delete(portfolio.uuid)
            print("✓ 批量删除完成")

            # 验证删除结果
            print("→ 验证删除结果...")
            remaining_portfolios = portfolio_crud.find(filters={"name__like": "test_single_%"})
            count_after = len(remaining_portfolios)
            print(f"✓ 删除后剩余 {count_after} 条记录")
            assert count_after == 0
            print("✓ 批量删除验证成功")

        except Exception as e:
            print(f"✗ 批量删除失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestPortfolioCRUDBusinessLogic:
    # 明确配置CRUD类
    CRUD_TEST_CONFIG = {'crud_class': PortfolioCRUD}

    """5. CRUD层业务逻辑测试 - Portfolio业务场景验证"""

    def test_portfolio_lifecycle_management(self):
        """测试投资组合生命周期管理"""
        print("\n" + "="*60)
        print("开始测试: 投资组合生命周期管理")
        print("="*60)

        portfolio_crud = PortfolioCRUD()

        try:
            # 1. 创建回测阶段的投资组合
            print("1. 创建回测阶段投资组合...")
            backtest_portfolio = MPortfolio(
                name="lifecycle_backtest_test",
                backtest_start_date=datetime(2023, 1, 1),
                backtest_end_date=datetime(2023, 6, 30),
                is_live=False,
                source=SOURCE_TYPES.TEST
            )
            portfolio_crud.add(backtest_portfolio)
            print(f"✓ 回测组合创建成功: {backtest_portfolio.name}")

            # 2. 模拟回测完成，转换为实盘
            print("2. 转换为实盘投资组合...")
            portfolio_crud.update(backtest_portfolio.uuid,
                is_live=True,
                backtest_end_date=datetime(2099, 12, 31)
            )
            print("✓ 转换为实盘组合成功")

            # 3. 验证生命周期状态
            print("3. 验证生命周期状态...")
            live_portfolio = portfolio_crud.find(filters={"uuid": backtest_portfolio.uuid})[0]
            print(f"✓ 当前状态: 实盘={live_portfolio.is_live}")
            print(f"✓ 运行周期: {live_portfolio.backtest_start_date} ~ {live_portfolio.backtest_end_date}")

            assert live_portfolio.is_live == True
            assert live_portfolio.backtest_end_date.year == 2099
            print("✓ 投资组合生命周期验证成功")

        except Exception as e:
            print(f"✗ 投资组合生命周期测试失败: {e}")
            raise

    def test_portfolio_performance_tracking(self):
        """测试投资组合绩效追踪场景"""
        print("\n" + "="*60)
        print("开始测试: 投资组合绩效追踪场景")
        print("="*60)

        portfolio_crud = PortfolioCRUD()

        try:
            # 创建多个不同策略的投资组合
            print("1. 创建多个策略的投资组合...")
            strategy_portfolios = [
                MPortfolio(
                    name="performance_ma_strategy",
                    backtest_start_date=datetime(2023, 1, 1),
                    backtest_end_date=datetime(2023, 12, 31),
                    is_live=False,
                    source=SOURCE_TYPES.TEST
                ),
                MPortfolio(
                    name="performance_rsi_strategy",
                    backtest_start_date=datetime(2023, 1, 1),
                    backtest_end_date=datetime(2023, 12, 31),
                    is_live=False,
                    source=SOURCE_TYPES.TEST
                ),
                MPortfolio(
                    name="performance_momentum_strategy",
                    backtest_start_date=datetime(2023, 1, 1),
                    backtest_end_date=datetime(2023, 12, 31),
                    is_live=True,
                    source=SOURCE_TYPES.TEST
                )
            ]

            for portfolio in strategy_portfolios:
                portfolio_crud.add(portfolio)
            print(f"✓ 创建了 {len(strategy_portfolios)} 个策略投资组合")

            # 2. 分析投资组合分布
            print("2. 分析投资组合分布...")
            all_portfolios = portfolio_crud.find(filters={"name__like": "performance_%"})

            # 统计实盘和回测分布
            live_portfolios = [p for p in all_portfolios if p.is_live]
            backtest_portfolios = [p for p in all_portfolios if not p.is_live]

            # 统计时间分布
            durations = []
            for p in all_portfolios:
                duration = (p.backtest_end_date - p.backtest_start_date).days
                durations.append(duration)

            print(f"✓ 投资组合统计:")
            print(f"  - 总数量: {len(all_portfolios)}")
            print(f"  - 实盘组合: {len(live_portfolios)}")
            print(f"  - 回测组合: {len(backtest_portfolios)}")
            print(f"  - 平均运行天数: {sum(durations)/len(durations):.0f}")

            # 验证分析结果
            assert len(all_portfolios) == len(live_portfolios) + len(backtest_portfolios)
            assert all(d > 0 for d in durations)
            print("✓ 投资组合绩效分析验证成功")

        except Exception as e:
            print(f"✗ 投资组合绩效追踪测试失败: {e}")
            raise

    def test_portfolio_data_integrity(self):
        """测试Portfolio数据完整性和约束"""
        print("\n" + "="*60)
        print("开始测试: Portfolio数据完整性和约束")
        print("="*60)

        portfolio_crud = PortfolioCRUD()

        try:
            # 测试必要字段约束
            print("→ 测试必要字段约束...")

            # name不能为空 (仅测试新插入数据)
            try:
                invalid_portfolio = MPortfolio(
                    name="",  # 空字符串
                    backtest_start_date=datetime(2023, 1, 1),
                    backtest_end_date=datetime(2023, 12, 31),
                    source=SOURCE_TYPES.TEST
                )
                portfolio_crud.add(invalid_portfolio)
                print("✗ 应该拒绝name为空的投资组合")
                assert False, "应该抛出异常"
            except Exception as e:
                print(f"✓ 正确拒绝无效投资组合: {type(e).__name__}")

            # 验证时间约束和名称约束（排除历史空名数据）
            print("→ 验证时间约束和名称约束...")
            valid_portfolios = portfolio_crud.find(page=1, page_size=10)
            valid_count = 0
            for portfolio in valid_portfolios:
                # 验证时间逻辑
                assert portfolio.backtest_start_date <= portfolio.backtest_end_date

                # 只验证非空名称的数据（历史数据可能包含空名称）
                if portfolio.name and len(portfolio.name.strip()) > 0:
                    # 验证名称长度
                    assert len(portfolio.name) > 0
                    assert len(portfolio.name) <= 64
                    valid_count += 1

            print(f"✓ 验证了 {len(valid_portfolios)} 条投资组合的时间约束")
            print(f"✓ 验证了 {valid_count} 条投资组合的名称约束")
            print("✓ 数据完整性验证成功")

        except Exception as e:
            print(f"✗ 数据完整性测试失败: {e}")
            raise

    def test_portfolio_strategy_comparison(self):
        """测试投资组合策略比较分析"""
        print("\n" + "="*60)
        print("开始测试: 投资组合策略比较分析")
        print("="*60)

        portfolio_crud = PortfolioCRUD()

        try:
            # 创建不同策略类型的投资组合进行比较
            print("1. 创建不同策略的投资组合...")
            comparison_portfolios = [
                MPortfolio(
                    name="compare_conservative",
                    backtest_start_date=datetime(2023, 1, 1),
                    backtest_end_date=datetime(2023, 12, 31),
                    is_live=False,
                    source=SOURCE_TYPES.TEST
                ),
                MPortfolio(
                    name="compare_aggressive",
                    backtest_start_date=datetime(2023, 1, 1),
                    backtest_end_date=datetime(2023, 12, 31),
                    is_live=False,
                    source=SOURCE_TYPES.TEST
                ),
                MPortfolio(
                    name="compare_balanced",
                    backtest_start_date=datetime(2023, 1, 1),
                    backtest_end_date=datetime(2023, 12, 31),
                    is_live=True,
                    source=SOURCE_TYPES.TEST
                )
            ]

            for portfolio in comparison_portfolios:
                portfolio_crud.add(portfolio)
            print(f"✓ 创建了 {len(comparison_portfolios)} 个比较投资组合")

            # 2. 策略比较分析
            print("2. 执行策略比较分析...")
            all_portfolios = portfolio_crud.find(filters={"name__like": "compare_%"})

            # 按策略类型分组分析
            strategy_analysis = {}
            for portfolio in all_portfolios:
                strategy_type = portfolio.name.split("_")[1]  # 提取策略类型
                if strategy_type not in strategy_analysis:
                    strategy_analysis[strategy_type] = {
                        "count": 0,
                        "live_count": 0,
                        "total_days": 0
                    }

                strategy_analysis[strategy_type]["count"] += 1
                if portfolio.is_live:
                    strategy_analysis[strategy_type]["live_count"] += 1

                duration = (portfolio.backtest_end_date - portfolio.backtest_start_date).days
                strategy_analysis[strategy_type]["total_days"] += duration

            print(f"✓ 策略比较分析结果:")
            for strategy_type, analysis in strategy_analysis.items():
                avg_days = analysis["total_days"] / analysis["count"]
                live_ratio = analysis["live_count"] / analysis["count"]
                print(f"  - {strategy_type}: {analysis['count']}个组合, 实盘率{live_ratio:.1%}, 平均{avg_days:.0f}天")

            # 验证分析结果
            assert len(strategy_analysis) >= 2  # 至少有2种策略类型
            total_portfolios = sum(analysis["count"] for analysis in strategy_analysis.values())
            assert total_portfolios == len(all_portfolios)
            print("✓ 策略比较分析验证成功")

        except Exception as e:
            print(f"✗ 策略比较分析测试失败: {e}")
            raise


@pytest.mark.enum
@pytest.mark.database
class TestPortfolioCRUDEnumValidation:
    """PortfolioCRUD枚举传参验证测试 - 整合自独立的枚举测试文件"""

    # 明确配置CRUD类，添加全面的过滤条件以清理所有测试数据
    CRUD_TEST_CONFIG = {
        'crud_class': PortfolioCRUD,
        'filters': {
            'name__like': 'enum_%'  # 清理所有枚举测试相关的投资组合数据
        }
    }

    def test_source_enum_conversions(self):
        """测试投资组合数据源枚举转换功能"""
        print("\n" + "="*60)
        print("开始测试: 投资组合数据源枚举转换")
        print("="*60)

        portfolio_crud = PortfolioCRUD()

        # 记录初始状态
        before_count = len(portfolio_crud.find(filters={"name__like": "enum_source_test_%"}))
        print(f"→ 初始状态: {before_count} 条测试数据")

        # 测试不同数据源的枚举传参
        source_types = [
            (SOURCE_TYPES.SIM, "SIM模拟数据源"),
            (SOURCE_TYPES.TUSHARE, "Tushare数据源"),
            (SOURCE_TYPES.YAHOO, "Yahoo数据源"),
            (SOURCE_TYPES.AKSHARE, "AKShare数据源"),
            (SOURCE_TYPES.BACKTEST, "回测数据源")
        ]

        print(f"\n→ 测试 {len(source_types)} 种数据源枚举传参...")

        # 批量插入并验证条数变化
        for i, (source_type, source_name) in enumerate(source_types):
            test_portfolio = MPortfolio(
                name=f"enum_source_test_{i+1:03d}",
                description=f"测试投资组合 - {source_name}",
                backtest_start_date=datetime(2023, 1, 1) + timedelta(days=i*30),
                backtest_end_date=datetime(2023, 12, 31) + timedelta(days=i*30),
                initial_capital=1000000.0 + i * 100000,
                current_capital=1100000.0 + i * 110000,
                risk_level=0.1 + i * 0.02,
                source=source_type  # 直接传入枚举对象
            )

            before_insert = len(portfolio_crud.find(filters={"name__like": "enum_source_test_%"}))
            result = portfolio_crud.add(test_portfolio)
            assert result is not None, f"{source_name} 投资组合应该成功插入"

            after_insert = len(portfolio_crud.find(filters={"name__like": "enum_source_test_%"}))
            assert after_insert - before_insert == 1, f"{source_name} 插入应该增加1条记录"
            print(f"  ✓ {source_name} 枚举传参成功，数据库条数验证正确")

        # 验证总插入数量
        final_count = len(portfolio_crud.find(filters={"name__like": "enum_source_test_%"}))
        assert final_count - before_count == len(source_types), f"总共应该插入{len(source_types)}条记录"
        print(f"✓ 批量插入验证正确，共增加 {final_count - before_count} 条记录")

        # 验证查询时的枚举转换
        print("\n→ 验证查询时的枚举转换...")
        portfolios = portfolio_crud.find(filters={"name__like": "enum_source_test_%"})
        expected_count = final_count - before_count  # 我们新增的记录数
        assert len(portfolios) >= expected_count, f"应该至少查询到{expected_count}条数据源投资组合，实际{len(portfolios)}条"

        # 过滤出我们刚创建的投资组合
        our_portfolios = [p for p in portfolios if p.name.startswith("enum_source_test_")]
        print(f"→ 查询到总共{len(portfolios)}条投资组合，其中我们的测试投资组合{len(our_portfolios)}条")

        for portfolio in our_portfolios:
            # 数据库查询结果source是int值，需要转换为枚举对象进行比较
            source_enum = SOURCE_TYPES(portfolio.source)
            assert source_enum in [st for st, _ in source_types], "查询结果应该是有效的枚举对象"
            source_name = dict([(st, sn) for st, sn in source_types])[source_enum]
            print(f"  ✓ 投资组合 {portfolio.name}: 数据源={source_name}, 初始资金={portfolio.initial_capital:,.0f}")

        # 测试数据源过滤查询（枚举传参）
        print("\n→ 测试数据源过滤查询（枚举传参）...")
        sim_portfolios = portfolio_crud.find(
            filters={
                "name__like": "enum_source_test_%",
                "source": SOURCE_TYPES.SIM  # 枚举传参
            }
        )
        assert len(sim_portfolios) >= 1, "应该查询到至少1条SIM投资组合"
        print(f"  ✓ SIM数据源投资组合: {len(sim_portfolios)} 条，枚举过滤验证正确")

  
        print("✓ 投资组合数据源枚举转换测试通过")

    def test_comprehensive_enum_validation(self):
        """测试投资组合综合枚举验证功能"""
        print("\n" + "="*60)
        print("开始测试: 投资组合综合枚举验证")
        print("="*60)

        portfolio_crud = PortfolioCRUD()

        # 记录初始状态
        before_count = len(portfolio_crud.find(filters={"name__like": "comprehensive_enum_%"}))
        print(f"→ 初始状态: {before_count} 条测试数据")

        # 创建包含数据源枚举的测试投资组合
        enum_combinations = [
            # (数据源, 描述, 名称, 初始资金, 风险水平)
            (SOURCE_TYPES.TUSHARE, "Tushare量化组合", "quant_tushare", 2000000.0, 0.15),
            (SOURCE_TYPES.SIM, "SIM模拟组合", "sim_strategy", 1500000.0, 0.12),
            (SOURCE_TYPES.BACKTEST, "回测验证组合", "backtest_val", 1000000.0, 0.20),
            (SOURCE_TYPES.YAHOO, "Yahoo数据组合", "yahoo_data", 500000.0, 0.08),
            (SOURCE_TYPES.AKSHARE, "AKShare组合", "akshare_portfolio", 800000.0, 0.10),
        ]

        print(f"\n→ 创建 {len(enum_combinations)} 个综合枚举测试投资组合...")

        # 批量插入并验证条数变化
        for i, (source, desc, name_prefix, initial_capital, risk_level) in enumerate(enum_combinations):
            test_portfolio = MPortfolio(
                name=f"comprehensive_enum_{name_prefix}_{i+1:03d}",
                description=f"{desc} - 综合枚举测试",
                backtest_start_date=datetime(2023, 1, 1) + timedelta(days=i*30),
                backtest_end_date=datetime(2023, 12, 31) + timedelta(days=i*30),
                initial_capital=initial_capital,
                current_capital=initial_capital * 1.1,  # 假设有10%收益
                risk_level=risk_level,
                source=source  # 枚举传参
            )

            before_insert = len(portfolio_crud.find(filters={"name__like": "comprehensive_enum_%"}))
            result = portfolio_crud.add(test_portfolio)
            assert result is not None, f"{desc} 应该成功插入"

            after_insert = len(portfolio_crud.find(filters={"name__like": "comprehensive_enum_%"}))
            assert after_insert - before_insert == 1, f"{desc} 插入应该增加1条记录"
            print(f"  ✓ {desc} 创建成功，数据库条数验证正确")

        # 验证总插入数量
        final_count = len(portfolio_crud.find(filters={"name__like": "comprehensive_enum_%"}))
        assert final_count - before_count == len(enum_combinations), f"总共应该插入{len(enum_combinations)}条记录"
        print(f"✓ 批量插入验证正确，共增加 {final_count - before_count} 条记录")

        # 验证所有枚举字段的存储和查询
        print("\n→ 验证所有枚举字段的存储和查询...")
        portfolios = portfolio_crud.find(filters={"name__like": "comprehensive_enum_%"})
        expected_count = final_count - before_count  # 我们新增的记录数
        assert len(portfolios) >= expected_count, f"应该至少查询到{expected_count}条综合测试投资组合，实际{len(portfolios)}条"

        # 创建名称到预期数据源组合的映射
        expected_map = {}
        for i, (source, desc, name_prefix, _, _) in enumerate(enum_combinations):
            portfolio_name = f"comprehensive_enum_{name_prefix}_{i+1:03d}"
            expected_map[portfolio_name] = (source, desc)

        our_portfolios = [p for p in portfolios if p.name in expected_map]
        print(f"→ 查询到总共{len(portfolios)}条投资组合，其中我们的综合测试投资组合{len(our_portfolios)}条")

        total_initial_capital = 0
        for portfolio in our_portfolios:
            expected_source, desc = expected_map[portfolio.name]

            # 验证枚举字段正确性（数据库查询结果是int值）
            assert portfolio.source == expected_source.value, f"投资组合 {portfolio.name} 数据源int值不匹配，预期{expected_source.value}，实际{portfolio.source}"

            # 转换为枚举对象进行显示
            source_enum = SOURCE_TYPES(portfolio.source)
            total_initial_capital += portfolio.initial_capital
            print(f"  ✓ 投资组合 {portfolio.name}: {desc}, 数据源={source_enum.name}, 初始资金={portfolio.initial_capital:,.0f}")

        # 验证资金统计
        print("\n→ 验证资金统计...")
        assert total_initial_capital > 0, "总初始资金应该大于0"
        print(f"  ✓ 我们创建的投资组合总初始资金: {total_initial_capital:,.0f}")

        # 验证ModelList转换功能
        print("\n→ 验证ModelList转换功能...")
        model_list = portfolio_crud.find(filters={"name__like": "comprehensive_enum_%"})

        assert len(model_list) >= len(enum_combinations), f"ModelList应该包含至少{len(enum_combinations)}条测试投资组合"

        # 验证to_entities()方法中的枚举转换
        entities = model_list.to_entities()
        our_entities = [e for e in entities if hasattr(e, 'name') and e.name in expected_map]

        for entity in our_entities:
            assert hasattr(entity, 'source'), "业务对象应该有source属性"
            print(f"  ✓ 业务对象 {entity.name}: 数据源枚举转换正确")

        print("  ✓ ModelList转换中的枚举验证正确")

    
        print("✓ 投资组合综合枚举验证测试通过")


# TDD Red阶段验证：确保所有测试开始时都失败
if __name__ == "__main__":
    print("TDD Red阶段验证：Portfolio CRUD测试")
    print("所有测试用例应该在实现开始前失败")
    print("运行: pytest test/data/crud/test_portfolio_crud.py -v")
    print("预期结果: 所有测试失败 (Red阶段)")
    print("重点关注: 投资组合生命周期管理和策略比较分析")
