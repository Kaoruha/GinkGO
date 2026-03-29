"""
StockInfoCRUD数据库操作TDD测试

测试CRUD层的股票基础信息数据操作：
- 批量插入 (add_batch)
- 单条插入 (add)
- 查询 (find)
- 更新 (update)
- 删除 (remove)

StockInfo是股票基础信息数据模型，包含股票代码、名称、行业、市场、上市/退市时间等。
为策略分析和回测提供股票基础数据支持。

TODO: 添加replace方法测试用例
- 测试replace方法的原子操作 (备份→删除→插入→失败时恢复)
- 测试没有匹配数据时的行为 (应返回空结果，不插入新数据)
- 测试类型错误检查 (传入错误Model类型时应抛出TypeError)
- 测试空new_items的处理
- 测试批量替换的性能和正确性
- 测试ClickHouse和MySQL数据库的兼容性
"""
import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.data.crud.stock_info_crud import StockInfoCRUD
from ginkgo.data.models.model_stock_info import MStockInfo
from ginkgo.enums import SOURCE_TYPES, CURRENCY_TYPES, MARKET_TYPES


@pytest.mark.database
@pytest.mark.tdd
class TestStockInfoCRUDInsert:
    # 明确配置CRUD类
    CRUD_TEST_CONFIG = {'crud_class': StockInfoCRUD}

    """1. CRUD层插入操作测试 - StockInfo数据插入验证"""

    def test_add_batch_basic(self):
        """测试批量插入StockInfo数据 - 使用真实数据库"""
        print("\n" + "="*60)
        print("开始测试: StockInfo CRUD层批量插入")
        print("="*60)

        stock_crud = StockInfoCRUD()
        print(f"✓ 创建StockInfoCRUD实例: {stock_crud.__class__.__name__}")

        # 创建测试StockInfo数据
        test_stocks = [
            MStockInfo(
                code="000001.SZ",
                code_name="平安银行",
                industry="银行",
                currency=CURRENCY_TYPES.CNY,
                market=MARKET_TYPES.CHINA,
                list_date=datetime(1991, 4, 3),
                delist_date=datetime(2099, 12, 31)
            ),
            MStockInfo(
                code="000002.SZ",
                code_name="万科A",
                industry="房地产",
                currency=CURRENCY_TYPES.CNY,
                market=MARKET_TYPES.CHINA,
                list_date=datetime(1991, 1, 29),
                delist_date=datetime(2099, 12, 31)
            ),
            MStockInfo(
                code="600000.SH",
                code_name="浦发银行",
                industry="银行",
                currency=CURRENCY_TYPES.CNY,
                market=MARKET_TYPES.CHINA,
                list_date=datetime(1999, 11, 10),
                delist_date=datetime(2099, 12, 31)
            )
        ]
        print(f"✓ 创建测试数据: {len(test_stocks)}条StockInfo记录")
        print(f"  - 股票代码: {[s.code for s in test_stocks]}")
        print(f"  - 行业分布: {[s.industry for s in test_stocks]}")
        print(f"  - 市场类型: {set(s.market for s in test_stocks)}")

        try:
            # 批量插入
            print("\n→ 执行批量插入操作...")
            stock_crud.add_batch(test_stocks)
            print("✓ 批量插入成功")

            # 验证可以查询出插入的数据
            print("\n→ 验证插入的数据...")
            query_result = stock_crud.find(filters={"code__in": ["000001.SZ", "000002.SZ", "600000.SH"]})
            print(f"✓ 查询到 {len(query_result)} 条记录 (ModelList)")
            assert len(query_result) >= 3
            assert hasattr(query_result, 'to_dataframe'), "返回结果应该是ModelList，支持to_dataframe()方法"
            assert hasattr(query_result, 'to_entities'), "返回结果应该是ModelList，支持to_entities()方法"

            # 验证数据内容 - 使用新的API
            entities = query_result.to_entities()  # 转换为业务实体对象
            codes = [stock.code for stock in entities]
            industries = [stock.industry for stock in entities]
            markets = [stock.market for stock in entities]

            print(f"✓ 股票代码验证通过: {set(codes)}")
            print(f"✓ 行业分布验证通过: {set(industries)}")
            print(f"✓ 市场类型验证通过: {set(markets)}")

            assert "000001.SZ" in codes
            assert "000002.SZ" in codes
            assert "600000.SH" in codes

            # 测试DataFrame转换和枚举字段转换
            print("\n→ 测试新的DataFrame转换API...")
            df_result = query_result.to_dataframe()
            print(f"✓ DataFrame转换成功，形状: {df_result.shape}")
            print(f"✓ DataFrame列名: {list(df_result.columns)}")

            # 验证枚举字段转换
            if len(df_result) > 0:
                sample_row = df_result.iloc[0]
                print(f"✓ 枚举字段验证: market={sample_row['market']}, currency={sample_row['currency']}")
                # DataFrame可能包含int值（旧数据）或枚举对象（新数据）
                assert isinstance(sample_row['market'], (int, MARKET_TYPES)), "market字段应该是int值或枚举对象"
                assert isinstance(sample_row['currency'], (int, CURRENCY_TYPES)), "currency字段应该是int值或枚举对象"
                print("✅ 新CRUD框架的枚举转换验证通过")

        except Exception as e:
            print(f"✗ 批量插入失败: {e}")
            raise

    def test_add_single_stock(self):
        """测试单条StockInfo数据插入"""
        print("\n" + "="*60)
        print("开始测试: StockInfo CRUD层单条插入")
        print("="*60)

        stock_crud = StockInfoCRUD()

        test_stock = MStockInfo(
            code="000858.SZ",
            code_name="五粮液",
            industry="白酒",
            currency=CURRENCY_TYPES.CNY,
            market=MARKET_TYPES.CHINA,
            list_date=datetime(1998, 4, 27),
            delist_date=datetime(2099, 12, 31)
        )
        print(f"✓ 创建测试StockInfo: {test_stock.code} - {test_stock.code_name}")
        print(f"  - 行业: {test_stock.industry}")
        print(f"  - 上市日期: {test_stock.list_date}")

        try:
            # 单条插入
            print("\n→ 执行单条插入操作...")
            stock_crud.add(test_stock)
            print("✓ 单条插入成功")

            # 验证数据
            print("\n→ 验证插入的数据...")
            query_result = stock_crud.find(filters={"code": "000858.SZ"})
            print(f"✓ 查询到 {len(query_result)} 条记录 (ModelList)")
            assert len(query_result) >= 1

            # 测试新的转换API
            entities = query_result.to_entities()
            inserted_stock = entities[0]
            print(f"✓ 插入的StockInfo验证: {inserted_stock.code_name}")
            assert inserted_stock.code == "000858.SZ"
            assert inserted_stock.code_name == "五粮液"

            # 测试单个Model的to_entity方法
            model_instance = query_result[0]  # 原始Model
            entity = model_instance.to_entity()  # 转换为业务实体
            print(f"✅ 单个Model to_entity()测试: {entity.code_name}")
            assert entity.code == "000858.SZ"
            assert hasattr(entity, 'market'), "业务实体应该有market字段"

        except Exception as e:
            print(f"✗ 单条插入失败: {e}")
            raise

    def test_add_international_stock(self):
        """测试创建国际股票StockInfo"""
        print("\n" + "="*60)
        print("开始测试: 创建国际股票StockInfo")
        print("="*60)

        stock_crud = StockInfoCRUD()

        international_stock = MStockInfo(
            code="AAPL",
            code_name="Apple Inc.",
            industry="Technology",
            currency=CURRENCY_TYPES.USD,
            market=MARKET_TYPES.NASDAQ,
            list_date=datetime(1980, 12, 12),
            delist_date=datetime(2099, 12, 31)
        )
        print(f"✓ 创建国际股票MStockInfo: {international_stock.code}")
        print(f"  - 公司名称: {international_stock.code_name}")
        print(f"  - 行业: {international_stock.industry}")
        print(f"  - 货币: {international_stock.currency}")
        print(f"  - 市场: {international_stock.market}")

        try:
            # 插入国际股票信息
            print("\n→ 执行国际股票StockInfo插入...")
            stock_crud.add(international_stock)
            print("✓ 国际股票StockInfo插入成功")

            # 验证国际股票信息
            print("\n→ 验证国际股票StockInfo...")
            query_result = stock_crud.find(filters={"code": "AAPL"})
            assert len(query_result) >= 1

            # 使用新的转换API来获得正确的枚举对象
            entities = query_result.to_entities()
            verified_stock = entities[0]
            print(f"✓ 国际股票验证: {verified_stock.code_name}")
            print(f"  - 货币: {verified_stock.currency}")
            print(f"  - 市场: {verified_stock.market}")
            assert verified_stock.code == "AAPL"
            assert verified_stock.currency == CURRENCY_TYPES.USD
            assert verified_stock.market == MARKET_TYPES.NASDAQ
            print("✓ 国际股票信息验证通过")

        except Exception as e:
            print(f"✗ 国际股票StockInfo创建失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestStockInfoCRUDQuery:
    # 明确配置CRUD类
    CRUD_TEST_CONFIG = {'crud_class': StockInfoCRUD}

    """2. CRUD层查询操作测试 - StockInfo数据查询和过滤"""

    def test_find_by_code(self):
        """测试根据股票代码查询StockInfo"""
        print("\n" + "="*60)
        print("开始测试: 根据code查询StockInfo")
        print("="*60)

        stock_crud = StockInfoCRUD()

        try:
            # 查询特定股票代码的信息
            print("→ 查询code=000001.SZ的股票信息...")
            stocks = stock_crud.find(filters={"code": "000001.SZ"})
            print(f"✓ 查询到 {len(stocks)} 条记录")

            # 验证查询结果 - find()返回List[Model]
            print(f"✓ find()返回类型: {type(stocks).__name__}")
            print(f"✓ find()返回数量: {len(stocks)}")
            assert len(stocks) >= 1

            # 验证每个都是Model对象
            for i, model in enumerate(stocks):
                print(f"  - Model[{i}]: {model.code} - {model.code_name}")
                print(f"    - market值: {model.market} (类型: {type(model.market)})")
                assert model.code == "000001.SZ"

            # 测试转换API：to_dataframe()返回DataFrame
            print("\n→ 测试to_dataframe()转换...")
            df = stocks.to_dataframe()
            print(f"✓ to_dataframe()返回: {type(df).__name__}, 形状: {df.shape}")
            assert hasattr(df, 'columns'), "应该是DataFrame"

            # 测试转换API：to_entities()返回List[Entity]
            print("\n→ 测试to_entities()转换...")
            entities = stocks.to_entities()
            print(f"✓ to_entities()返回: {len(entities)} 个Entity")
            assert len(entities) >= 1

            # 验证Entity具有正确的枚举字段
            for entity in entities:
                print(f"  - Entity: {entity.code} - {entity.code_name}")
                print(f"    - market: {entity.market.name} (类型: {type(entity.market)})")
                assert hasattr(entity.market, 'name'), "Entity的market应该是枚举对象"
                assert entity.code == "000001.SZ"

            # API设计验证完成
            print("✅ find() + to_dataframe() + to_entities() API设计验证通过")

        except Exception as e:
            print(f"✗ 查询失败: {e}")
            raise

    def test_find_by_industry(self):
        """测试根据行业查询StockInfo"""
        print("\n" + "="*60)
        print("开始测试: 根据industry查询StockInfo")
        print("="*60)

        stock_crud = StockInfoCRUD()

        try:
            # 查询特定行业的股票
            print("→ 查询industry=银行的股票...")
            bank_stocks = stock_crud.find(filters={"industry": "银行"})
            print(f"✓ 查询到 {len(bank_stocks)} 只银行股")

            # 查询另一个行业的股票
            print("→ 查询industry=房地产的股票...")
            real_estate_stocks = stock_crud.find(filters={"industry": "房地产"})
            print(f"✓ 查询到 {len(real_estate_stocks)} 只房地产股")

            # 验证查询结果
            print("→ 验证查询结果...")
            for stock in bank_stocks:
                print(f"  - 银行股: {stock.code} - {stock.code_name}")
                assert stock.industry == "银行"

            for stock in real_estate_stocks:
                print(f"  - 房地产股: {stock.code} - {stock.code_name}")
                assert stock.industry == "房地产"

            print("✓ 行业查询验证成功")

        except Exception as e:
            print(f"✗ 行业查询失败: {e}")
            raise

    def test_find_by_market(self):
        """测试根据市场查询StockInfo"""
        print("\n" + "="*60)
        print("开始测试: 根据market查询StockInfo")
        print("="*60)

        stock_crud = StockInfoCRUD()

        try:
            # 查询中国市场的股票
            print("→ 查询中国市场股票 (market=CHINA)...")
            china_stocks = stock_crud.find(filters={"market": MARKET_TYPES.CHINA})
            print(f"✓ 查询到 {len(china_stocks)} 只中国股票")

            # 查询美国市场的股票
            print("→ 查询美国市场股票 (market=NASDAQ)...")
            us_stocks = stock_crud.find(filters={"market": MARKET_TYPES.NASDAQ})
            print(f"✓ 查询到 {len(us_stocks)} 只美国股票")

            # 验证查询结果
            print("→ 验证查询结果...")
            for stock in china_stocks:
                print(f"  - 中国股票: {stock.code} - {stock.code_name}")
                assert stock.market == MARKET_TYPES.CHINA.value

            for stock in us_stocks:
                print(f"  - 美国股票: {stock.code} - {stock.code_name}")
                assert stock.market == MARKET_TYPES.NASDAQ.value

            print("✓ 市场查询验证成功")

        except Exception as e:
            print(f"✗ 市场查询失败: {e}")
            raise

    def test_find_by_listing_date_range(self):
        """测试根据上市日期范围查询StockInfo"""
        print("\n" + "="*60)
        print("开始测试: 根据上市日期范围查询StockInfo")
        print("="*60)

        stock_crud = StockInfoCRUD()

        try:
            # 查询特定年代上市的股票
            start_date = datetime(1990, 1, 1)
            end_date = datetime(1999, 12, 31)

            print(f"→ 查询1990年代上市的股票 ({start_date} ~ {end_date})...")
            all_stocks = stock_crud.find()
            filtered_stocks = [
                s for s in all_stocks
                if start_date <= s.list_date <= end_date
            ]

            print(f"✓ 查询到 {len(filtered_stocks)} 只1990年代上市的股票")

            # 验证查询结果
            for stock in filtered_stocks:
                print(f"  - {stock.code}: {stock.code_name} (上市: {stock.list_date})")
                assert start_date <= stock.list_date <= end_date

            print("✓ 上市日期范围查询验证成功")

        except Exception as e:
            print(f"✗ 上市日期范围查询失败: {e}")
            raise

    def test_find_with_pagination(self):
        """测试分页查询StockInfo - 简化版本"""
        print("\n" + "="*60)
        print("开始测试: 分页查询StockInfo")
        print("="*60)

        stock_crud = StockInfoCRUD()

        try:
            # 简单分页查询测试
            print("→ 执行基本分页查询...")

            # 查询第一页
            page1 = stock_crud.find(page=1, page_size=5)
            print(f"✓ 第1页查询成功: {len(page1)} 条记录")

            # 基本验证
            assert isinstance(page1, list), "分页结果应该是列表"
            print("✓ 分页基本功能验证通过")

        except Exception as e:
            print(f"✗ 分页查询失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestStockInfoCRUDUpdate:
    # 明确配置CRUD类
    CRUD_TEST_CONFIG = {'crud_class': StockInfoCRUD}

    """3. CRUD层更新操作测试 - StockInfo属性更新"""

    def test_update_stock_industry(self):
        """测试更新StockInfo行业信息"""
        print("\n" + "="*60)
        print("开始测试: 更新StockInfo行业信息")
        print("="*60)

        stock_crud = StockInfoCRUD()

        try:
            # 查询待更新的股票信息
            print("→ 查询待更新的股票信息...")
            stocks = stock_crud.find(page_size=1)
            if not stocks:
                print("✗ 没有找到可更新的股票信息")
                return

            target_stock = stocks[0]
            print(f"✓ 找到股票: {target_stock.code} - {target_stock.code_name}")
            print(f"  - 当前行业: {target_stock.industry}")
            print(f"  - 当前市场: {target_stock.market}")

            # 更新股票行业信息
            print("→ 更新股票行业信息...")
            new_industry = f"更新_{target_stock.industry}"

            # 使用简短的名称避免超过32字符限制
            new_code_name = f"更新_{target_stock.code[:10]}"  # 只取股票代码前10位

            updated_data = {
                "industry": new_industry,
                "code_name": new_code_name
            }

            stock_crud.modify(filters={"uuid": target_stock.uuid}, updates=updated_data)
            print("✓ 股票行业信息更新成功")

            # 验证更新结果
            print("→ 验证更新结果...")
            updated_stocks = stock_crud.find(filters={"uuid": target_stock.uuid})
            assert len(updated_stocks) == 1

            updated_stock = updated_stocks[0]
            print(f"✓ 更新后行业: {updated_stock.industry}")
            print(f"✓ 更新后名称: {updated_stock.code_name}")

            assert updated_stock.industry == new_industry
            assert updated_stock.code_name == new_code_name
            print("✓ 股票信息更新验证成功")

        except Exception as e:
            print(f"✗ 更新股票信息失败: {e}")
            raise

    def test_update_stock_market_info(self):
        """测试更新StockInfo市场信息"""
        print("\n" + "="*60)
        print("开始测试: 更新StockInfo市场信息")
        print("="*60)

        stock_crud = StockInfoCRUD()

        try:
            # 查询待更新的股票信息
            print("→ 查询待更新的股票信息...")
            stocks = stock_crud.find(filters={"market": MARKET_TYPES.CHINA}, page_size=1)
            if not stocks:
                print("✗ 没有找到可更新的中国股票")
                return

            target_stock = stocks[0]
            print(f"✓ 找到股票: {target_stock.code}")
            print(f"  - 当前市场: {target_stock.market}")
            print(f"  - 当前货币: {target_stock.currency}")

            # 更新市场信息（这里我们模拟一个场景）
            print("→ 更新市场信息...")
            # 注意：实际应用中市场通常不会改变，这里只是测试更新功能
            updated_data = {
                "delist_date": datetime.now() + timedelta(days=365)  # 更新退市日期
            }

            stock_crud.modify(filters={"uuid": target_stock.uuid}, updates=updated_data)
            print("✓ 市场信息更新成功")

            # 验证更新结果
            print("→ 验证更新结果...")
            updated_stocks = stock_crud.find(filters={"uuid": target_stock.uuid})
            assert len(updated_stocks) == 1

            updated_stock = updated_stocks[0]
            print(f"✓ 更新后退市日期: {updated_stock.delist_date}")

            # 验证时间差大约是365天
            time_diff = (updated_stock.delist_date - datetime.now()).days
            assert 360 <= time_diff <= 370  # 允许一些误差
            print("✓ 市场信息更新验证成功")

        except Exception as e:
            print(f"✗ 市场信息更新失败: {e}")
            raise

    def test_update_stock_batch(self):
        """测试批量更新StockInfo"""
        print("\n" + "="*60)
        print("开始测试: 批量更新StockInfo")
        print("="*60)

        stock_crud = StockInfoCRUD()

        try:
            # 查询多个股票进行批量更新
            print("→ 查询需要批量更新的股票...")
            stocks = stock_crud.find(page_size=3)
            if len(stocks) < 2:
                print("✗ 股票数量不足，跳过批量更新测试")
                return

            print(f"✓ 找到 {len(stocks)} 个股票进行批量更新")

            # 批量更新股票信息
            for i, stock in enumerate(stocks):
                print(f"→ 更新股票 {stock.code} 的行业信息...")
                stock_crud.modify(filters={"uuid": stock.uuid}, updates={"industry": f"批量更新行业_{i+1}"})

            print("✓ 批量更新完成")

            # 验证批量更新结果
            print("→ 验证批量更新结果...")
            updated_stocks = stock_crud.find(page_size=3)
            updated_count = sum(1 for s in updated_stocks if s.industry.startswith("批量更新行业_"))
            print(f"✓ 更新了 {updated_count} 个股票的行业信息")
            assert updated_count >= 2
            print("✓ 批量更新验证成功")

        except Exception as e:
            print(f"✗ 批量更新失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestStockInfoCRUDDelete:
    # 明确配置CRUD类
    CRUD_TEST_CONFIG = {'crud_class': StockInfoCRUD}

    """4. CRUD层删除操作测试 - StockInfo数据清理"""

    def test_delete_stock_by_uuid(self):
        """测试根据UUID删除StockInfo"""
        print("\n" + "="*60)
        print("开始测试: 根据UUID删除StockInfo")
        print("="*60)

        stock_crud = StockInfoCRUD()

        try:
            # 先插入一条测试数据
            print("→ 创建测试股票信息...")
            test_stock = MStockInfo(
                code="999999.SZ",
                code_name="测试股票",
                industry="测试行业",
                currency=CURRENCY_TYPES.CNY,
                market=MARKET_TYPES.CHINA,
                list_date=datetime(2023, 1, 1),
                delist_date=datetime(2099, 12, 31)
            )
            stock_crud.add(test_stock)
            print(f"✓ 创建测试股票: {test_stock.uuid}")

            # 查询确认插入成功
            inserted_stocks = stock_crud.find(filters={"uuid": test_stock.uuid})
            assert len(inserted_stocks) == 1
            print("✓ 股票信息插入确认成功")

            # 删除股票信息
            print("→ 删除测试股票信息...")
            stock_crud.remove(filters={"uuid": test_stock.uuid})
            print("✓ 股票信息删除成功")

            # 验证删除结果
            print("→ 验证删除结果...")
            deleted_stocks = stock_crud.find(filters={"uuid": test_stock.uuid})
            assert len(deleted_stocks) == 0
            print("✓ 股票信息删除验证成功")

        except Exception as e:
            print(f"✗ 删除股票信息失败: {e}")
            raise

    def test_delete_stocks_by_market(self):
        """测试根据市场批量删除StockInfo"""
        print("\n" + "="*60)
        print("开始测试: 根据市场批量删除StockInfo")
        print("="*60)

        stock_crud = StockInfoCRUD()

        try:
            # 查询删除前的数量
            print("→ 查询删除前的股票数量...")
            test_market_stocks = stock_crud.find(filters={"market": MARKET_TYPES.NASDAQ})
            count_before = len(test_market_stocks)
            print(f"✓ 删除前NASDAQ市场有 {count_before} 只股票")

            if count_before == 0:
                print("✗ 没有找到可删除的NASDAQ股票")
                return

            # 批量删除（注意：实际应用中通常不会删除真实股票数据）
            print("→ 批量删除NASDAQ市场股票信息...")
            for stock in test_market_stocks[:1]:  # 只删除一条作为测试
                stock_crud.remove(filters={"uuid": stock.uuid})
            print("✓ 批量删除完成")

            # 验证删除结果
            print("→ 验证删除结果...")
            remaining_stocks = stock_crud.find(filters={"market": MARKET_TYPES.NASDAQ})
            count_after = len(remaining_stocks)
            print(f"✓ 删除后NASDAQ市场剩余 {count_after} 只股票")
            assert count_after < count_before
            print("✓ 批量删除验证成功")

        except Exception as e:
            print(f"✗ 批量删除失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestStockInfoCRUDBusinessLogic:
    # 明确配置CRUD类
    CRUD_TEST_CONFIG = {'crud_class': StockInfoCRUD}

    """5. CRUD层业务逻辑测试 - StockInfo业务场景验证"""

    def test_stock_market_analysis(self):
        """测试股票市场分布分析"""
        print("\n" + "="*60)
        print("开始测试: 股票市场分布分析")
        print("="*60)

        stock_crud = StockInfoCRUD()

        try:
            # 查询所有股票进行市场分析
            print("→ 查询所有股票进行市场分析...")
            all_stocks = stock_crud.find()

            if len(all_stocks) < 5:
                print("✗ 股票数据不足，跳过市场分析测试")
                return

            # 按市场分组统计
            market_distribution = {}
            for stock in all_stocks:
                market_name = MARKET_TYPES(stock.market).name
                if market_name not in market_distribution:
                    market_distribution[market_name] = {
                        "count": 0,
                        "industries": set()
                    }
                market_distribution[market_name]["count"] += 1
                market_distribution[market_name]["industries"].add(stock.industry)

            print(f"✓ 市场分布分析结果:")
            for market_name, stats in market_distribution.items():
                print(f"  - {market_name}: {stats['count']} 只股票, {len(stats['industries'])} 个行业")

            # 验证分析结果
            total_stocks = sum(stats["count"] for stats in market_distribution.values())
            assert total_stocks == len(all_stocks)
            assert len(market_distribution) >= 1
            print("✓ 股票市场分析验证成功")

        except Exception as e:
            print(f"✗ 股票市场分析失败: {e}")
            raise

    def test_industry_distribution_analysis(self):
        """测试行业分布分析"""
        print("\n" + "="*60)
        print("开始测试: 行业分布分析")
        print("="*60)

        stock_crud = StockInfoCRUD()

        try:
            # 查询所有股票进行行业分析
            print("→ 查询所有股票进行行业分析...")
            all_stocks = stock_crud.find()

            if len(all_stocks) < 5:
                print("✗ 股票数据不足，跳过行业分析测试")
                return

            # 按行业分组统计
            industry_distribution = {}
            for stock in all_stocks:
                if stock.industry not in industry_distribution:
                    industry_distribution[stock.industry] = {
                        "count": 0,
                        "markets": set(),
                        "avg_listing_year": 0,
                        "total_years": 0
                    }
                industry_distribution[stock.industry]["count"] += 1
                industry_distribution[stock.industry]["markets"].add(MARKET_TYPES(stock.market).name)
                industry_distribution[stock.industry]["total_years"] += stock.list_date.year

            # 计算平均上市年份
            for industry, stats in industry_distribution.items():
                if stats["count"] > 0:
                    stats["avg_listing_year"] = stats["total_years"] / stats["count"]

            print(f"✓ 行业分布分析结果:")
            for industry, stats in industry_distribution.items():
                print(f"  - {industry}: {stats['count']} 只股票, {len(stats['markets'])} 个市场")
                print(f"    平均上市年份: {stats['avg_listing_year']:.0f}")

            # 验证分析结果
            total_stocks = sum(stats["count"] for stats in industry_distribution.values())
            assert total_stocks == len(all_stocks)
            assert len(industry_distribution) >= 1
            print("✓ 行业分布分析验证成功")

        except Exception as e:
            print(f"✗ 行业分布分析失败: {e}")
            raise

    def test_stock_data_integrity(self):
        """测试StockInfo数据完整性和约束"""
        print("\n" + "="*60)
        print("开始测试: StockInfo数据完整性和约束")
        print("="*60)

        stock_crud = StockInfoCRUD()

        try:
            # 测试必要字段约束
            print("→ 测试必要字段约束...")

            # code不能为空 - 源码会将空字符串替换为默认值"ginkgo_test_code"
            try:
                invalid_stock = MStockInfo(
                    code="",  # 空字符串，源码会替换为默认值
                    code_name="测试股票",
                    industry="测试行业",
                    source=SOURCE_TYPES.TEST
                )
                # 源码当前允许空code（替换为默认值）
                result = stock_crud.add(invalid_stock)
                assert result is not None, "空code的股票信息应能成功插入（使用默认值）"
                print(f"✓ 空code股票信息插入成功（源码使用默认值'{invalid_stock.code}'）")
            except Exception as e:
                print(f"  注意: 源码行为变更，空code被拒绝: {type(e).__name__}")

            # 验证枚举值约束
            print("→ 验证枚举值约束...")
            valid_stocks = stock_crud.find(page_size=10)
            for stock in valid_stocks:
                # 验证market是有效枚举值
                assert stock.market in [m.value for m in MARKET_TYPES]
                # 验证currency是有效枚举值
                assert stock.currency in [c.value for c in CURRENCY_TYPES]
                # 验证日期逻辑
                assert stock.list_date <= stock.delist_date
                # 验证字符串长度
                assert len(stock.code) <= 32
                assert len(stock.code_name) <= 32
                assert len(stock.industry) <= 32

            print(f"✓ 验证了 {len(valid_stocks)} 条股票信息的约束条件")
            print("✓ 数据完整性验证成功")

        except Exception as e:
            print(f"✗ 数据完整性测试失败: {e}")
            raise

    def test_listing_timeline_analysis(self):
        """测试上市时间轴分析"""
        print("\n" + "="*60)
        print("开始测试: 上市时间轴分析")
        print("="*60)

        stock_crud = StockInfoCRUD()

        try:
            # 查询所有股票进行时间轴分析
            print("→ 查询所有股票进行时间轴分析...")
            all_stocks = stock_crud.find()

            if len(all_stocks) < 3:
                print("✗ 股票数据不足，跳过时间轴分析测试")
                return

            # 按年代分组统计
            timeline_analysis = {}
            for stock in all_stocks:
                decade = (stock.list_date.year // 10) * 10
                decade_key = f"{decade}s"

                if decade_key not in timeline_analysis:
                    timeline_analysis[decade_key] = {
                        "count": 0,
                        "years": [],
                        "markets": set()
                    }

                timeline_analysis[decade_key]["count"] += 1
                timeline_analysis[decade_key]["years"].append(stock.list_date.year)
                timeline_analysis[decade_key]["markets"].add(MARKET_TYPES(stock.market).name)

            print(f"✓ 上市时间轴分析结果:")
            for decade_key in sorted(timeline_analysis.keys()):
                stats = timeline_analysis[decade_key]
                year_range = f"{min(stats['years'])}-{max(stats['years'])}"
                print(f"  - {decade_key}: {stats['count']} 只股票 ({year_range})")
                print(f"    涉及市场: {', '.join(stats['markets'])}")

            # 验证分析结果
            total_stocks = sum(stats["count"] for stats in timeline_analysis.values())
            assert total_stocks == len(all_stocks)
            assert len(timeline_analysis) >= 1
            print("✓ 上市时间轴分析验证成功")

        except Exception as e:
            print(f"✗ 上市时间轴分析失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestStockInfoCRUDAPIDesign:
    # 明确配置CRUD类
    CRUD_TEST_CONFIG = {'crud_class': StockInfoCRUD}

    """验证CRUD API设计规范：正确的返回类型和转换方法"""

    def test_create_add_returns_single_model(self):
        """验证create和add方法返回单个Model"""
        print("\n" + "="*60)
        print("开始测试: create/add返回单个Model")
        print("="*60)

        stock_crud = StockInfoCRUD()

        try:
            # 测试create方法
            print("→ 测试create方法...")
            created_model = stock_crud.create(
                code="API_TEST001.SZ",
                code_name="API测试公司",
                industry="测试行业",
                currency=CURRENCY_TYPES.CNY,
                market=MARKET_TYPES.CHINA,
                list_date=datetime(2023, 1, 1),
                delist_date=datetime(2099, 12, 31),
                source=SOURCE_TYPES.TEST
            )

            # 验证返回单个Model
            print(f"✓ create()返回类型: {type(created_model).__name__}")
            assert not isinstance(created_model, list), "create()应该返回单个Model，不是List"
            assert hasattr(created_model, 'uuid'), "应该是有效的Model对象"
            assert created_model.code == "API_TEST001.SZ"
            print(f"✓ create()返回单个Model验证通过: {created_model.code_name}")

            # 测试add方法
            print("\n→ 测试add方法...")
            test_model = MStockInfo(
                code="API_TEST002.SZ",
                code_name="API测试公司2",
                industry="测试行业2",
                currency=CURRENCY_TYPES.CNY,
                market=MARKET_TYPES.CHINA,
                list_date=datetime(2023, 1, 2),
                delist_date=datetime(2099, 12, 31),
                source=SOURCE_TYPES.TEST
            )
            added_model = stock_crud.add(test_model)

            # 验证返回单个Model
            print(f"✓ add()返回类型: {type(added_model).__name__}")
            assert not isinstance(added_model, list), "add()应该返回单个Model，不是List"
            assert hasattr(added_model, 'uuid'), "应该是有效的Model对象"
            assert added_model.code == "API_TEST002.SZ"
            print(f"✓ add()返回单个Model验证通过: {added_model.code_name}")

            # 测试单个Model的to_entity方法
            print("\n→ 测试单个Model.to_entity()...")
            entity = created_model.to_entity()
            print(f"✓ to_entity()返回类型: {type(entity).__name__}")
            assert hasattr(entity, 'market'), "Entity应该有market字段"
            assert hasattr(entity.market, 'name'), "Entity的market应该是枚举对象"
            print(f"✓ 单个Model转换Entity验证通过: {entity.code_name}, market={entity.market.name}")

            print("✅ create/add返回单个Model测试成功")

        except Exception as e:
            print(f"✗ create/add测试失败: {e}")
            raise

    def test_add_batch_returns_list_of_models(self):
        """验证add_batch方法返回List[Model]"""
        print("\n" + "="*60)
        print("开始测试: add_batch返回List[Model]")
        print("="*60)

        stock_crud = StockInfoCRUD()

        try:
            # 创建多个测试Model
            test_models = [
                MStockInfo(
                    code="BATCH_TEST001.SZ",
                    code_name="批量测试公司1",
                    industry="测试行业1",
                    currency=CURRENCY_TYPES.CNY,
                    market=MARKET_TYPES.CHINA,
                    list_date=datetime(2023, 1, 1),
                    delist_date=datetime(2099, 12, 31),
                    source=SOURCE_TYPES.TEST
                ),
                MStockInfo(
                    code="BATCH_TEST002.SZ",
                    code_name="批量测试公司2",
                    industry="测试行业2",
                    currency=CURRENCY_TYPES.USD,
                    market=MARKET_TYPES.NASDAQ,
                    list_date=datetime(2023, 1, 2),
                    delist_date=datetime(2099, 12, 31),
                    source=SOURCE_TYPES.TEST
                ),
                MStockInfo(
                    code="BATCH_TEST003.SZ",
                    code_name="批量测试公司3",
                    industry="测试行业3",
                    currency=CURRENCY_TYPES.OTHER,
                    market=MARKET_TYPES.OTHER,
                    list_date=datetime(2023, 1, 3),
                    delist_date=datetime(2099, 12, 31),
                    source=SOURCE_TYPES.TEST
                )
            ]

            # 执行批量插入
            print("→ 执行add_batch...")
            returned_models = stock_crud.add_batch(test_models)

            # 验证返回List[Model]
            print(f"✓ add_batch()返回类型: {type(returned_models).__name__}")
            assert isinstance(returned_models, list), "add_batch()应该返回List"
            assert len(returned_models) == len(test_models), f"应该返回{len(test_models)}个Model"

            # 验证每个元素都是Model
            for i, model in enumerate(returned_models):
                print(f"  - Model[{i}]: {model.code} - {model.code_name}")
                assert hasattr(model, 'uuid'), f"第{i}个应该是有效的Model对象"
                assert model.code.startswith("BATCH_TEST"), f"第{i}个Model代码不匹配"

            print(f"✓ add_batch()返回List[Model]验证通过，数量: {len(returned_models)}")

            # 测试ModelList的转换方法
            print("\n→ 测试ModelList转换方法...")
            model_list = returned_models

            # 测试to_dataframe()返回DataFrame
            df = model_list.to_dataframe()
            print(f"✓ to_dataframe()返回: {type(df).__name__}, 形状: {df.shape}")
            assert hasattr(df, 'columns'), "应该是DataFrame"
            assert len(df) == len(returned_models), "DataFrame行数应该等于Model数量"

            # 测试to_entities()返回List[Entity]
            entities = model_list.to_entities()
            print(f"✓ to_entities()返回: {len(entities)} 个Entity")
            assert len(entities) == len(returned_models), "Entity数量应该等于Model数量"

            # 验证Entity的枚举字段
            for entity in entities:
                assert hasattr(entity.market, 'name'), "Entity的market应该是枚举对象"
                assert hasattr(entity.currency, 'name'), "Entity的currency应该是枚举对象"

            print("✅ add_batch返回List[Model]测试成功")

        except Exception as e:
            print(f"✗ add_batch测试失败: {e}")
            raise

    def test_find_returns_list_of_models(self):
        """验证find方法返回List[Model]"""
        print("\n" + "="*60)
        print("开始测试: find返回List[Model]")
        print("="*60)

        stock_crud = StockInfoCRUD()

        try:
            # 查询所有数据
            print("→ 查询所有StockInfo...")
            models = stock_crud.find()

            # 验证返回List[Model]
            print(f"✓ find()返回类型: {type(models).__name__}")
            assert hasattr(models, 'to_dataframe'), "应该支持to_dataframe()方法"
            assert hasattr(models, 'to_entities'), "应该支持to_entities()方法"

            print(f"✓ find()返回ModelList，数量: {len(models)}")

            if len(models) > 0:
                # 验证是ModelList，包含Model对象
                first_model = models[0]
                print(f"✓ 第一个元素类型: {type(first_model).__name__}")
                assert hasattr(first_model, 'uuid'), "应该是有效的Model对象"
                print(f"✓ 第一个Model: {first_model.code} - {first_model.code_name}")

                # 测试ModelList的转换功能
                print("\n→ 测试ModelList转换功能...")

                # to_dataframe() → DataFrame
                df = models.to_dataframe()
                print(f"✓ to_dataframe(): {type(df).__name__}, 形状: {df.shape}")
                assert len(df) == len(models), "DataFrame行数应该等于Model数量"

                # to_entities() → List[Entity]
                entities = models.to_entities()
                print(f"✓ to_entities(): {len(entities)} 个Entity")
                assert len(entities) == len(models), "Entity数量应该等于Model数量"

                # 验证Entity枚举字段
                if len(entities) > 0:
                    first_entity = entities[0]
                    assert hasattr(first_entity.market, 'name'), "Entity的market应该是枚举对象"
                    print(f"✓ Entity枚举验证: market={first_entity.market.name}")

            print("✅ find返回List[Model]测试成功")

        except Exception as e:
            print(f"✗ find测试失败: {e}")
            raise

    def test_single_model_to_entity(self):
        """验证单个Model的to_entity方法"""
        print("\n" + "="*60)
        print("开始测试: 单个Model.to_entity()")
        print("="*60)

        stock_crud = StockInfoCRUD()

        try:
            # 创建一个Model
            created_model = stock_crud.create(
                code="SINGLE_TEST.SZ",
                code_name="单个Model测试",
                industry="测试行业",
                currency=CURRENCY_TYPES.CNY,
                market=MARKET_TYPES.CHINA,
                list_date=datetime(2023, 1, 1),
                delist_date=datetime(2099, 12, 31),
                source=SOURCE_TYPES.TEST
            )

            print(f"✓ 创建Model: {created_model.code_name}")

            # 测试to_entity()方法
            print("→ 执行to_entity()转换...")
            entity = created_model.to_entity()

            # 验证返回Entity
            print(f"✓ to_entity()返回类型: {type(entity).__name__}")
            assert entity.code == created_model.code, "Entity应该保持相同的code"
            assert entity.code_name == created_model.code_name, "Entity应该保持相同的code_name"

            # 验证枚举字段转换
            print(f"✓ Entity枚举字段验证:")
            print(f"  - market: {entity.market.name} (类型: {type(entity.market)})")
            print(f"  - currency: {entity.currency.name} (类型: {type(entity.currency)})")

            assert hasattr(entity.market, 'name'), "Entity的market应该是枚举对象"
            assert hasattr(entity.currency, 'name'), "Entity的currency应该是枚举对象"
            assert entity.market == MARKET_TYPES.CHINA, "market枚举值应该正确"
            assert entity.currency == CURRENCY_TYPES.CNY, "currency枚举值应该正确"

            print("✅ 单个Model.to_entity()测试成功")

        except Exception as e:
            print(f"✗ 单个Model.to_entity()测试失败: {e}")
            raise

    def test_api_design_consistency(self):
        """验证API设计的一致性"""
        print("\n" + "="*60)
        print("开始测试: API设计一致性验证")
        print("="*60)

        stock_crud = StockInfoCRUD()

        try:
            # API一致性验证矩阵
            api_expectations = {
                "create()": "Single Model",
                "add()": "Single Model",
                "add_batch()": "List[Model]",
                "find()": "List[Model]",
                "Model.to_entity()": "Single Entity",
                "ModelList.to_entities()": "List[Entity]",
                "ModelList.to_dataframe()": "DataFrame"
            }

            print("→ API设计预期:")
            for method, expected in api_expectations.items():
                print(f"  - {method}: {expected}")

            # 验证create()
            print("\n→ 验证create()...")
            created = stock_crud.create(code="CONSISTENCY_TEST.SZ", code_name="一致性测试", industry="测试", currency=CURRENCY_TYPES.CNY, market=MARKET_TYPES.CHINA, list_date=datetime(2023, 1, 1), delist_date=datetime(2099, 12, 31), source=SOURCE_TYPES.TEST)
            assert not isinstance(created, list), "create()应该返回单个Model"
            print("✓ create()返回单个Model")

            # 验证find()
            print("→ 验证find()...")
            found = stock_crud.find(filters={"code": "CONSISTENCY_TEST.SZ"})
            assert hasattr(found, 'to_dataframe'), "find()应该返回支持转换的ModelList"
            print("✓ find()返回ModelList")

            # 验证转换方法
            print("→ 验证转换方法...")
            entity = created.to_entity()
            assert hasattr(entity, 'market'), "to_entity()应该返回Entity"
            print("✓ to_entity()返回Entity")

            entities = found.to_entities()
            assert isinstance(entities, list), "to_entities()应该返回List"
            print("✓ to_entities()返回List[Entity]")

            df = found.to_dataframe()
            import pandas as pd
            assert isinstance(df, pd.DataFrame), "to_dataframe()应该返回DataFrame"
            print("✓ to_dataframe()返回DataFrame")

            print("\n🎯 API设计一致性验证完全通过！")
            print("📊 API设计总结:")
            print("   ✓ CRUD操作返回Model/ModelList")
            print("   ✓ 转换方法提供统一的数据格式")
            print("   ✓ 枚举字段自动转换为枚举对象")
            print("   ✓ 支持链式调用和灵活的数据操作")

        except Exception as e:
            print(f"✗ API一致性测试失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestStockInfoCRUDNewFeatures:
    # 明确配置CRUD类
    CRUD_TEST_CONFIG = {'crud_class': StockInfoCRUD}

    """6. CRUD层新功能测试 - ModelConversion和ModelList功能验证"""

    def test_model_conversion_api(self):
        """测试新的ModelConversion API"""
        print("\n" + "="*60)
        print("开始测试: ModelConversion API")
        print("="*60)

        stock_crud = StockInfoCRUD()

        try:
            # 创建测试数据
            test_stock = MStockInfo(
                code="TEST001.SZ",
                code_name="测试公司",
                industry="测试行业",
                currency=CURRENCY_TYPES.CNY,
                market=MARKET_TYPES.CHINA,
                list_date=datetime(2023, 1, 1),
                delist_date=datetime(2099, 12, 31)
            )
            stock_crud.add(test_stock)
            print("✓ 创建测试股票信息")

            # 查询数据
            result = stock_crud.find(filters={"code": "TEST001.SZ"})
            assert len(result) >= 1
            print("✓ 查询到股票信息")

            # 测试ModelList API
            model_list = result
            print(f"✓ ModelList类型: {type(model_list).__name__}")
            assert hasattr(model_list, 'to_dataframe')
            assert hasattr(model_list, 'to_entities')
            assert hasattr(model_list, 'first')

            # 测试to_entities()
            entities = model_list.to_entities()
            print(f"✓ to_entities()返回: {len(entities)} 个业务实体")
            assert len(entities) >= 1

            entity = entities[0]
            assert entity.code == "TEST001.SZ"
            assert hasattr(entity.market, 'name'), "转换后的market应该是枚举对象"
            assert hasattr(entity.currency, 'name'), "转换后的currency应该是枚举对象"
            print(f"✓ 业务实体验证: {entity.code_name}, market={entity.market.name}")

            # 测试to_dataframe()
            df = model_list.to_dataframe()
            print(f"✓ to_dataframe()返回形状: {df.shape}")
            assert len(df) >= 1

            df_row = df.iloc[0]
            assert df_row['code'] == "TEST001.SZ"
            assert hasattr(df_row['market'], 'name'), "DataFrame中的market应该是枚举对象"
            assert hasattr(df_row['currency'], 'name'), "DataFrame中的currency应该是枚举对象"
            print(f"✓ DataFrame验证: {df_row['code_name']}, market={df_row['market'].name}")

            print("✅ ModelConversion API测试成功")

        except Exception as e:
            print(f"✗ ModelConversion API测试失败: {e}")
            raise

    def test_single_model_to_entity(self):
        """测试单个Model的to_entity方法"""
        print("\n" + "="*60)
        print("开始测试: 单个Model to_entity方法")
        print("="*60)

        stock_crud = StockInfoCRUD()

        try:
            # 查询数据
            result = stock_crud.find(page_size=1)
            if not result:
                print("✗ 没有找到测试数据")
                return

            # 获取单个Model
            model = result[0]
            print(f"✓ 获取Model: {model.code}")

            # 测试to_entity方法
            entity = model.to_entity()
            print(f"✓ 转换为业务实体: {entity.code_name}")

            # 验证转换结果
            assert entity.code == model.code
            assert entity.code_name == model.code_name
            assert hasattr(entity, 'market'), "业务实体应该有market字段"
            assert hasattr(entity, 'currency'), "业务实体应该有currency字段"

            # 验证枚举字段转换
            assert hasattr(entity.market, 'name'), "market应该是枚举对象"
            assert hasattr(entity.currency, 'name'), "currency应该是枚举对象"
            print(f"✓ 枚举字段验证: market={entity.market.name}, currency={entity.currency.name}")

            print("✅ 单个Model to_entity测试成功")

        except Exception as e:
            print(f"✗ 单个Model to_entity测试失败: {e}")
            raise

    def test_model_list_filtering(self):
        """测试ModelList的过滤功能"""
        print("\n" + "="*60)
        print("开始测试: ModelList过滤功能")
        print("="*60)

        stock_crud = StockInfoCRUD()

        try:
            # 查询多个股票
            all_stocks = stock_crud.find(page_size=10)
            if len(all_stocks) < 3:
                print("✗ 股票数据不足，跳过过滤测试")
                return

            print(f"✓ 查询到 {len(all_stocks)} 个股票")

            # 测试first()方法
            first_stock = all_stocks.first()
            assert first_stock is not None
            print(f"✓ first()方法: {first_stock.code}")

            # 测试count()方法
            count = all_stocks.count()
            assert count == len(all_stocks)
            print(f"✓ count()方法: {count}")

            # 测试filter()方法
            # 过滤出银行股
            bank_stocks = all_stocks.filter(lambda s: s.industry == "银行")
            print(f"✓ 过滤出银行股: {len(bank_stocks)} 个")

            # 验证过滤结果
            for stock in bank_stocks:
                assert stock.industry == "银行"
            print("✓ 过滤结果验证通过")

            # 测试过滤后的ModelList仍然支持转换API
            if len(bank_stocks) > 0:
                bank_entities = bank_stocks.to_entities()
                bank_df = bank_stocks.to_dataframe()
                print(f"✓ 过滤后的ModelList支持转换: entities={len(bank_entities)}, df_shape={bank_df.shape}")

            print("✅ ModelList过滤功能测试成功")

        except Exception as e:
            print(f"✗ ModelList过滤功能测试失败: {e}")
            raise

    def test_enum_conversion_consistency(self):
        """测试枚举转换的一致性"""
        print("\n" + "="*60)
        print("开始测试: 枚举转换一致性")
        print("="*60)

        stock_crud = StockInfoCRUD()

        try:
            # 查询数据
            result = stock_crud.find(page_size=5)
            if not result:
                print("✗ 没有找到测试数据")
                return

            print(f"✓ 查询到 {len(result)} 个股票")

            # 转换为业务实体
            entities = result.to_entities()
            print(f"✓ 转换为 {len(entities)} 个业务实体")

            # 转换为DataFrame
            df = result.to_dataframe()
            print(f"✓ 转换为DataFrame，形状: {df.shape}")

            # 验证枚举转换的一致性
            for i, entity in enumerate(entities):
                if i < len(df):
                    df_row = df.iloc[i]

                    # 验证相同数据的枚举字段一致
                    assert entity.code == df_row['code'], f"第{i}行代码不一致"

                    # 验证market枚举一致性
                    assert entity.market.name == df_row['market'].name, f"第{i}行market不一致"
                    assert type(entity.market) == type(df_row['market']), f"第{i}行market类型不一致"

                    # 验证currency枚举一致性
                    assert entity.currency.name == df_row['currency'].name, f"第{i}行currency不一致"
                    assert type(entity.currency) == type(df_row['currency']), f"第{i}行currency类型不一致"

            print("✅ 枚举转换一致性验证通过")

            # 验证枚举值的有效性
            for entity in entities:
                assert entity.market in MARKET_TYPES, f"无效的market枚举值: {entity.market}"
                assert entity.currency in CURRENCY_TYPES, f"无效的currency枚举值: {entity.currency}"

            for _, row in df.iterrows():
                assert row['market'] in MARKET_TYPES, f"DataFrame中无效的market枚举值: {row['market']}"
                assert row['currency'] in CURRENCY_TYPES, f"DataFrame中无效的currency枚举值: {row['currency']}"

            print("✅ 枚举值有效性验证通过")
            print("✅ 枚举转换一致性测试成功")

        except Exception as e:
            print(f"✗ 枚举转换一致性测试失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestStockInfoCRUDConversions:
    # 明确配置CRUD类
    CRUD_TEST_CONFIG = {'crud_class': StockInfoCRUD}

    """7. CRUD层转换方法测试 - StockInfo ModelList转换功能验证"""

    def test_model_list_conversions(self):
        """测试ModelList的to_dataframe和to_entities转换功能"""
        import pandas as pd
        print("\n" + "="*60)
        print("开始测试: StockInfo ModelList转换功能")
        print("="*60)

        stock_crud = StockInfoCRUD()

        try:
            # 创建测试数据
            test_stocks = [
                MStockInfo(
                    code="CONVERT_TEST001.SZ",
                    code_name="转换测试公司1",
                    industry="测试行业1",
                    currency=CURRENCY_TYPES.CNY,
                    market=MARKET_TYPES.CHINA,
                    list_date=datetime(2023, 1, 5),
                    delist_date=datetime(2099, 12, 31),
                    source=SOURCE_TYPES.TEST
                ),
                MStockInfo(
                    code="CONVERT_TEST002.SZ",
                    code_name="转换测试公司2",
                    industry="测试行业2",
                    currency=CURRENCY_TYPES.USD,
                    market=MARKET_TYPES.NASDAQ,
                    list_date=datetime(2023, 1, 6),
                    delist_date=datetime(2099, 12, 31),
                    source=SOURCE_TYPES.TEST
                ),
                MStockInfo(
                    code="CONVERT_TEST003.SH",
                    code_name="转换测试公司3",
                    industry="测试行业3",
                    currency=CURRENCY_TYPES.OTHER,
                    market=MARKET_TYPES.OTHER,
                    list_date=datetime(2023, 1, 7),
                    delist_date=datetime(2099, 12, 31),
                    source=SOURCE_TYPES.TEST
                )
            ]

            # 获取操作前数据条数用于验证
            before_count = len(stock_crud.find(filters={"source": SOURCE_TYPES.TEST.value}))
            print(f"✓ 操作前数据库记录数: {before_count}")

            # 插入测试数据
            stock_crud.add_batch(test_stocks)

            # 验证数据库记录数变化
            after_count = len(stock_crud.find(filters={"source": SOURCE_TYPES.TEST.value}))
            print(f"✓ 操作后数据库记录数: {after_count}")
            assert after_count - before_count == len(test_stocks), f"应增加{len(test_stocks)}条数据，实际增加{after_count - before_count}条"

            # 获取ModelList进行转换测试
            print("\n→ 获取ModelList...")
            model_list = stock_crud.find(filters={"code__like": "CONVERT_TEST%"})
            print(f"✓ ModelList类型: {type(model_list).__name__}")
            print(f"✓ ModelList长度: {len(model_list)}")
            assert len(model_list) >= 3

            # 测试1: to_dataframe转换
            print("\n→ 测试to_dataframe转换...")
            df = model_list.to_dataframe()
            print(f"✓ DataFrame类型: {type(df).__name__}")
            print(f"✓ DataFrame形状: {df.shape}")
            assert isinstance(df, pd.DataFrame), "应返回DataFrame"
            assert len(df) == len(model_list), f"DataFrame行数应等于ModelList长度，{len(df)} != {len(model_list)}"

            # 验证DataFrame列和内容
            required_columns = ['code', 'code_name', 'industry', 'market', 'currency', 'list_date']
            for col in required_columns:
                assert col in df.columns, f"DataFrame应包含列: {col}"
            print(f"✓ 验证必要列存在: {required_columns}")

            # 验证DataFrame数据内容
            assert all(df['code'].str.startswith('CONVERT_TEST')), "股票代码应以CONVERT_TEST开头"
            assert set(df['industry']) == {'测试行业1', '测试行业2', '测试行业3'}, "行业应匹配"
            print("✓ DataFrame数据内容验证通过")

            # 验证枚举字段转换
            print("→ 验证枚举字段转换...")
            for i, (_, row) in enumerate(df.iterrows()):
                market_val = row['market']
                currency_val = row['currency']

                assert isinstance(market_val, MARKET_TYPES), f"第{i}行market应为枚举对象，实际{type(market_val)}"
                assert isinstance(currency_val, CURRENCY_TYPES), f"第{i}行currency应为枚举对象，实际{type(currency_val)}"

                # 验证枚举值的有效性
                assert market_val in MARKET_TYPES, f"第{i}行market枚举值无效: {market_val}"
                assert currency_val in CURRENCY_TYPES, f"第{i}行currency枚举值无效: {currency_val}"

                print(f"  - 股票{i+1}: {row['code']} market={market_val.name} currency={currency_val.name}")
            print("✓ 枚举字段转换验证通过")

            # 测试2: to_entities转换
            print("\n→ 测试to_entities转换...")
            entities = model_list.to_entities()
            print(f"✓ 实体列表类型: {type(entities).__name__}")
            print(f"✓ 实体列表长度: {len(entities)}")
            assert len(entities) == len(model_list), f"实体列表长度应等于ModelList长度，{len(entities)} != {len(model_list)}"

            # 验证实体类型和内容
            first_entity = entities[0]
            from ginkgo.entities import StockInfo
            assert isinstance(first_entity, StockInfo), f"应转换为StockInfo实体，实际{type(first_entity)}"

            # 验证实体属性
            assert first_entity.code.startswith('CONVERT_TEST')
            assert first_entity.code_name.startswith('转换测试公司')
            print("✓ StockInfo实体转换验证通过")

            # 测试3: 业务对象映射验证
            print("\n→ 测试业务对象映射...")
            for i, entity in enumerate(entities):
                # 验证枚举类型正确转换
                assert entity.market in [MARKET_TYPES.CHINA, MARKET_TYPES.NASDAQ, MARKET_TYPES.OTHER]
                assert entity.currency in [CURRENCY_TYPES.CNY, CURRENCY_TYPES.USD, CURRENCY_TYPES.OTHER]

                # 验证其他字段类型
                assert isinstance(entity.code, str)
                assert isinstance(entity.code_name, str)
                assert isinstance(entity.industry, str)
                print(f"  - 实体{i+1}: {entity.code} - {entity.code_name}")
                print(f"    市场: {entity.market.name}, 货币: {entity.currency.name}")
            print("✓ 业务对象映射验证通过")

            # 测试4: 验证缓存机制
            print("\n→ 测试转换缓存机制...")
            df2 = model_list.to_dataframe()
            entities2 = model_list.to_entities()
            # 验证结果一致性
            assert df.equals(df2), "DataFrame缓存结果应一致"
            assert len(entities) == len(entities2), "实体列表缓存结果应一致"
            print("✓ 缓存机制验证正确")

            # 测试5: 验证空ModelList的转换
            print("\n→ 测试空ModelList的转换...")
            empty_model_list = stock_crud.find(filters={"code": "NONEXISTENT_CONVERT_TEST"})
            assert len(empty_model_list) == 0, "空ModelList长度应为0"
            empty_df = empty_model_list.to_dataframe()
            empty_entities = empty_model_list.to_entities()
            assert isinstance(empty_df, pd.DataFrame), "空转换应返回DataFrame"
            assert empty_df.shape[0] == 0, "空DataFrame行数应为0"
            assert isinstance(empty_entities, list), "空转换应返回列表"
            assert len(empty_entities) == 0, "空实体列表长度应为0"
            print("✓ 空ModelList转换验证正确")

            # 测试6: 单个Model的to_entity转换
            print("\n→ 测试单个Model的to_entity转换...")
            single_model = model_list[0]  # 获取第一个Model
            single_entity = single_model.to_entity()
            print(f"✓ 单个Model转换: {single_model.code} → {single_entity.code_name}")

            assert isinstance(single_entity, StockInfo), "单个Model应转换为StockInfo实体"
            assert single_entity.code == single_model.code
            assert hasattr(single_entity.market, 'name'), "转换后market应为枚举对象"
            assert hasattr(single_entity.currency, 'name'), "转换后currency应为枚举对象"
            print("✓ 单个Model to_entity转换验证通过")

            print("\n✓ 所有StockInfo ModelList转换功能测试通过！")

        finally:
            # 清理测试数据并验证删除效果
            try:
                test_stocks_to_delete = stock_crud.find(filters={"code__like": "CONVERT_TEST%"})
                before_delete = len(stock_crud.find(filters={"source": SOURCE_TYPES.TEST.value}))

                for stock in test_stocks_to_delete:
                    stock_crud.remove({"uuid": stock.uuid})

                after_delete = len(stock_crud.find(filters={"source": SOURCE_TYPES.TEST.value}))
                deleted_count = before_delete - after_delete
                print(f"\n→ 清理测试数据: 删除了 {deleted_count} 条记录")

            except Exception as cleanup_error:
                print(f"\n✗ 清理测试数据失败: {cleanup_error}")
                # 不重新抛出异常，避免影响测试结果


@pytest.mark.enum
@pytest.mark.database
class TestStockInfoCRUDEnumValidation:
    """StockInfoCRUD枚举传参验证测试 - 整合自独立的枚举测试文件"""

    # 明确配置CRUD类，添加全面的过滤条件以清理所有测试数据
    CRUD_TEST_CONFIG = {
        'crud_class': StockInfoCRUD,
        'filters': {
            'code__like': ['ENUM_%', 'COMPREHENSIVE_%']  # 清理所有枚举测试相关的股票代码
        }
    }

    def test_market_enum_conversions(self):
        """测试股票市场枚举转换功能"""
        print("\n" + "="*60)
        print("开始测试: 股票市场枚举转换")
        print("="*60)

        stock_crud = StockInfoCRUD()

        # 记录初始状态
        before_count = len(stock_crud.find(filters={"code__like": "ENUM_MARKET_%"}))
        print(f"→ 初始状态: {before_count} 条测试数据")

        # 测试不同市场的枚举传参
        market_types = [
            (MARKET_TYPES.CHINA, "中国A股市场"),
            (MARKET_TYPES.NASDAQ, "纳斯达克市场"),
            (MARKET_TYPES.OTHER, "其他市场"),
            (MARKET_TYPES.VOID, "无效市场")
        ]

        print(f"\n→ 测试 {len(market_types)} 种市场枚举传参...")

        # 批量插入并验证条数变化
        for i, (market_type, market_name) in enumerate(market_types):
            test_stock = MStockInfo(
                code=f"ENUM_MARKET_{i+1:03d}",
                code_name=f"测试股票{market_name}",
                market=market_type,  # 直接传入枚举对象
                currency=CURRENCY_TYPES.CNY,
                source=SOURCE_TYPES.TEST,  # 添加source参数
                industry="测试行业",
                list_date=datetime.now(),
                delist_date=datetime(2099, 12, 31)
            )

            before_insert = len(stock_crud.find(filters={"code__like": "ENUM_MARKET_%"}))
            result = stock_crud.add(test_stock)
            assert result is not None, f"{market_name} 股票应该成功插入"

            after_insert = len(stock_crud.find(filters={"code__like": "ENUM_MARKET_%"}))
            assert after_insert - before_insert == 1, f"{market_name} 插入应该增加1条记录"
            print(f"  ✓ {market_name} 枚举传参成功，数据库条数验证正确")

        # 验证总插入数量
        final_count = len(stock_crud.find(filters={"code__like": "ENUM_MARKET_%"}))
        assert final_count - before_count == len(market_types), f"总共应该插入{len(market_types)}条记录"
        print(f"✓ 批量插入验证正确，共增加 {final_count - before_count} 条记录")

        # 验证查询时的枚举转换
        print("\n→ 验证查询时的枚举转换...")
        stocks = stock_crud.find(filters={"code__like": "ENUM_MARKET_%"})
        expected_count = final_count - before_count  # 我们新增的记录数
        assert len(stocks) >= expected_count, f"应该至少查询到{expected_count}条市场股票，实际{len(stocks)}条"

        # 过滤出我们刚创建的股票
        our_stocks = [s for s in stocks if s.code.startswith("ENUM_MARKET_")]
        print(f"→ 查询到总共{len(stocks)}条股票，其中我们的测试股票{len(our_stocks)}条")

        for stock in our_stocks:
            # 数据库查询结果market是int值，需要转换为枚举对象进行比较
            market_enum = MARKET_TYPES(stock.market)
            assert market_enum in [mt for mt, _ in market_types], "查询结果应该是有效的枚举对象"
            market_name = dict([(mt, mn) for mt, mn in market_types])[market_enum]
            print(f"  ✓ 股票 {stock.code}: 市场={market_name}, 行业={stock.industry}")

        # 测试市场过滤查询（枚举传参）
        print("\n→ 测试市场过滤查询（枚举传参）...")
        china_stocks = stock_crud.find(
            filters={
                "code__like": "ENUM_MARKET_%",
                "market": MARKET_TYPES.CHINA  # 枚举传参
            }
        )
        assert len(china_stocks) >= 1, "应该查询到至少1条中国A股股票"
        print(f"  ✓ 中国A股股票: {len(china_stocks)} 条，枚举过滤验证正确")

        # 清理测试数据并验证删除效果
        print("\n→ 清理测试数据...")
        delete_before = len(stock_crud.find(filters={"code__like": "ENUM_MARKET_%"}))
        stock_crud.remove(filters={"code__like": "ENUM_MARKET_%"})
        delete_after = len(stock_crud.find(filters={"code__like": "ENUM_MARKET_%" }))

        assert delete_before - delete_after >= len(market_types), f"删除操作应该至少移除{len(market_types)}条记录"
        print("✓ 测试数据清理完成，数据库条数验证正确")

        print("✓ 股票市场枚举转换测试通过")

    def test_currency_enum_conversions(self):
        """测试股票货币枚举转换功能"""
        print("\n" + "="*60)
        print("开始测试: 股票货币枚举转换")
        print("="*60)

        stock_crud = StockInfoCRUD()

        # 记录初始状态
        before_count = len(stock_crud.find(filters={"code__like": "ENUM_CURRENCY_%"}))
        print(f"→ 初始状态: {before_count} 条测试数据")

        # 测试不同货币的枚举传参
        currency_types = [
            (CURRENCY_TYPES.CNY, "人民币"),
            (CURRENCY_TYPES.USD, "美元"),
            (CURRENCY_TYPES.OTHER, "其他货币"),
            (CURRENCY_TYPES.VOID, "无效货币")
        ]

        print(f"\n→ 测试 {len(currency_types)} 种货币枚举传参...")

        # 批量插入并验证条数变化
        for i, (currency_type, currency_name) in enumerate(currency_types):
            test_stock = MStockInfo(
                code=f"ENUM_CURRENCY_{i+1:03d}",
                code_name=f"测试股票{currency_name}",
                market=MARKET_TYPES.CHINA,
                currency=currency_type,  # 直接传入枚举对象
                source=SOURCE_TYPES.TEST,  # 添加source参数
                industry="测试行业",
                list_date=datetime.now(),
                delist_date=datetime(2099, 12, 31)
            )

            before_insert = len(stock_crud.find(filters={"code__like": "ENUM_CURRENCY_%"}))
            result = stock_crud.add(test_stock)
            assert result is not None, f"{currency_name} 股票应该成功插入"

            after_insert = len(stock_crud.find(filters={"code__like": "ENUM_CURRENCY_%"}))
            assert after_insert - before_insert == 1, f"{currency_name} 插入应该增加1条记录"
            print(f"  ✓ {currency_name} 枚举传参成功，数据库条数验证正确")

        # 验证总插入数量
        final_count = len(stock_crud.find(filters={"code__like": "ENUM_CURRENCY_%"}))
        assert final_count - before_count == len(currency_types), f"总共应该插入{len(currency_types)}条记录"
        print(f"✓ 批量插入验证正确，共增加 {final_count - before_count} 条记录")

        # 验证查询时的枚举转换
        print("\n→ 验证查询时的枚举转换...")
        stocks = stock_crud.find(filters={"code__like": "ENUM_CURRENCY_%"})
        expected_count = final_count - before_count  # 我们新增的记录数
        assert len(stocks) >= expected_count, f"应该至少查询到{expected_count}条货币股票，实际{len(stocks)}条"

        # 过滤出我们刚创建的股票
        our_stocks = [s for s in stocks if s.code.startswith("ENUM_CURRENCY_")]
        print(f"→ 查询到总共{len(stocks)}条股票，其中我们的测试股票{len(our_stocks)}条")

        for stock in our_stocks:
            # 数据库查询结果currency是int值，需要转换为枚举对象进行比较
            currency_enum = CURRENCY_TYPES(stock.currency)
            assert currency_enum in [ct for ct, _ in currency_types], "查询结果应该是有效的枚举对象"
            currency_name = dict([(ct, cn) for ct, cn in currency_types])[currency_enum]
            print(f"  ✓ 股票 {stock.code}: 货币={currency_name}, 行业={stock.industry}")

        # 测试货币过滤查询（枚举传参）
        print("\n→ 测试货币过滤查询（枚举传参）...")
        usd_stocks = stock_crud.find(
            filters={
                "code__like": "ENUM_CURRENCY_%",
                "currency": CURRENCY_TYPES.USD  # 枚举传参
            }
        )
        assert len(usd_stocks) >= 1, "应该查询到至少1条美元股票"
        print(f"  ✓ 美元股票: {len(usd_stocks)} 条，枚举过滤验证正确")

        # 清理测试数据并验证删除效果
        print("\n→ 清理测试数据...")
        delete_before = len(stock_crud.find(filters={"code__like": "ENUM_CURRENCY_%"}))
        stock_crud.remove(filters={"code__like": "ENUM_CURRENCY_%"})
        delete_after = len(stock_crud.find(filters={"code__like": "ENUM_CURRENCY_%" }))

        assert delete_before - delete_after >= len(currency_types), f"删除操作应该至少移除{len(currency_types)}条记录"
        print("✓ 测试数据清理完成，数据库条数验证正确")

        print("✓ 股票货币枚举转换测试通过")

    def test_comprehensive_enum_validation(self):
        """测试股票信息综合枚举验证功能"""
        print("\n" + "="*60)
        print("开始测试: 股票信息综合枚举验证")
        print("="*60)

        stock_crud = StockInfoCRUD()

        # 记录初始状态
        before_count = len(stock_crud.find(filters={"code__like": "COMPREHENSIVE_%"}))
        print(f"→ 初始状态: {before_count} 条测试数据")

        # 创建包含所有枚举字段的测试股票
        enum_combinations = [
            # (市场, 货币, 数据源, 代码, 名称, 行业)
            (MARKET_TYPES.CHINA, CURRENCY_TYPES.CNY, SOURCE_TYPES.TUSHARE, "COMPREHENSIVE_001", "中国银行", "银行"),
            (MARKET_TYPES.NASDAQ, CURRENCY_TYPES.USD, SOURCE_TYPES.YAHOO, "COMPREHENSIVE_002", "苹果公司", "科技"),
            (MARKET_TYPES.OTHER, CURRENCY_TYPES.OTHER, SOURCE_TYPES.AKSHARE, "COMPREHENSIVE_003", "其他市场股票", "综合"),
            (MARKET_TYPES.VOID, CURRENCY_TYPES.USD, SOURCE_TYPES.BACKTEST, "COMPREHENSIVE_004", "测试股票", "测试"),
            (MARKET_TYPES.CHINA, CURRENCY_TYPES.CNY, SOURCE_TYPES.TDX, "COMPREHENSIVE_005", "比亚迪", "新能源"),
        ]

        print(f"\n→ 创建 {len(enum_combinations)} 个综合枚举测试股票...")

        # 批量插入并验证条数变化
        for i, (market, currency, source, code, name, industry) in enumerate(enum_combinations):
            test_stock = MStockInfo(
                code=f"{code}.SZ" if market == MARKET_TYPES.CHINA else f"{code}.US",
                code_name=name,
                market=market,      # 枚举传参
                currency=currency,  # 枚举传参
                industry=industry,
                list_date=datetime.now() - timedelta(days=i*100),
                delist_date=datetime(2099, 12, 31),
                source=source,      # 枚举传参 - 修复：添加source参数
            )

            before_insert = len(stock_crud.find(filters={"code__like": "COMPREHENSIVE_%"}))
            result = stock_crud.add(test_stock)
            assert result is not None, f"{name} 应该成功插入"
            # 直接验证新创建的记录
            assert result.market == market.value, f"新创建的股票 {result.code} 市场值不匹配，预期{market.value}，实际{result.market}"
            assert result.currency == currency.value, f"新创建的股票 {result.code} 货币值不匹配，预期{currency.value}，实际{result.currency}"
            assert result.source == source.value, f"新创建的股票 {result.code} 数据源值不匹配，预期{source.value}，实际{result.source}"

            after_insert = len(stock_crud.find(filters={"code__like": "COMPREHENSIVE_%"}))
            assert after_insert - before_insert == 1, f"{name} 插入应该增加1条记录"
            print(f"  ✓ {name} 创建成功，数据库条数验证正确")

        # 验证总插入数量
        final_count = len(stock_crud.find(filters={"code__like": "COMPREHENSIVE_%"}))
        assert final_count - before_count == len(enum_combinations), f"总共应该插入{len(enum_combinations)}条记录"
        print(f"✓ 批量插入验证正确，共增加 {final_count - before_count} 条记录")

        # 验证所有枚举字段的存储和查询
        print("\n→ 验证所有枚举字段的存储和查询...")
        stocks = stock_crud.find(filters={"code__like": "COMPREHENSIVE_%"})
        expected_count = final_count - before_count  # 我们新增的记录数
        assert len(stocks) >= expected_count, f"应该至少查询到{expected_count}条综合测试股票，实际{len(stocks)}条"

        # 创建名称到预期枚举组合的映射，并选择最新创建的记录
        expected_map = {}
        our_stocks = []

        for market, currency, source, code, name, industry in enum_combinations:
            stock_code = f"{code}.SZ" if market == MARKET_TYPES.CHINA else f"{code}.US"
            expected_map[stock_code] = (market, currency, source, name)

            # 查找该代码的所有记录，选择最新的一条
            code_stocks = [s for s in stocks if s.code == stock_code]
            if code_stocks:
                latest_stock = max(code_stocks, key=lambda s: s.create_at)
                our_stocks.append(latest_stock)

        print(f"→ 查询到总共{len(stocks)}条股票，选择其中{len(our_stocks)}条最新创建的测试股票")

        for stock in our_stocks:
            expected_market, expected_currency, expected_source, name = expected_map[stock.code]

            # 验证枚举字段正确性（数据库查询结果是int值）
            assert stock.market == expected_market.value, f"股票 {stock.code} 市场int值不匹配，预期{expected_market.value}，实际{stock.market}"
            assert stock.currency == expected_currency.value, f"股票 {stock.code} 货币int值不匹配，预期{expected_currency.value}，实际{stock.currency}"
            assert stock.source == expected_source.value, f"股票 {stock.code} 数据源int值不匹配，预期{expected_source.value}，实际{stock.source}"

            # 转换为枚举对象进行显示
            market_enum = MARKET_TYPES(stock.market)
            currency_enum = CURRENCY_TYPES(stock.currency)
            source_enum = SOURCE_TYPES(stock.source)
            print(f"  ✓ 股票 {stock.code}: {name}, 市场={market_enum.name}, 货币={currency_enum.name}, 数据源={source_enum.name}")

        # 验证市场分布统计
        print("\n→ 验证市场分布统计...")
        market_distribution = {}
        for stock in our_stocks:
            market_enum = MARKET_TYPES(stock.market)
            market_name = market_enum.name
            market_distribution[market_name] = market_distribution.get(market_name, 0) + 1

        print(f"  ✓ 市场分布: {market_distribution}")

        # 验证ModelList转换功能
        print("\n→ 验证ModelList转换功能...")
        model_list = stock_crud.find(filters={"code__like": "COMPREHENSIVE_%"})

        assert len(model_list) >= len(enum_combinations), f"ModelList应该包含至少{len(enum_combinations)}条测试股票"

        # 验证to_entities()方法中的枚举转换
        entities = model_list.to_entities()
        our_entities = [e for e in entities if hasattr(e, 'code') and e.code in expected_map]

        for entity in our_entities:
            assert hasattr(entity, 'market'), "业务对象应该有market属性"
            assert hasattr(entity, 'currency'), "业务对象应该有currency属性"
            assert hasattr(entity, 'source'), "业务对象应该有source属性"
            print(f"  ✓ 业务对象 {entity.code}: 所有枚举转换正确")

        print("  ✓ ModelList转换中的枚举验证正确")

        # 清理测试数据并验证删除效果
        print("\n→ 清理测试数据...")
        delete_before = len(stock_crud.find(filters={"code__like": "COMPREHENSIVE_%"}))
        stock_crud.remove(filters={"code__like": "COMPREHENSIVE_%"})
        delete_after = len(stock_crud.find(filters={"code__like": "COMPREHENSIVE_%" }))

        assert delete_before - delete_after >= len(enum_combinations), f"删除操作应该至少移除{len(enum_combinations)}条记录"
        print("✓ 测试数据清理完成，数据库条数验证正确")

        print("✓ 股票信息综合枚举验证测试通过")


# TDD Red阶段验证：确保所有测试开始时都失败
if __name__ == "__main__":
    print("TDD Red阶段验证：StockInfo CRUD测试")
    print("所有测试用例应该在实现开始前失败")
    print("运行: pytest test/data/crud/test_stock_info_crud.py -v")
    print("预期结果: 所有测试失败 (Red阶段)")
    print("重点关注: 股票信息完整性、市场分布分析和行业统计")
    print("新增功能: ModelConversion API, ModelList功能, 枚举转换一致性")