"""
AST analyzer for static code analysis of strategy classes.

Provides high-level analysis functions for extracting class structure,
methods, decorators, and other code patterns from Python source files.
"""

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

from ginkgo.libs import GLOG
from ginkgo.trading.evaluation.utils.ast_helpers import (
    find_all_class_defs,
    find_all_method_defs,
    find_method_def,
    get_base_classes,
    get_class_variables,
    get_decorators,
    get_function_signature,
    get_imports,
    inherits_from,
    parse_file,
)


@dataclass
class ClassInfo:
    """
    Information about a class extracted from AST.

    Attributes:
        name: Class name
        lineno: Line number where class is defined
        end_lineno: Ending line number
        bases: List of base class names
        methods: Dictionary of method_name -> MethodInfo
        variables: Dictionary of variable_name -> value
        decorators: List of decorator names
        is_abstract: Whether the class appears to be abstract
        docstring: Class docstring (if any)
    """

    name: str
    lineno: int
    end_lineno: Optional[int]
    bases: List[str] = field(default_factory=list)
    methods: Dict[str, "MethodInfo"] = field(default_factory=dict)
    variables: Dict[str, str] = field(default_factory=dict)
    decorators: List[str] = field(default_factory=list)
    is_abstract: bool = False
    docstring: Optional[str] = None


@dataclass
class MethodInfo:
    """
    Information about a method extracted from AST.

    Attributes:
        name: Method name
        lineno: Line number where method is defined
        end_lineno: Ending line number
        args: List of argument information dicts
        returns: Return type annotation (if any)
        decorators: List of decorator names
        is_async: Whether this is an async method
        docstring: Method docstring (if any)
    """

    name: str
    lineno: int
    end_lineno: Optional[int]
    args: List[Dict[str, Any]] = field(default_factory=list)
    returns: Optional[str] = None
    decorators: List[str] = field(default_factory=list)
    is_async: bool = False
    docstring: Optional[str] = None


@dataclass
class FileAnalysis:
    """
    Complete analysis of a Python source file.

    Attributes:
        file_path: Path to the analyzed file
        imports: Dictionary of import information
        classes: Dictionary of class_name -> ClassInfo
        has_syntax_error: Whether the file has syntax errors
        syntax_error_message: Error message if syntax error exists
    """

    file_path: Path
    imports: Dict[str, Any] = field(default_factory=dict)
    classes: Dict[str, ClassInfo] = field(default_factory=dict)
    has_syntax_error: bool = False
    syntax_error_message: Optional[str] = None


