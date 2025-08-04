#!/usr/bin/env python3
"""
Ginkgo 快速启动脚本

一键测试和验证 Ginkgo 库回测功能的完整流程。
包含环境检查、示例运行、结果展示等功能。

使用方法:
    python quick_start.py                    # 运行完整演示
    python quick_start.py --check-only      # 仅检查环境
    python quick_start.py --simple          # 简化演示（不生成图表）

作者: Ginkgo Framework
日期: 2025
"""

import sys
import argparse
import traceback
from pathlib import Path

def check_environment():
    """检查运行环境"""
    print(":magnifying_glass_tilted_left: 检查 Ginkgo 运行环境...")
    print("="*50)
    
    issues = []
    
    # 1. Python 版本检查
    if sys.version_info < (3, 8):
        issues.append(":x: Python 版本过低，需要 3.8+")
    else:
        print(f":white_check_mark: Python 版本: {sys.version.split()[0]}")
    
    # 2. 核心库导入检查
    try:
        from ginkgo.libs import GLOG, GCONF
        print(":white_check_mark: Ginkgo 核心库导入成功")
    except ImportError as e:
        issues.append(f":x: Ginkgo 核心库导入失败: {e}")
    
    # 3. 数据访问检查
    try:
        from ginkgo.data import get_stockinfos
        stockinfos = get_stockinfos()
        if stockinfos.shape[0] > 0:
            print(f":white_check_mark: 数据库连接正常，找到 {stockinfos.shape[0]} 只股票")
        else:
            issues.append(":warning: 数据库为空，建议运行: ginkgo data init")
    except Exception as e:
        issues.append(f":x: 数据库连接失败: {e}")
    
    # 4. 回测组件检查
    try:
        from ginkgo.backtest.execution.engines import HistoricEngine
        from ginkgo.backtest.execution.portfolios import PortfolioT1Backtest
        from ginkgo.backtest.strategy.strategies.base_strategy import StrategyBase
        print(":white_check_mark: 回测组件导入成功")
    except ImportError as e:
        issues.append(f":x: 回测组件导入失败: {e}")
    
    # 5. 可选依赖检查
    optional_deps = [
        ("matplotlib", "图表绘制"),
        ("pandas", "数据处理"),
        ("numpy", "数值计算"),
    ]
    
    for module_name, description in optional_deps:
        try:
            __import__(module_name)
            print(f":white_check_mark: {description}库 ({module_name}) 可用")
        except ImportError:
            issues.append(f":warning: 可选依赖 {module_name} 未安装，{description}功能可能受限")
    
    # 6. 配置文件检查
    config_files = [
        Path.home() / ".ginkgo" / "config.yaml",
        Path.home() / ".ginkgo" / "secure.yml"
    ]
    
    for config_file in config_files:
        if config_file.exists():
            print(f":white_check_mark: 配置文件存在: {config_file}")
        else:
            issues.append(f":warning: 配置文件不存在: {config_file}")
    
    print("\n" + "="*50)
    
    if not issues:
        print(":party_popper: 环境检查完成，所有检查项目都通过！")
        return True
    else:
        print(":clipboard: 环境检查发现以下问题:")
        for issue in issues:
            print(f"  {issue}")
        
        critical_issues = [i for i in issues if i.startswith(":x:")]
        if critical_issues:
            print("\n❗ 发现关键问题，建议先解决后再运行演示")
            return False
        else:
            print("\n:bulb: 发现一些警告，但不影响基本功能运行")
            return True


def run_simple_demo():
    """运行简化演示"""
    print("\n:rocket: 运行 Ginkgo 简化回测演示...")
    print("="*50)
    
    try:
        # 导入必要的模块
        from ginkgo_backtest_demo import GinkgoBacktestDemo
        
        # 创建演示实例
        demo = GinkgoBacktestDemo()
        
        # 设置简化模式（不保存文件）
        print(":bar_chart: 开始简化回测演示...")
        
        # 环境设置
        if not demo.setup_environment():
            print(":x: 环境设置失败")
            return False
        
        # 获取样本股票
        stock_codes = demo.get_sample_stocks(2)  # 减少股票数量以加快演示
        start_date = "2024-05-01"  # 缩短时间范围
        end_date = "2024-06-30"
        
        print(f":calendar: 回测时间: {start_date} 至 {end_date}")
        print(f":chart_with_upwards_trend: 股票池: {stock_codes}")
        
        # 尝试手动装配方式（最可靠）
        print("\n:wrench: 使用手动装配方式进行回测...")
        engine = demo.method_3_manual_assembly(stock_codes, start_date, end_date)
        
        if engine:
            results = demo.run_backtest(engine, "手动装配演示")
            if results:
                demo.analyze_results(results)
                print("\n:white_check_mark: 简化演示完成成功！")
                return True
        
        print(":x: 简化演示失败")
        return False
        
    except Exception as e:
        print(f":x: 演示运行出错: {e}")
        traceback.print_exc()
        return False


