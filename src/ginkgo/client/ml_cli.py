# Upstream: Data Layer
# Downstream: External APIs (Tushare, Yahoo, etc.)
# Role: 机器学习CLI，提供models列出、train训练、predict预测、factors因子计算和strategy策略测试命令






"""
机器学习CLI命令

提供ML模型的训练、评估、预测和管理功能的命令行接口。
"""

import typer
import pandas as pd
import numpy as np
from rich.console import Console
from rich.table import Table
from rich.progress import track
from rich import print
from typing import Optional, List
from datetime import datetime, timedelta

from ginkgo.quant_ml.containers import create_model, get_available_models, ml_container
from ginkgo.quant_ml.features import FeatureProcessor, AlphaFactors
from ginkgo.quant_ml.strategies import PredictionStrategy
from ginkgo.libs import GLOG, GCONF
from ginkgo.data.operations import get_bars_page_filtered

ml_app = typer.Typer(
    name="ml",
    help=":robot: [bold blue]机器学习模块[/bold blue] - 模型训练、预测和策略管理",
    no_args_is_help=True
)

console = Console()


@ml_app.command("models")
def list_models():
    """
    :mag: 列出所有可用的机器学习模型
    """
    try:
        models = get_available_models()
        
        table = Table(title="可用的机器学习模型")
        table.add_column("模型类型", style="cyan")
        table.add_column("模型类", style="green")
        table.add_column("描述", style="yellow")
        
        model_descriptions = {
            "lightgbm": "梯度提升决策树，高效且准确",
            "xgboost": "极端梯度提升，支持GPU加速", 
            "random_forest": "随机森林，集成学习算法",
            "linear": "线性模型，包含Ridge、Lasso等",
            "svm": "支持向量机，适合小样本问题"
        }
        
        for model_type, model_class in models.items():
            description = model_descriptions.get(model_type, "机器学习模型")
            table.add_row(model_type, model_class.__name__, description)
        
        console.print(table)
        console.print(f"\n:information_source: 使用 [cyan]ginkgo ml train --model <model_type>[/cyan] 训练模型")
        
    except Exception as e:
        console.print(f":x: [red]错误:[/red] {e}")
        GLOG.ERROR(f"列出模型失败: {e}")


