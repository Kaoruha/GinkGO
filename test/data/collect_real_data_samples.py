#!/usr/bin/env python3
"""
数据收集脚本：获取真实API格式样本

此脚本用于获取TDX和Tushare真实API的数据格式样本，
用于构建准确的Mock数据进行单元测试。

运行前请确保：
1. TDX网络连接正常
2. Tushare Token已配置
3. 测试环境已设置
"""

import sys
import os
import json
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

try:
    from ginkgo.data.sources.ginkgo_tdx import GinkgoTDX
    from ginkgo.data.sources.ginkgo_tushare import GinkgoTushare
    from ginkgo.libs import datetime_normalize, GCONF
    
    print(":white_check_mark: 成功导入Ginkgo模块")
except ImportError as e:
    print(f":x: 导入错误: {e}")
    sys.exit(1)


class DataSampleCollector:
    """真实数据样本收集器"""
    
    def __init__(self):
        self.output_dir = Path(__file__).parent / "real_data_samples"
        self.output_dir.mkdir(exist_ok=True)
        
        # 测试参数
        self.test_code = "000001.SZ"  # 平安银行
        self.tick_date_range = [
            "2024-01-15", "2024-01-16", "2024-01-17", 
            "2024-01-18", "2024-01-19", "2024-01-20"
        ]
        self.bar_date_range = [
            "2024-02-01", "2024-02-02", "2024-02-03",
            "2024-02-04", "2024-02-05"
        ]
        
    def collect_tdx_tick_samples(self):
        """收集TDX tick数据样本"""
        print("\n:arrows_counterclockwise: 开始收集TDX tick数据样本...")
        
        try:
            tdx = GinkgoTDX()
            tick_samples = {}
            
            for date_str in self.tick_date_range:
                print(f"  :satellite_antenna: 获取 {self.test_code} 在 {date_str} 的tick数据...")
                
                try:
                    # 获取tick数据
                    df = tdx.fetch_history_transaction_detail(self.test_code, date_str)
                    
                    if df is not None and not df.empty:
                        # 只取前10条记录作为样本
                        sample_df = df.head(10).copy()
                        
                        # 转换为可序列化的格式
                        # 处理时间戳类型的序列化问题
                        serializable_df = sample_df.copy()
                        
                        # 将timestamp列转换为字符串
                        if 'timestamp' in serializable_df.columns:
                            serializable_df['timestamp'] = serializable_df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
                        
                        sample_data = {
                            "columns": list(serializable_df.columns),
                            "data": serializable_df.to_dict('records'),
                            "dtypes": {col: str(dtype) for col, dtype in sample_df.dtypes.items()},
                            "shape": serializable_df.shape,
                            "sample_values": {
                                col: list(serializable_df[col].head(5).astype(str)) 
                                for col in serializable_df.columns
                            }
                        }
                        
                        tick_samples[date_str] = sample_data
                        print(f"    :white_check_mark: 成功获取 {sample_df.shape[0]} 条记录")
                        
                    else:
                        tick_samples[date_str] = None
                        print(f"    :warning: 无数据")
                        
                except Exception as e:
                    print(f"    :x: 失败: {e}")
                    tick_samples[date_str] = {"error": str(e)}
            
            # 保存tick样本数据
            output_file = self.output_dir / "tdx_tick_samples.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(tick_samples, f, indent=2, ensure_ascii=False)
            
            print(f":white_check_mark: TDX tick样本已保存到: {output_file}")
            return tick_samples
            
        except Exception as e:
            print(f":x: TDX tick数据收集失败: {e}")
            return {}
    
    def collect_tushare_bar_samples(self):
        """收集Tushare bar数据样本"""
        print("\n:arrows_counterclockwise: 开始收集Tushare bar数据样本...")
        
        try:
            # 检查Token
            if not hasattr(GCONF, 'TUSHARETOKEN') or not GCONF.TUSHARETOKEN:
                print(":warning: TUSHARETOKEN未配置，跳过Tushare数据收集")
                return {}
            
            tushare = GinkgoTushare()
            bar_samples = {}
            
            # 构建日期范围
            start_date = self.bar_date_range[0].replace("-", "")
            end_date = self.bar_date_range[-1].replace("-", "")
            
            print(f"  :satellite_antenna: 获取 {self.test_code} 在 {start_date} 到 {end_date} 的bar数据...")
            
            try:
                # 获取日线数据
                df = tushare.fetch_cn_stock_daybar(self.test_code, start_date, end_date)
                
                if df is not None and not df.empty:
                    # 转换为可序列化的格式
                    sample_data = {
                        "columns": list(df.columns),
                        "data": df.to_dict('records'),
                        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
                        "shape": df.shape,
                        "sample_values": {
                            col: list(df[col].head(5).astype(str)) 
                            for col in df.columns
                        }
                    }
                    
                    bar_samples["date_range_data"] = sample_data
                    print(f"    :white_check_mark: 成功获取 {df.shape[0]} 条记录")
                    
                else:
                    bar_samples["date_range_data"] = None
                    print(f"    :warning: 无数据")
                    
            except Exception as e:
                print(f"    :x: 失败: {e}")
                bar_samples["date_range_data"] = {"error": str(e)}
            
            # 保存bar样本数据
            output_file = self.output_dir / "tushare_bar_samples.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(bar_samples, f, indent=2, ensure_ascii=False)
            
            print(f":white_check_mark: Tushare bar样本已保存到: {output_file}")
            return bar_samples
            
        except Exception as e:
            print(f":x: Tushare bar数据收集失败: {e}")
            return {}
    
    def collect_tdx_bar_samples(self):
        """收集TDX bar数据样本（作为对比）"""
        print("\n:arrows_counterclockwise: 开始收集TDX bar数据样本...")
        
        try:
            tdx = GinkgoTDX()
            
            # 获取日K线数据
            start_date = self.bar_date_range[0]
            end_date = self.bar_date_range[-1]
            
            print(f"  :satellite_antenna: 获取 {self.test_code} 在 {start_date} 到 {end_date} 的TDX bar数据...")
            
            try:
                df = tdx.fetch_history_daybar(self.test_code, start_date, end_date)
                
                if df is not None and not df.empty:
                    # 转换为可序列化的格式
                    sample_data = {
                        "columns": list(df.columns),
                        "data": df.to_dict('records'),
                        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
                        "shape": df.shape,
                        "sample_values": {
                            col: list(df[col].head(5).astype(str)) 
                            for col in df.columns
                        }
                    }
                    
                    # 保存TDX bar样本数据
                    output_file = self.output_dir / "tdx_bar_samples.json"
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(sample_data, f, indent=2, ensure_ascii=False)
                    
                    print(f"    :white_check_mark: 成功获取 {df.shape[0]} 条记录")
                    print(f":white_check_mark: TDX bar样本已保存到: {output_file}")
                    return sample_data
                    
                else:
                    print(f"    :warning: 无数据")
                    return None
                    
            except Exception as e:
                print(f"    :x: 失败: {e}")
                return {"error": str(e)}
                
        except Exception as e:
            print(f":x: TDX bar数据收集失败: {e}")
            return {}
    
    def generate_mock_data_templates(self):
        """基于收集的样本生成Mock数据模板"""
        print("\n:arrows_counterclockwise: 生成Mock数据模板...")
        
        templates = {}
        
        # 读取tick样本
        tick_file = self.output_dir / "tdx_tick_samples.json"
        if tick_file.exists():
            with open(tick_file, 'r', encoding='utf-8') as f:
                tick_samples = json.load(f)
            
            templates["tick_template"] = self._create_tick_mock_template(tick_samples)
        
        # 读取bar样本
        bar_file = self.output_dir / "tushare_bar_samples.json"
        if bar_file.exists():
            with open(bar_file, 'r', encoding='utf-8') as f:
                bar_samples = json.load(f)
            
            templates["bar_template"] = self._create_bar_mock_template(bar_samples)
        
        # 保存模板
        template_file = self.output_dir / "mock_data_templates.json"
        with open(template_file, 'w', encoding='utf-8') as f:
            json.dump(templates, f, indent=2, ensure_ascii=False)
        
        print(f":white_check_mark: Mock数据模板已保存到: {template_file}")
        return templates
    
    def _create_tick_mock_template(self, tick_samples):
        """创建tick数据的Mock模板"""
        template = {
            "description": "基于真实TDX API格式的Tick Mock数据模板",
            "structure": {},
            "sample_data": {},
            "data_types": {}
        }
        
        # 从第一个有效样本提取结构
        for date_str, sample in tick_samples.items():
            if sample and not isinstance(sample, dict) or "error" not in sample:
                template["structure"] = sample.get("columns", [])
                template["data_types"] = sample.get("dtypes", {})
                template["sample_data"][date_str] = sample.get("data", [])[:3]  # 只保留3条样本
                break
        
        return template
    
    def _create_bar_mock_template(self, bar_samples):
        """创建bar数据的Mock模板"""
        template = {
            "description": "基于真实Tushare API格式的Bar Mock数据模板",
            "structure": {},
            "sample_data": {},
            "data_types": {}
        }
        
        # 从date_range_data提取结构
        if "date_range_data" in bar_samples and bar_samples["date_range_data"]:
            sample = bar_samples["date_range_data"]
            template["structure"] = sample.get("columns", [])
            template["data_types"] = sample.get("dtypes", {})
            template["sample_data"] = sample.get("data", [])[:5]  # 保留5条样本
        
        return template
    
    def run_collection(self):
        """运行完整的数据收集流程"""
        print(":rocket: 开始收集真实API数据样本...")
        print(f":file_folder: 输出目录: {self.output_dir}")
        print(f":dart: 测试股票: {self.test_code}")
        
        # 收集各种数据样本
        tick_samples = self.collect_tdx_tick_samples()
        bar_samples = self.collect_tushare_bar_samples()
        tdx_bar_samples = self.collect_tdx_bar_samples()
        
        # 生成Mock模板
        templates = self.generate_mock_data_templates()
        
        print("\n:clipboard: 收集摘要:")
        print(f"  TDX Tick样本: {len([k for k, v in tick_samples.items() if v and 'error' not in str(v)])} 个日期")
        print(f"  Tushare Bar样本: {':white_check_mark:' if bar_samples else ':x:'}")
        print(f"  TDX Bar样本: {':white_check_mark:' if tdx_bar_samples else ':x:'}")
        
        print(f"\n:party_popper: 数据收集完成！请查看 {self.output_dir} 目录下的文件")
        
        return {
            "tick_samples": tick_samples,
            "bar_samples": bar_samples,
            "tdx_bar_samples": tdx_bar_samples,
            "templates": templates
        }


if __name__ == "__main__":
    print("=" * 60)
    print("真实API数据样本收集器")
    print("=" * 60)
    
    collector = DataSampleCollector()
    
    try:
        results = collector.run_collection()
        print("\n:white_check_mark: 收集完成！可以开始基于真实格式构建Mock数据了。")
        
    except KeyboardInterrupt:
        print("\n⏹️ 用户中断")
    except Exception as e:
        print(f"\n:x: 收集过程中出现错误: {e}")
        import traceback
        traceback.print_exc()