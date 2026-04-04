# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: Ast Helpers模块提供ASTHelpers AST辅助工具提供AST操作辅助函数支持代码分析功能支持回测评估和代码验证






"""
AST helper utilities for static code analysis.

Provides utility functions for parsing Python source code into AST
and extracting common patterns (classes, methods, decorators, etc.).
"""

import ast
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Type, TypeVar, Union


def parse_file(file_path: Path) -> Optional[ast.Module]:
    """
    Parse a Python file into an AST tree.

    Args:
        file_path: Path to the Python file

    Returns:
        Parsed AST tree, or None if parsing fails

    Raises:
        SyntaxError: If the file has invalid syntax
        FileNotFoundError: If the file doesn't exist
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source_code = f.read()
        return ast.parse(source_code, filename=str(file_path))
    except SyntaxError as e:
        raise SyntaxError(f"Syntax error in {file_path}: {e.msg} at line {e.lineno}")


def parse_source(source_code: str, filename: str = "<string>") -> ast.Module:
    """
    Parse source code string into an AST tree.

    Args:
        source_code: Python source code as string
        filename: Optional filename for error messages

    Returns:
        Parsed AST tree

    Raises:
        SyntaxError: If the source has invalid syntax
    """
    return ast.parse(source_code, filename=filename)


def find_class_def(
    tree: ast.Module, class_name: str
) -> Optional[ast.ClassDef]:
    """
    Find a class definition by name in the AST tree.

    Args:
        tree: The AST tree to search
        class_name: Name of the class to find

    Returns:
        ClassDef node if found, None otherwise
    """
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return node
    return None


def find_all_class_defs(tree: ast.Module) -> List[ast.ClassDef]:
    """
    Find all class definitions in the AST tree.

    Args:
        tree: The AST tree to search

    Returns:
        List of all ClassDef nodes
    """
    return [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]


def find_method_def(
    class_node: ast.ClassDef, method_name: str
) -> Optional[ast.FunctionDef]:
    """
    Find a method definition by name in a class.

    Args:
        class_node: The ClassDef node to search
        method_name: Name of the method to find

    Returns:
        FunctionDef node if found, None otherwise
    """
    for node in class_node.body:
        if isinstance(node, ast.FunctionDef) and node.name == method_name:
            return node
    return None


def find_all_method_defs(class_node: ast.ClassDef) -> List[ast.FunctionDef]:
    """
    Find all method definitions in a class.

    Args:
        class_node: The ClassDef node to search

    Returns:
        List of all FunctionDef nodes in the class
    """
    return [
        node
        for node in class_node.body
        if isinstance(node, ast.FunctionDef)
    ]


def get_base_classes(class_node: ast.ClassDef) -> List[str]:
    """
    Get the base class names for a class.

    Args:
        class_node: The ClassDef node

    Returns:
        List of base class names
    """
    bases = []
    for base in class_node.bases:
        if isinstance(base, ast.Name):
            bases.append(base.id)
        elif isinstance(base, ast.Attribute):
            # Handle cases like 'module.ClassName'
            bases.append(ast.unparse(base))
    return bases


def inherits_from(class_node: ast.ClassDef, base_class_name: str) -> bool:
    """
    Check if a class inherits from a specific base class.

    Args:
        class_node: The ClassDef node
        base_class_name: Name of the base class to check

    Returns:
        True if the class inherits from base_class_name
    """
    return base_class_name in get_base_classes(class_node)


def get_function_signature(
    func_node: ast.FunctionDef
) -> Dict[str, Any]:
    """
    Extract function signature information.

    Args:
        func_node: The FunctionDef node

    Returns:
        Dictionary with signature information:
        - name: Function name
        - args: List of argument names
        - returns: Return annotation (if any)
        - decorators: List of decorator names
    """
    args_info = []
    for arg in func_node.args.args:
        arg_info = {"name": arg.arg, "annotation": None}
        if arg.annotation:
            arg_info["annotation"] = ast.unparse(arg.annotation)
        args_info.append(arg_info)

    # Check for variadic args
    if func_node.args.vararg:
        args_info.append({
            "name": f"*{func_node.args.vararg.arg}",
            "annotation": ast.unparse(func_node.args.vararg.annotation) if func_node.args.vararg.annotation else None,
        })

    # Check for keyword args
    if func_node.args.kwarg:
        args_info.append({
            "name": f"**{func_node.args.kwarg.arg}",
            "annotation": ast.unparse(func_node.args.kwarg.annotation) if func_node.args.kwarg.annotation else None,
        })

    return {
        "name": func_node.name,
        "args": args_info,
        "returns": ast.unparse(func_node.returns) if func_node.returns else None,
        "decorators": [
            _extract_decorator_name(d) for d in func_node.decorator_list
        ],
    }


def _extract_decorator_node(
    decorator: ast.expr
) -> Optional[Union[ast.Name, ast.Attribute, ast.Call]]:
    """
    Extract the actual decorator node from potentially nested structures.

    Args:
        decorator: The decorator expression

    Returns:
        The core decorator node (Name, Attribute, or Call)
    """
    if isinstance(decorator, (ast.Name, ast.Attribute, ast.Call)):
        return decorator
    return None


def _extract_decorator_name(decorator: ast.expr) -> str:
    """
    Extract decorator name as string.

    Args:
        decorator: The decorator node

    Returns:
        Decorator name as string
    """
    if isinstance(decorator, ast.Name):
        return decorator.id
    elif isinstance(decorator, ast.Attribute):
        return ast.unparse(decorator)
    elif isinstance(decorator, ast.Call):
        return _extract_decorator_name(decorator.func)
    return ast.unparse(decorator)


def get_decorators(
    node: Union[ast.FunctionDef, ast.ClassDef]
) -> List[str]:
    """
    Get all decorator names for a function or class.

    Args:
        node: The FunctionDef or ClassDef node

    Returns:
        List of decorator names
    """
    return [
        _extract_decorator_name(d) for d in node.decorator_list
    ]


def has_decorator(
    node: Union[ast.FunctionDef, ast.ClassDef],
    decorator_name: str,
) -> bool:
    """
    Check if a function or class has a specific decorator.

    Args:
        node: The FunctionDef or ClassDef node
        decorator_name: Decorator name to check

    Returns:
        True if the node has the decorator
    """
    decorators = get_decorators(node)
    return decorator_name in decorators


def get_method_calls(
    func_node: ast.FunctionDef
) -> List[Dict[str, Any]]:
    """
    Extract all method/function calls within a function.

    Args:
        func_node: The FunctionDef node

    Returns:
        List of call information dictionaries:
        - name: Call name (e.g., 'self.get_time_provider')
        - line: Line number
    """
    calls = []

    for node in ast.walk(func_node):
        if isinstance(node, ast.Call):
            call_info = {
                "name": ast.unparse(node.func),
                "line": node.lineno,
            }
            calls.append(call_info)

    return calls


def has_call(func_node: ast.FunctionDef, func_name: str) -> bool:
    """
    Check if a function contains a call to a specific function.

    Args:
        func_node: The FunctionDef node
        func_name: Function name to check (e.g., 'self.get_time_provider')

    Returns:
        True if the function contains a call to func_name
    """
    calls = get_method_calls(func_node)
    return any(func_name in call["name"] for call in calls)


def find_super_calls(
    func_node: ast.FunctionDef
) -> List[ast.Call]:
    """
    Find all super() calls in a function.

    Args:
        func_node: The FunctionDef node

    Returns:
        List of Call nodes that are super() calls
    """
    super_calls = []

    for node in ast.walk(func_node):
        if isinstance(node, ast.Call):
            # Check if it's a super() call
            if isinstance(node.func, ast.Name) and node.func.id == "super":
                super_calls.append(node)

    return super_calls


def has_super_call(func_node: ast.FunctionDef) -> bool:
    """
    Check if a function contains a super() call.

    Args:
        func_node: The FunctionDef node

    Returns:
        True if the function contains a super() call
    """
    return len(find_super_calls(func_node)) > 0


def find_return_statements(
    func_node: ast.FunctionDef
) -> List[ast.Return]:
    """
    Find all return statements in a function.

    Args:
        func_node: The FunctionDef node

    Returns:
        List of Return nodes
    """
    returns = []

    for node in ast.walk(func_node):
        if isinstance(node, ast.Return):
            returns.append(node)

    return returns


def get_class_variables(class_node: ast.ClassDef) -> Dict[str, Optional[str]]:
    """
    Extract class-level variable assignments.

    Args:
        class_node: The ClassDef node

    Returns:
        Dictionary mapping variable names to their values (as strings)
    """
    variables = {}

    for node in class_node.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    variables[target.id] = ast.unparse(node.value) if node.value else None

    return variables


def has_abstract_marker(class_node: ast.ClassDef) -> bool:
    """
    Check if a class has __abstract__ = False marker.

    This is a Ginkgo-specific pattern for marking concrete strategy classes.

    Args:
        class_node: The ClassDef node

    Returns:
        True if the class has __abstract__ = False
    """
    variables = get_class_variables(class_node)
    return variables.get("__abstract__") == "False"


def get_source_segment(
    source_code: str,
    node: ast.AST,
    padding: int = 0,
) -> str:
    """
    Extract source code segment for an AST node.

    Args:
        source_code: Full source code
        node: AST node
        padding: Number of surrounding lines to include

    Returns:
        Source code segment
    """
    lines = source_code.splitlines()

    if not hasattr(node, "lineno") or node.lineno is None:
        return ""

    start_line = max(0, node.lineno - 1 - padding)
    end_line = min(len(lines), node.end_lineno + padding) if node.end_lineno else node.lineno + padding

    return "\n".join(lines[start_line:end_line])


def get_imports(tree: ast.Module) -> Dict[str, List[str]]:
    """
    Extract all imports from an AST tree.

    Args:
        tree: The AST tree

    Returns:
        Dictionary with 'module' and 'from' imports:
        {
            'module': ['os', 'sys'],  # import os, sys
            'from': {                   # from x import y
                'ginkgo': ['BaseStrategy', 'Signal'],
                ...
            }
        }
    """
    imports: Dict[str, Any] = {
        "module": [],
        "from": {},
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports["module"].append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module if node.module else ""
            if module not in imports["from"]:
                imports["from"][module] = []
            for alias in node.names:
                imports["from"][module].append(alias.name)

    return imports


def is_abstract_class(class_node: ast.ClassDef) -> bool:
    """
    Check if a class appears to be abstract (has abstract methods).

    Args:
        class_node: The ClassDef node

    Returns:
        True if the class appears to be abstract
    """
    # Check for ABC inheritance
    bases = get_base_classes(class_node)
    if any("ABC" in base or "abc.ABC" in base for base in bases):
        return True

    # Check for abstractmethod decorators
    for method in find_all_method_defs(class_node):
        decorators = get_decorators(method)
        if any("abstractmethod" in dec for dec in decorators):
            return True

    # Check for __abstract__ = True (Ginkgo pattern)
    variables = get_class_variables(class_node)
    if variables.get("__abstract__") == "True":
        return True

    return False