def run_full_demo():
    """运行完整演示"""
    print("\n:dart: 运行 Ginkgo 完整回测演示...")
    print("="*50)
    
    try:
        # 导入演示模块
        from ginkgo_backtest_demo import GinkgoBacktestDemo
        from ginkgo_analysis_utils import GinkgoAnalyzer
        
        # 1. 运行回测演示
        demo = GinkgoBacktestDemo()
        demo.run_demo()
        
        # 2. 运行结果分析演示
        print("\n:bar_chart: 运行结果分析演示...")
        analyzer = GinkgoAnalyzer()
        analyzer.run_full_analysis(
            engine_id="demo_engine_001",
            save_charts=False,  # 不保存图表文件
            export_excel=False  # 不导出Excel文件
        )
        
        print("\n:party_popper: 完整演示完成！")
        return True
        
    except Exception as e:
        print(f":x: 完整演示出错: {e}")
        traceback.print_exc()
        return False


def show_help_info():
    """显示帮助信息"""
    help_text = """
🌿 Ginkgo 量化回测库快速入门

📚 主要文件:
  • ginkgo_backtest_demo.py     - 完整回测演示脚本
  • ginkgo_analysis_utils.py    - 结果分析工具
  • GINKGO_BACKTEST_GUIDE.md    - 详细使用指南
  • quick_start.py              - 本快速启动脚本

:rocket: 快速开始:
  1. 检查环境:  python quick_start.py --check-only
  2. 简化演示:  python quick_start.py --simple
  3. 完整演示:  python quick_start.py

📖 学习路径:
  1. 阅读 GINKGO_BACKTEST_GUIDE.md 了解基本概念
  2. 运行 quick_start.py 查看演示效果  
  3. 修改 ginkgo_backtest_demo.py 中的策略参数进行实验
  4. 使用 ginkgo_analysis_utils.py 分析自己的回测结果

:bulb: 常用命令:
  • ginkgo data init                    - 初始化数据库
  • ginkgo data update --stockinfo      - 更新股票信息
  • ginkgo system config set --debug on - 启用调试模式

:link: 更多资源:
  • 项目主页: https://github.com/Kaoruha/GinkGO
  • 文档目录: ./docs/
  • 示例代码: ./examples/
    """
    print(help_text)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Ginkgo 快速启动脚本")
    parser.add_argument("--check-only", action="store_true", help="仅检查环境，不运行演示")
    parser.add_argument("--simple", action="store_true", help="运行简化演示")
    parser.add_argument("--help-info", action="store_true", help="显示详细帮助信息")
    
    args = parser.parse_args()
    
    print("🌿 欢迎使用 Ginkgo 量化回测库！")
    print("="*60)
    
    # 显示帮助信息
    if args.help_info:
        show_help_info()
        return
    
    # 环境检查
    env_ok = check_environment()
    
    if args.check_only:
        print("\n:clipboard: 环境检查完成")
        sys.exit(0 if env_ok else 1)
    
    if not env_ok:
        print("\n:bulb: 建议:")
        print("  1. 运行 'ginkgo data init' 初始化数据库")
        print("  2. 运行 'ginkgo data update --stockinfo' 更新股票数据")  
        print("  3. 运行 'ginkgo system config set --debug on' 启用调试模式")
        print("  4. 再次运行此脚本")
        
        response = input("\n是否继续运行演示？(y/N): ").lower().strip()
        if response != 'y':
            print("👋 退出程序")
            return
    
    # 运行演示
    if args.simple:
        success = run_simple_demo()
    else:
        success = run_full_demo()
    
    if success:
        print("\n:confetti_ball: 演示运行成功！")
        print("\n📖 接下来你可以:")
        print("  • 阅读 GINKGO_BACKTEST_GUIDE.md 了解更多用法")
        print("  • 修改策略参数进行实验")
        print("  • 开发自己的量化策略")
        print("  • 分析真实的历史数据")
    else:
        print("\n😞 演示运行遇到问题")
        print("  • 检查错误信息并解决相关问题")
        print("  • 查看 GINKGO_BACKTEST_GUIDE.md 中的常见问题章节")
        print("  • 确保数据库已正确初始化")


if __name__ == "__main__":
    main()