class ASTAnalyzer:
    """
    Analyzer for extracting structured information from Python AST.

    Provides high-level methods for analyzing Python source code
    and extracting class structures, method signatures, decorators, etc.
    """

    def __init__(self, enable_caching: bool = True):
        """
        Initialize the AST analyzer.

        Args:
            enable_caching: Whether to cache parse results
        """
        self.enable_caching = enable_caching
        self._cache: Dict[Path, FileAnalysis] = {}

    def analyze_file(self, file_path: Path) -> FileAnalysis:
        """
        Analyze a Python file and extract structured information.

        Args:
            file_path: Path to the Python file

        Returns:
            FileAnalysis with complete file information
        """
        # Check cache first
        if self.enable_caching and file_path in self._cache:
            return self._cache[file_path]

        analysis = FileAnalysis(file_path=file_path)

        try:
            # Parse the file
            tree = parse_file(file_path)

            # Extract imports
            analysis.imports = get_imports(tree)

            # Extract class information
            for class_node in find_all_class_defs(tree):
                class_info = self._analyze_class(class_node)
                analysis.classes[class_info.name] = class_info

        except SyntaxError as e:
            analysis.has_syntax_error = True
            analysis.syntax_error_message = str(e)
            GLOG.WARN(f"Syntax error in {file_path}: {e}")

        except Exception as e:
            GLOG.ERROR(f"Error analyzing {file_path}: {e}")

        # Cache the result
        if self.enable_caching:
            self._cache[file_path] = analysis

        return analysis

    def _analyze_class(self, class_node: ast.ClassDef) -> ClassInfo:
        """
        Analyze a class definition node.

        Args:
            class_node: The ClassDef AST node

        Returns:
            ClassInfo with complete class information
        """
        # Extract basic information
        class_info = ClassInfo(
            name=class_node.name,
            lineno=class_node.lineno,
            end_lineno=class_node.end_lineno,
            bases=get_base_classes(class_node),
            decorators=get_decorators(class_node),
            docstring=ast.get_docstring(class_node),
        )

        # Extract class variables
        class_info.variables = get_class_variables(class_node)

        # Determine if abstract
        class_info.is_abstract = self._is_abstract_class(class_node)

        # Extract methods
        for method_node in find_all_method_defs(class_node):
            method_info = self._analyze_method(method_node)
            class_info.methods[method_info.name] = method_info

        return class_info

    def _analyze_method(self, method_node: ast.FunctionDef) -> MethodInfo:
        """
        Analyze a method definition node.

        Args:
            method_node: The FunctionDef AST node

        Returns:
            MethodInfo with complete method information
        """
        sig = get_function_signature(method_node)

        return MethodInfo(
            name=method_node.name,
            lineno=method_node.lineno,
            end_lineno=method_node.end_lineno,
            args=sig["args"],
            returns=sig["returns"],
            decorators=sig["decorators"],
            is_async=isinstance(method_node, ast.AsyncFunctionDef),
            docstring=ast.get_docstring(method_node),
        )

    def _is_abstract_class(self, class_node: ast.ClassDef) -> bool:
        """
        Check if a class appears to be abstract.

        Args:
            class_node: The ClassDef node

        Returns:
            True if the class appears to be abstract
        """
        # Check for ABC inheritance
        for base in class_node.bases:
            if isinstance(base, ast.Name) and "ABC" in base.id:
                return True
            elif isinstance(base, ast.Attribute) and "ABC" in base.attr:
                return True

        # Check for abstractmethod decorators
        for item in class_node.body:
            if isinstance(item, ast.FunctionDef):
                for decorator in item.decorator_list:
                    if isinstance(decorator, ast.Name) and "abstractmethod" in decorator.id:
                        return True
                    elif isinstance(decorator, ast.Attribute) and "abstractmethod" in decorator.attr:
                        return True

        # Check for __abstract__ = True (Ginkgo pattern)
        for item in class_node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name) and target.id == "__abstract__":
                        if isinstance(item.value, (ast.Name, ast.Constant)):
                            value = None
                            if isinstance(item.value, ast.Name):
                                value = item.value.id
                            elif isinstance(item.value, ast.Constant):
                                value = item.value.value

                            if value is True or value == "True":
                                return True

        return False

    def find_strategy_classes(self, analysis: FileAnalysis) -> List[ClassInfo]:
        """
        Find all classes that inherit from BaseStrategy.

        Args:
            analysis: The file analysis result

        Returns:
            List of ClassInfo for strategy classes
        """
        strategies = []
        for class_info in analysis.classes.values():
            if "BaseStrategy" in class_info.bases:
                strategies.append(class_info)
        return strategies

    def get_method_by_name(
        self, class_info: ClassInfo, method_name: str
    ) -> Optional[MethodInfo]:
        """
        Get a method from a class by name.

        Args:
            class_info: The class information
            method_name: Name of the method to find

        Returns:
            MethodInfo if found, None otherwise
        """
        return class_info.methods.get(method_name)

    def has_method(self, class_info: ClassInfo, method_name: str) -> bool:
        """
        Check if a class has a specific method.

        Args:
            class_info: The class information
            method_name: Name of the method to check

        Returns:
            True if the class has the method
        """
        return method_name in class_info.methods

    def has_decorator(
        self, class_or_method: Union[ClassInfo, MethodInfo], decorator_name: str
    ) -> bool:
        """
        Check if a class or method has a specific decorator.

        Args:
            class_or_method: ClassInfo or MethodInfo to check
            decorator_name: Decorator name to look for

        Returns:
            True if the decorator is present
        """
        return decorator_name in class_or_method.decorators

    def clear_cache(self) -> None:
        """Clear the analysis cache."""
        self._cache.clear()

    def get_cache_size(self) -> int:
        """Get the number of cached analyses."""
        return len(self._cache)


def analyze_strategy_file(file_path: Path) -> Optional[ClassInfo]:
    """
    Convenience function to analyze a strategy file and get the strategy class.

    Args:
        file_path: Path to the strategy file

    Returns:
        ClassInfo of the first strategy class found, or None
    """
    analyzer = ASTAnalyzer()
    analysis = analyzer.analyze_file(file_path)

    if analysis.has_syntax_error:
        return None

    strategies = analyzer.find_strategy_classes(analysis)
    if strategies:
        return strategies[0]

    return None


def extract_class_structure(file_path: Path, class_name: str) -> Optional[Dict[str, Any]]:
    """
    Extract complete structure information for a specific class.

    Args:
        file_path: Path to the Python file
        class_name: Name of the class to extract

    Returns:
        Dictionary with class structure, or None if not found
    """
    analyzer = ASTAnalyzer()
    analysis = analyzer.analyze_file(file_path)

    if class_name not in analysis.classes:
        return None

    class_info = analysis.classes[class_name]

    return {
        "name": class_info.name,
        "lineno": class_info.lineno,
        "bases": class_info.bases,
        "is_abstract": class_info.is_abstract,
        "decorators": class_info.decorators,
        "variables": class_info.variables,
        "methods": {
            name: {
                "lineno": info.lineno,
                "args": info.args,
                "returns": info.returns,
                "decorators": info.decorators,
                "is_async": info.is_async,
            }
            for name, info in class_info.methods.items()
        },
    }
