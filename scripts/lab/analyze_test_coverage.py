#!/usr/bin/env python3
"""
测试覆盖分析工具
扫描所有测试文件，提取"测试覆盖源文件"标注，分析测试覆盖缺口
"""
import os
import re
from pathlib import Path
from typing import Set, List, Dict

def extract_coverage_from_test_file(file_path: str) -> List[str]:
    """从测试文件中提取覆盖的源文件列表"""
    covered_files = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 查找测试覆盖源文件标注
        coverage_pattern = r'测试覆盖源文件:\s*(.*?)"""'
        match = re.search(coverage_pattern, content, re.DOTALL)
        
        if match:
            coverage_content = match.group(1)
            # 提取每行中的源文件路径
            file_pattern = r'src/ginkgo/[^\s-]+\.py'
            files = re.findall(file_pattern, coverage_content)
            covered_files.extend(files)
            
    except Exception as e:
        print(f"读取文件失败 {file_path}: {e}")
        
    return covered_files

def get_all_source_files() -> Set[str]:
    """获取src/ginkgo下的所有.py源文件"""
    source_files = set()
    src_path = Path("src/ginkgo")
    
    for py_file in src_path.rglob("*.py"):
        # 排除__init__.py文件
        if py_file.name != "__init__.py":
            source_files.add(str(py_file))
    
    return source_files

def get_all_test_files() -> List[str]:
    """获取所有测试文件"""
    test_files = []
    test_path = Path("test")
    
    for py_file in test_path.rglob("test_*.py"):
        test_files.append(str(py_file))
    
    return sorted(test_files)

def analyze_coverage():
    """分析测试覆盖情况"""
    print("🔍 开始分析测试覆盖情况...")
    
    # 获取所有源文件
    all_sources = get_all_source_files()
    print(f"📂 发现 {len(all_sources)} 个源文件")
    
    # 获取所有测试文件
    all_tests = get_all_test_files()
    print(f"📋 发现 {len(all_tests)} 个测试文件")
    
    # 分析每个测试文件覆盖的源文件
    covered_files = set()
    test_coverage_map = {}
    
    print("\n🔎 分析测试文件覆盖标注...")
    for test_file in all_tests:
        covered = extract_coverage_from_test_file(test_file)
        if covered:
            test_coverage_map[test_file] = covered
            covered_files.update(covered)
        else:
            print(f"⚠️ 无覆盖标注: {test_file}")
    
    print(f"✅ 找到覆盖标注的测试文件: {len(test_coverage_map)} 个")
    print(f"📊 已被测试覆盖的源文件: {len(covered_files)} 个")
    
    # 找出未覆盖的源文件
    uncovered_files = all_sources - covered_files
    print(f"❌ 未被测试覆盖的源文件: {len(uncovered_files)} 个")
    
    # 按模块分类
    coverage_by_module = categorize_by_module(uncovered_files)
    
    # 生成报告
    generate_report(all_sources, covered_files, uncovered_files, coverage_by_module, test_coverage_map)

def categorize_by_module(files: Set[str]) -> Dict[str, List[str]]:
    """按模块分类文件"""
    categories = {
        "client": [],          # CLI工具
        "core": [],            # 核心架构
        "data": [],            # 数据层
        "features": [],        # 因子和特征
        "libs": [],            # 工具库
        "notifier": [],        # 通知模块
        "quant_ml": [],        # 机器学习
        "trading": [],         # 交易模块
        "config": [],          # 配置
        "other": []            # 其他
    }
    
    for file_path in files:
        # 移除src/ginkgo前缀
        relative_path = file_path.replace("src/ginkgo/", "")
        
        module = relative_path.split("/")[0]
        if module in categories:
            categories[module].append(file_path)
        else:
            categories["other"].append(file_path)
    
    # 移除空分类
    return {k: sorted(v) for k, v in categories.items() if v}

def prioritize_files(files: List[str]) -> Dict[str, List[str]]:
    """按重要性优先级分类文件"""
    high_priority = []     # 🔴 高优先级
    medium_priority = []   # 🟡 中优先级  
    low_priority = []      # 🟢 低优先级
    
    for file_path in files:
        path_lower = file_path.lower()
        
        # 高优先级：核心API和基础架构
        if any(keyword in path_lower for keyword in [
            "base_", "interface", "engine", "strategy", "risk", "portfolio", 
            "container", "factory", "adapter", "core_container", "service"
        ]):
            high_priority.append(file_path)
        
        # 低优先级：CLI和工具
        elif any(keyword in path_lower for keyword in [
            "cli", "notifier", "plot", "display", "utils", "tool"
        ]):
            low_priority.append(file_path)
        
        # 中优先级：其他业务组件
        else:
            medium_priority.append(file_path)
    
    return {
        "high": sorted(high_priority),
        "medium": sorted(medium_priority), 
        "low": sorted(low_priority)
    }

def generate_report(all_sources, covered_files, uncovered_files, coverage_by_module, test_coverage_map):
    """生成详细的覆盖分析报告"""
    
    print("\n" + "="*80)
    print("📊 GINKGO 测试覆盖分析报告")
    print("="*80)
    
    # 总体统计
    total_files = len(all_sources)
    covered_count = len(covered_files)
    uncovered_count = len(uncovered_files)
    coverage_rate = (covered_count / total_files) * 100
    
    print(f"\n📈 总体覆盖统计:")
    print(f"   总源文件数量: {total_files}")
    print(f"   已覆盖文件数量: {covered_count}")
    print(f"   未覆盖文件数量: {uncovered_count}")
    print(f"   测试覆盖率: {coverage_rate:.1f}%")
    
    # 按模块统计
    print(f"\n📂 按模块统计未覆盖文件:")
    for module, files in coverage_by_module.items():
        print(f"   {module}: {len(files)} 个文件")
    
    # 按优先级分类
    prioritized = prioritize_files(list(uncovered_files))
    
    print(f"\n🔥 按优先级分类未覆盖文件:")
    print(f"   🔴 高优先级: {len(prioritized['high'])} 个")
    print(f"   🟡 中优先级: {len(prioritized['medium'])} 个") 
    print(f"   🟢 低优先级: {len(prioritized['low'])} 个")
    
    # 详细列表
    print(f"\n" + "="*80)
    print("📋 详细的未覆盖文件清单")
    print("="*80)
    
    print(f"\n🔴 高优先级缺口 (核心API和基础架构):")
    for file_path in prioritized['high']:
        print(f"   - {file_path}")
    
    print(f"\n🟡 中优先级缺口 (关键业务组件):")
    for file_path in prioritized['medium']:
        print(f"   - {file_path}")
    
    print(f"\n🟢 低优先级缺口 (工具和辅助功能):")
    for file_path in prioritized['low']:
        print(f"   - {file_path}")
    
    # 测试建议
    print(f"\n" + "="*80)
    print("💡 测试补充建议")
    print("="*80)
    
    print(f"\n建议测试补充优先级：")
    print(f"1. 🔴 高优先级缺口应立即补充测试")
    print(f"2. 🟡 中优先级缺口根据业务重要性补充") 
    print(f"3. 🟢 低优先级缺口可在后续迭代中补充")
    
    print(f"\n重点关注模块：")
    for module, files in sorted(coverage_by_module.items(), key=lambda x: len(x[1]), reverse=True)[:5]:
        print(f"   - {module}: {len(files)} 个未覆盖文件")

if __name__ == "__main__":
    os.chdir("/home/kaoru/Ginkgo")
    analyze_coverage()