@ml_app.command("train")
def train_model(
    model_type: str = typer.Option("lightgbm", help="模型类型"),
    code: str = typer.Option("000001.SZ", help="股票代码"),
    start_date: str = typer.Option("20200101", help="开始日期"),
    end_date: str = typer.Option("20231231", help="结束日期"),
    prediction_horizon: int = typer.Option(5, help="预测天数"),
    test_ratio: float = typer.Option(0.2, help="测试集比例"),
    save_path: Optional[str] = typer.Option(None, help="模型保存路径")
):
    """
    :gear: 训练机器学习模型
    """
    try:
        console.print(f":rocket: 开始训练 [cyan]{model_type}[/cyan] 模型...")
        console.print(f"股票代码: {code}, 时间范围: {start_date} - {end_date}")
        
        # 1. 加载数据
        console.print(":floppy_disk: 加载历史数据...")
        bars = get_bars_page_filtered(
            code=code,
            start=start_date,
            end=end_date,
            adjusted=True
        )
        
        if not bars:
            console.print(f":x: [red]未找到股票 {code} 的数据[/red]")
            return
        
        # 转换为DataFrame
        data_list = []
        for bar in track(bars, description="转换数据格式"):
            data_list.append({
                'timestamp': bar.timestamp,
                'open': bar.open,
                'high': bar.high,
                'low': bar.low,
                'close': bar.close,
                'volume': bar.volume,
                'code': bar.code
            })
        
        df = pd.DataFrame(data_list)
        console.print(f":white_check_mark: 加载完成，数据量: {len(df)}")
        
        # 2. 特征工程
        console.print(":wrench: 计算特征因子...")
        alpha_factors = AlphaFactors()
        df_with_features = alpha_factors.calculate_all_factors(df)
        
        # 3. 创建目标变量
        console.print(f":dart: 创建 {prediction_horizon} 日预测目标...")
        df_with_features['target'] = (
            df_with_features['close'].shift(-prediction_horizon) / 
            df_with_features['close'] - 1
        )
        
        # 清理数据
        df_clean = df_with_features.dropna()
        
        if len(df_clean) < 100:
            console.print(":x: [red]有效数据量不足100条，无法训练[/red]")
            return
        
        # 4. 数据分割
        split_idx = int(len(df_clean) * (1 - test_ratio))
        train_data = df_clean.iloc[:split_idx]
        test_data = df_clean.iloc[split_idx:]
        
        console.print(f":scissors: 数据分割 - 训练集: {len(train_data)}, 测试集: {len(test_data)}")
        
        # 5. 特征处理
        feature_processor = FeatureProcessor()
        
        # 排除非特征列
        exclude_cols = ['timestamp', 'code', 'target', 'open', 'high', 'low', 'close', 'volume']
        feature_cols = [col for col in df_clean.columns if col not in exclude_cols]
        
        X_train = train_data[feature_cols]
        y_train = train_data[['target']]
        X_test = test_data[feature_cols]
        y_test = test_data[['target']]
        
        # 特征预处理
        console.print(":gear: 特征预处理...")
        X_train_processed = feature_processor.fit_transform(X_train, y_train)
        X_test_processed = feature_processor.transform(X_test)
        
        console.print(f":white_check_mark: 特征处理完成，特征数: {X_train_processed.shape[1]}")
        
        # 6. 模型训练
        console.print(f":brain: 训练 {model_type} 模型...")
        
        # 创建模型
        if model_type == "lightgbm":
            model = create_model(model_type, task="regression", early_stopping_rounds=50)
        elif model_type == "xgboost":
            model = create_model(model_type, task="regression", early_stopping_rounds=50)
        else:
            model = create_model(model_type, task="regression")
        
        # 训练模型
        eval_set = [(X_test_processed, y_test)] if model_type in ["lightgbm", "xgboost"] else None
        
        if eval_set:
            model.fit(X_train_processed, y_train, eval_set=eval_set, verbose_eval=20)
        else:
            model.fit(X_train_processed, y_train)
        
        console.print(":white_check_mark: [green]模型训练完成！[/green]")
        
        # 7. 模型评估
        console.print(":chart_with_upwards_trend: 模型评估...")
        
        # 预测
        train_pred = model.predict(X_train_processed)
        test_pred = model.predict(X_test_processed)
        
        # 计算评估指标
        from sklearn.metrics import mean_squared_error, r2_score
        
        train_mse = mean_squared_error(y_train, train_pred)
        test_mse = mean_squared_error(y_test, test_pred)
        train_r2 = r2_score(y_train, train_pred)
        test_r2 = r2_score(y_test, test_pred)
        
        # 计算方向准确率
        train_direction_acc = np.mean(
            np.sign(train_pred.values.flatten()) == np.sign(y_train.values.flatten())
        )
        test_direction_acc = np.mean(
            np.sign(test_pred.values.flatten()) == np.sign(y_test.values.flatten())
        )
        
        # 显示结果
        results_table = Table(title="模型评估结果")
        results_table.add_column("指标", style="cyan")
        results_table.add_column("训练集", style="green")
        results_table.add_column("测试集", style="yellow")
        
        results_table.add_row("MSE", f"{train_mse:.6f}", f"{test_mse:.6f}")
        results_table.add_row("R²", f"{train_r2:.4f}", f"{test_r2:.4f}")
        results_table.add_row("方向准确率", f"{train_direction_acc:.4f}", f"{test_direction_acc:.4f}")
        
        console.print(results_table)
        
        # 8. 特征重要性
        if hasattr(model, 'get_feature_importance'):
            importance = model.get_feature_importance()
            if importance is not None:
                console.print(":bar_chart: 前10重要特征:")
                importance_table = Table()
                importance_table.add_column("特征名", style="cyan")
                importance_table.add_column("重要性", style="green")
                
                for feat, imp in importance.head(10).items():
                    importance_table.add_row(feat, f"{imp:.4f}")
                
                console.print(importance_table)
        
        # 9. 保存模型
        if save_path:
            model.save(save_path)
            console.print(f":floppy_disk: 模型已保存到: {save_path}")
        else:
            # 自动生成保存路径
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_path = f"./models/{model_type}_{code}_{timestamp}.pkl"
            
            import os
            os.makedirs("./models", exist_ok=True)
            
            model.save(default_path)
            console.print(f":floppy_disk: 模型已保存到: {default_path}")
        
        console.print(":tada: [green]模型训练和评估完成！[/green]")
        
    except Exception as e:
        console.print(f":x: [red]训练失败:[/red] {e}")
        GLOG.ERROR(f"模型训练失败: {e}")


