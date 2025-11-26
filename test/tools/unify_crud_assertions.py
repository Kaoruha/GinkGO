#!/usr/bin/env python3
"""
CRUD测试统一化脚本 - 统一插入和删除测试的计数断言模式

目标：将所有CRUD测试中的插入/删除测试修改为通过比对操作前后的数据条数来断言
模式：
- 插入测试：获取操作前count -> 执行插入 -> 获取操作后count -> 断言count增加
- 删除测试：获取操作前count -> 执行删除 -> 获取操作后count -> 断言count减少
"""

import os
import re
import glob
from pathlib import Path
from typing import List, Tuple, Dict

class CRUDAssertionUnifier:
    def __init__(self, test_dir: str = "test/data/crud/"):
        self.test_dir = Path(test_dir)
        self.modified_files = []
        self.skipped_files = []

    def find_crud_test_files(self) -> List[Path]:
        """查找所有CRUD测试文件"""
        pattern = str(self.test_dir / "test_*_crud.py")
        return list(glob.glob(pattern))

    def analyze_file(self, file_path: Path) -> Dict[str, List]:
        """分析文件中的测试方法，识别需要修改的插入和删除测试"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 需要修改的模式
        insert_patterns = [
            r'def test_add.*\([\s\S]*?crud\..*create.*\([\s\S]*?assert',
            r'def test_insert.*\([\s\S]*?crud\..*insert.*\([\s\S]*?assert',
        ]

        delete_patterns = [
            r'def test_delete.*\([\s\S]*?crud\..*delete.*\([\s\S]*?assert',
            r'def test_remove.*\([\s\S]*?crud\..*remove.*\([\s\S]*?assert',
        ]

        # 检查是否已经使用了count模式
        count_pattern = r'crud\.count\(\)'

        methods_to_modify = {
            'insert': [],
            'delete': []
        }

        # 查找所有测试方法
        test_methods = re.finditer(r'(def test_.*?\([\s\S]*?)(?=def|\Z)', content, re.MULTILINE)

        for method_match in test_methods:
            method_content = method_match.group(1)
            method_name = method_match.group(1).split('(')[0].replace('def ', '')

            # 检查是否是插入或删除测试
            is_insert = any(keyword in method_name.lower() for keyword in ['add', 'insert'])
            is_delete = any(keyword in method_name.lower() for keyword in ['delete', 'remove'])

            # 检查是否已经使用了count模式
            has_count = bool(re.search(count_pattern, method_content))

            # 检查是否包含CRUD操作
            has_crud_operation = bool(re.search(r'crud\..*create|crud\..*insert|crud\..*delete|crud\..*remove', method_content))

            if is_insert and has_crud_operation and not has_count:
                methods_to_modify['insert'].append(method_name)
            elif is_delete and has_crud_operation and not has_count:
                methods_to_modify['delete'].append(method_name)

        return methods_to_modify

    def generate_count_assertion_code(self, operation: str, crud_var: str = 'crud') -> str:
        """生成计数断言代码模板"""
        if operation == 'insert':
            return f'''
            # 获取插入前的总记录数
            pre_insert_count = {crud_var}.count()
            print(f"→ 插入前总记录数: {{pre_insert_count}}")

            # 执行插入操作（此处的插入代码保持不变）

            # 验证插入后的总记录数增加
            post_insert_count = {crud_var}.count()
            assert post_insert_count > pre_insert_count, f"插入后总记录数应该增加，之前{{pre_insert_count}}条，现在{{post_insert_count}}条"
            print(f"✓ 插入后总记录数: {{post_insert_count}} (增加 {{post_insert_count - pre_insert_count}} 条)")
            '''
        elif operation == 'delete':
            return f'''
            # 获取删除前的总记录数
            pre_delete_count = {crud_var}.count()
            print(f"→ 删除前总记录数: {{pre_delete_count}}")

            # 执行删除操作（此处的删除代码保持不变）

            # 验证删除后的总记录数减少
            post_delete_count = {crud_var}.count()
            assert post_delete_count < pre_delete_count, f"删除后总记录数应该减少，之前{{pre_delete_count}}条，现在{{post_delete_count}}条"
            print(f"✓ 删除后总记录数: {{post_delete_count}} (减少 {{pre_delete_count - post_delete_count}} 条)")
            '''
        return ""

    def modify_method(self, method_content: str, operation: str) -> str:
        """修改单个测试方法的断言逻辑"""
        # 查找crud变量名（可能是crud、bar_crud、order_crud等）
        crud_var_match = re.search(r'(\w+_crud|crud)\.count?\(\)', method_content)
        crud_var = crud_var_match.group(1) if crud_var_match else 'crud'

        # 生成新的计数断言代码
        count_assertion = self.generate_count_assertion_code(operation, crud_var)

        # 修改策略：在方法开头添加pre-count，在assert之前添加post-count断言
        lines = method_content.split('\n')
        new_lines = []
        i = 0

        while i < len(lines):
            line = lines[i]

            # 在测试方法的第一行添加pre-count
            if i == 1:  # 跳过方法定义行
                # 找到第一个实际代码行（不是注释或空行）
                j = i
                while j < len(lines) and (lines[j].strip().startswith('#') or lines[j].strip() == '' or 'def ' in lines[j]):
                    new_lines.append(lines[j])
                    j += 1

                if j < len(lines):
                    # 在第一个实际代码行之前插入pre-count
                    indent = len(lines[j]) - len(lines[j].lstrip())
                    pre_count_code = f"{' ' * indent}# 获取{operation}前的总记录数"
                    new_lines.append(pre_count_code)
                    new_lines.append(f"{' ' * indent}pre_{operation}_count = {crud_var}.count()")
                    new_lines.append(f"{' ' * indent}print(f\"→ {operation}前总记录数: {{pre_{operation}_count}}\")")
                    new_lines.append('')
                    i = j - 1  # 回退以便重新处理当前行
                else:
                    new_lines.append(line)

            # 查找assert语句，在其前面插入post-count断言
            elif line.strip().startswith('assert'):
                indent = len(line) - len(line.lstrip())

                # 移除旧的验证代码（通常是查询数据库验证）
                # 查找并移除以assert开头的旧验证代码
                old_assertions = []
                assert_start = i
                while i < len(lines) and (lines[i].strip().startswith('assert') or
                                         lines[i].strip().startswith('result =') or
                                         lines[i].strip().startswith('deleted_count =') or
                                         'crud.get' in lines[i] or
                                         lines[i].strip() == '' or
                                         lines[i].strip().startswith('#')):
                    old_assertions.append(lines[i])
                    i += 1

                # 插入新的计数断言
                new_lines.append(f"{' ' * indent}# 验证{operation}后的总记录数")
                if operation == 'insert':
                    new_lines.append(f"{' ' * indent}post_{operation}_count = {crud_var}.count()")
                    new_lines.append(f"{' ' * indent}assert post_{operation}_count > pre_{operation}_count, "
                                   f"f\"{operation}后总记录数应该增加，之前{{pre_{operation}_count}}条，现在{{post_{operation}_count}}条\"")
                    new_lines.append(f"{' ' * indent}print(f\"✓ {operation}后总记录数: {{post_{operation}_count}} "
                                   f"(增加 {{post_{operation}_count - pre_{operation}_count}} 条)\")")
                else:  # delete
                    new_lines.append(f"{' ' * indent}post_{operation}_count = {crud_var}.count()")
                    new_lines.append(f"{' ' * indent}assert post_{operation}_count < pre_{operation}_count, "
                                   f"f\"{operation}后总记录数应该减少，之前{{pre_{operation}_count}}条，现在{{post_{operation}_count}}条\"")
                    new_lines.append(f"{' ' * indent}print(f\"✓ {operation}后总记录数: {{post_{operation}_count}} "
                                   f"(减少 {{pre_{operation}_count - post_{operation}_count}} 条)\")")

                i -= 1  # 回退一步
            else:
                new_lines.append(line)

            i += 1

        return '\n'.join(new_lines)

    def modify_file(self, file_path: Path) -> bool:
        """修改单个文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 分析文件
            methods_to_modify = self.analyze_file(file_path)

            if not methods_to_modify['insert'] and not methods_to_modify['delete']:
                print(f"  ✓ 文件 {file_path.name} 已经使用了正确的计数断言模式")
                self.skipped_files.append(file_path.name)
                return False

            print(f"  📝 修改文件: {file_path.name}")
            print(f"    - 需要修改的插入测试: {len(methods_to_modify['insert'])}个")
            print(f"    - 需要修改的删除测试: {len(methods_to_modify['delete'])}个")

            # 修改内容
            new_content = content

            # 这里应该实现具体的方法修改逻辑
            # 由于复杂度较高，我们先标记需要手动修改的文件
            print(f"    ⚠️  需要手动修改的方法:")
            for method in methods_to_modify['insert']:
                print(f"      - {method} (插入测试)")
            for method in methods_to_modify['delete']:
                print(f"      - {method} (删除测试)")

            self.modified_files.append(file_path.name)
            return True

        except Exception as e:
            print(f"  ❌ 修改文件 {file_path.name} 时出错: {e}")
            return False

    def create_manual_fix_guide(self, file_path: Path, methods_to_modify: Dict[str, List[str]]):
        """为每个需要修改的文件创建手动修复指南"""
        guide_file = file_path.parent / f"{file_path.stem}_fix_guide.md"

        with open(guide_file, 'w', encoding='utf-8') as f:
            f.write(f"# {file_path.name} 修复指南\n\n")
            f.write("## 需要修改的测试方法\n\n")

            if methods_to_modify['insert']:
                f.write("### 插入测试修改\n\n")
                f.write("需要将以下方法修改为使用计数断言模式：\n\n")
                for method in methods_to_modify['insert']:
                    f.write(f"- `{method}`\n")

                f.write("\n#### 修改模式示例:\n\n")
                f.write("```python\n")
                f.write("# 在方法开头添加:\n")
                f.write("pre_insert_count = crud.count()\n")
                f.write("print(f\"→ 插入前总记录数: {pre_insert_count}\")\n")
                f.write("\n")
                f.write("# 在原有的assert之前添加:\n")
                f.write("post_insert_count = crud.count()\n")
                f.write("assert post_insert_count > pre_insert_count, \\\n")
                f.write("    f\"插入后总记录数应该增加，之前{pre_insert_count}条，现在{post_insert_count}条\"\n")
                f.write("print(f\"✓ 插入后总记录数: {post_insert_count} (增加 {post_insert_count - pre_insert_count} 条)\")\n")
                f.write("```\n\n")

            if methods_to_modify['delete']:
                f.write("### 删除测试修改\n\n")
                f.write("需要将以下方法修改为使用计数断言模式：\n\n")
                for method in methods_to_modify['delete']:
                    f.write(f"- `{method}`\n")

                f.write("\n#### 修改模式示例:\n\n")
                f.write("```python\n")
                f.write("# 在方法开头添加:\n")
                f.write("pre_delete_count = crud.count()\n")
                f.write("print(f\"→ 删除前总记录数: {pre_delete_count}\")\n")
                f.write("\n")
                f.write("# 在原有的assert之前添加:\n")
                f.write("post_delete_count = crud.count()\n")
                f.write("assert post_delete_count < pre_delete_count, \\\n")
                f.write("    f\"删除后总记录数应该减少，之前{pre_delete_count}条，现在{post_delete_count}条\"\n")
                f.write("print(f\"✓ 删除后总记录数: {post_delete_count} (减少 {pre_delete_count - post_delete_count} 条)\")\n")
                f.write("```\n\n")

    def run_analysis(self):
        """运行分析并生成修复指南"""
        print("🔍 开始分析CRUD测试文件...")

        files = self.find_crud_test_files()
        print(f"  找到 {len(files)} 个CRUD测试文件\n")

        for file_path in files:
            print(f"📁 分析文件: {file_path.name}")

            methods_to_modify = self.analyze_file(Path(file_path))

            if methods_to_modify['insert'] or methods_to_modify['delete']:
                print(f"  📝 发现需要修改的方法:")
                if methods_to_modify['insert']:
                    print(f"    - 插入测试: {len(methods_to_modify['insert'])}个")
                if methods_to_modify['delete']:
                    print(f"    - 删除测试: {len(methods_to_modify['delete'])}个")

                # 创建修复指南
                self.create_manual_fix_guide(Path(file_path), methods_to_modify)
                print(f"  📋 已生成修复指南: {file_path.stem}_fix_guide.md")
                self.modified_files.append(file_path.name)
            else:
                print(f"  ✅ 文件已经使用正确的计数断言模式")
                self.skipped_files.append(file_path.name)

            print()

        print("📊 分析总结:")
        print(f"  - 总文件数: {len(files)}")
        print(f"  - 需要修改的文件: {len(self.modified_files)}")
        print(f"  - 已符合要求的文件: {len(self.skipped_files)}")

        if self.modified_files:
            print(f"\n📋 需要修改的文件列表:")
            for file_name in self.modified_files:
                print(f"  - {file_name}")

            print(f"\n🔧 请按照生成的修复指南逐一修改这些文件")


def main():
    """主函数"""
    unifier = CRUDAssertionUnifier()
    unifier.run_analysis()


if __name__ == "__main__":
    main()