@ml_app.command("predict")
def predict_with_model(
    model_path: str = typer.Argument(..., help="模型文件路径"),
    code: str = typer.Option("000001.SZ", help="股票代码"),
    date: str = typer.Option("", help="预测日期 (YYYYMMDD)，为空则使用最新数据")
):
    """
    :crystal_ball: 使用训练好的模型进行预测
    """
    try:
        console.print(f":crystal_ball: 加载模型: {model_path}")
        
        # 加载模型
        from ginkgo.core.interfaces.model_interface import IModel
        model = IModel.load(model_path)
        
        if not model.is_trained:
            console.print(":x: [red]模型未训练[/red]")
            return
        
        console.print(":white_check_mark: [green]模型加载成功[/green]")
        
        # 获取预测日期
        if not date:
            pred_date = datetime.now().strftime("%Y%m%d")
        else:
            pred_date = date
        
        # 加载数据
        start_date = (datetime.strptime(pred_date, "%Y%m%d") - timedelta(days=100)).strftime("%Y%m%d")
        
        console.print(f":floppy_disk: 加载 {code} 的数据 ({start_date} - {pred_date})")
        
        bars = get_bars_page_filtered(
            code=code,
            start=start_date,
            end=pred_date,
            adjusted=True
        )
        
        if not bars:
            console.print(f":x: [red]未找到股票 {code} 的数据[/red]")
            return
        
        # 转换数据并计算特征
        data_list = []
        for bar in bars:
            data_list.append({
                'timestamp': bar.timestamp,
                'open': bar.open,
                'high': bar.high,
                'low': bar.low,
                'close': bar.close,
                'volume': bar.volume,
                'code': bar.code
            })
        
        df = pd.DataFrame(data_list)
        
        # 计算特征
        console.print(":wrench: 计算特征...")
        alpha_factors = AlphaFactors()
        df_with_features = alpha_factors.calculate_all_factors(df)
        
        if len(df_with_features) == 0:
            console.print(":x: [red]特征计算失败[/red]")
            return
        
        # 获取最新数据进行预测
        latest_data = df_with_features.tail(1)
        
        # 特征处理
        feature_processor = FeatureProcessor()
        exclude_cols = ['timestamp', 'code', 'open', 'high', 'low', 'close', 'volume']
        feature_cols = [col for col in latest_data.columns if col not in exclude_cols]
        
        features = latest_data[feature_cols].dropna(axis=1)
        
        if features.empty:
            console.print(":x: [red]没有有效特征数据[/red]")
            return
        
        # 预测
        console.print(":gear: 进行预测...")
        prediction = model.predict(features)
        
        pred_value = prediction.iloc[0, 0] if isinstance(prediction, pd.DataFrame) else prediction[0]
        
        # 显示结果
        latest_price = latest_data['close'].iloc[-1]
        latest_time = latest_data['timestamp'].iloc[-1]
        
        console.print(f"\n:chart_with_upwards_trend: [bold]预测结果[/bold]")
        console.print(f"股票代码: [cyan]{code}[/cyan]")
        console.print(f"当前价格: [yellow]{latest_price:.2f}[/yellow]")
        console.print(f"最新时间: [blue]{latest_time}[/blue]")
        console.print(f"预测收益率: [{'green' if pred_value > 0 else 'red'}]{pred_value:.4f} ({pred_value*100:.2f}%)[/]")
        
        if pred_value > 0.01:
            console.print(":arrow_up: [green]建议: 买入[/green]")
        elif pred_value < -0.01:
            console.print(":arrow_down: [red]建议: 卖出[/red]")
        else:
            console.print(":pause_button: [yellow]建议: 持有[/yellow]")
        
    except Exception as e:
        console.print(f":x: [red]预测失败:[/red] {e}")
        GLOG.ERROR(f"预测失败: {e}")


@ml_app.command("factors")
def show_factors(
    code: str = typer.Option("000001.SZ", help="股票代码"),
    start_date: str = typer.Option("20231201", help="开始日期"),
    end_date: str = typer.Option("20231231", help="结束日期"),
    factor_group: str = typer.Option("all", help="因子组别 (basic/technical/volatility/momentum/mean_reversion/all)")
):
    """
    :bar_chart: 计算和显示Alpha因子
    """
    try:
        console.print(f":bar_chart: 计算 {code} 的Alpha因子...")
        
        # 加载数据
        bars = get_bars_page_filtered(
            code=code,
            start=start_date,
            end=end_date,
            adjusted=True
        )
        
        if not bars:
            console.print(f":x: [red]未找到股票 {code} 的数据[/red]")
            return
        
        # 转换数据
        data_list = []
        for bar in bars:
            data_list.append({
                'timestamp': bar.timestamp,
                'open': bar.open,
                'high': bar.high,
                'low': bar.low,
                'close': bar.close,
                'volume': bar.volume
            })
        
        df = pd.DataFrame(data_list)
        console.print(f":white_check_mark: 数据加载完成: {len(df)} 条记录")
        
        # 计算因子
        alpha_factors = AlphaFactors()
        
        if factor_group == "all":
            df_factors = alpha_factors.calculate_all_factors(df)
        elif factor_group == "basic":
            df_factors = alpha_factors.calculate_basic_factors(df)
        elif factor_group == "technical":
            df_factors = alpha_factors.calculate_technical_indicators(df)
        elif factor_group == "volatility":
            df_factors = alpha_factors.calculate_volatility_factors(df)
        elif factor_group == "momentum":
            df_factors = alpha_factors.calculate_momentum_factors(df)
        elif factor_group == "mean_reversion":
            df_factors = alpha_factors.calculate_mean_reversion_factors(df)
        else:
            console.print(f":x: [red]未知的因子组别: {factor_group}[/red]")
            return
        
        # 显示最新因子值
        latest_factors = df_factors.tail(1)
        
        console.print(f"\n:calendar: [bold]{factor_group.upper()}因子 - 最新值[/bold]")
        console.print(f"时间: {latest_factors['timestamp'].iloc[0]}")
        console.print(f"股价: {latest_factors['close'].iloc[0]:.2f}")
        
        # 获取因子分组
        factor_groups = alpha_factors.get_factor_groups()
        
        if factor_group == "all":
            display_factors = []
            for group_factors in factor_groups.values():
                display_factors.extend(group_factors)
        else:
            display_factors = factor_groups.get(factor_group, [])
        
        # 显示表格
        if display_factors:
            table = Table()
            table.add_column("因子名称", style="cyan")
            table.add_column("数值", style="green")
            table.add_column("描述", style="yellow")
            
            for factor in display_factors:
                if factor in latest_factors.columns:
                    value = latest_factors[factor].iloc[0]
                    if pd.notna(value):
                        table.add_row(
                            factor, 
                            f"{value:.4f}", 
                            _get_factor_description(factor)
                        )
            
            console.print(table)
        
        console.print(f"\n:information_source: 总计算因子数: {len(df_factors.columns) - len(df.columns)}")
        
    except Exception as e:
        console.print(f":x: [red]因子计算失败:[/red] {e}")
        GLOG.ERROR(f"因子计算失败: {e}")


def _get_factor_description(factor_name: str) -> str:
    """获取因子描述"""
    descriptions = {
        'price_range': '价格波动幅度',
        'returns_1d': '1日收益率',
        'volume_ratio': '成交量比率',
        'rsi_14': 'RSI技术指标',
        'volatility_20': '20日波动率',
        'momentum_5': '5日动量',
        'bb_zscore': '布林带Z分数'
    }
    return descriptions.get(factor_name, '量化因子')


@ml_app.command("strategy")
def test_ml_strategy(
    model_path: str = typer.Argument(..., help="模型文件路径"),
    code: str = typer.Option("000001.SZ", help="股票代码"),
    start_date: str = typer.Option("20230101", help="开始日期"),
    end_date: str = typer.Option("20231231", help="结束日期"),
):
    """
    :chart_with_upwards_trend: 测试机器学习策略
    """
    try:
        console.print(f":chart_with_upwards_trend: 测试ML策略...")
        console.print(f"模型: {model_path}")
        console.print(f"股票: {code}, 时间: {start_date} - {end_date}")
        
        # 加载模型
        from ginkgo.core.interfaces.model_interface import IModel
        model = IModel.load(model_path)
        
        # 创建策略
        strategy = PredictionStrategy(
            name="TestMLStrategy",
            model=model,
            prediction_horizon=5,
            signal_threshold=0.01
        )
        
        console.print(":white_check_mark: [green]策略初始化完成[/green]")
        console.print(f"策略类型: {strategy.strategy_type}")
        console.print(f"模型状态: {'已训练' if model.is_trained else '未训练'}")
        
        # 这里可以添加更多策略测试逻辑
        # 比如模拟回测、信号生成测试等
        
        strategy_metrics = strategy.get_strategy_summary()
        
        metrics_table = Table(title="策略信息")
        metrics_table.add_column("指标", style="cyan")
        metrics_table.add_column("数值", style="green")
        
        for key, value in strategy_metrics.items():
            if isinstance(value, float):
                metrics_table.add_row(key, f"{value:.4f}")
            else:
                metrics_table.add_row(key, str(value))
        
        console.print(metrics_table)
        
    except Exception as e:
        console.print(f":x: [red]策略测试失败:[/red] {e}")
        GLOG.ERROR(f"策略测试失败: {e}")


if __name__ == "__main__":
    ml_app()