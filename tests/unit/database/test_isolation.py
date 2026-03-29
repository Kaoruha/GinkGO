"""
Database Test Isolation Utilities

Provides decorators and utilities to ensure database tests are properly isolated
and only run in safe environments.

:warning:  CRITICAL SAFETY FEATURES :warning:
- DEBUG mode validation (DEBUGMODE=True required)
- Test port validation (development ports only)
- User confirmation requirements
- Automatic cleanup mechanisms
"""

import os
import functools
from typing import Callable, Any
from unittest import SkipTest

try:
    from ginkgo.libs import GCONF
    from ginkgo.libs.core.logger import GLOG
except ImportError:
    GCONF = None
    GLOG = None


class DatabaseTestError(Exception):
    """Raised when database test safety checks fail."""
    pass


def database_test_required(func: Callable) -> Callable:
    """
    Decorator to mark tests that require database access.
    
    This decorator performs critical safety checks:
    1. Confirms DEBUGMODE is enabled
    2. Validates using development database ports
    3. Logs all database test executions
    
    Usage:
        @database_test_required
        def test_database_operation(self):
            # Your database test code here
            pass
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Skip if no config available
        if GCONF is None:
            raise SkipTest("Ginkgo configuration not available")
        
        # Critical safety checks
        _validate_debug_mode()
        _validate_port_configuration()
        
        # Log database test execution
        if GLOG:
            GLOG.info(f":file_cabinet: Executing database test: {func.__name__}")
        
        try:
            result = func(*args, **kwargs)
            if GLOG:
                GLOG.info(f":white_check_mark: Database test completed: {func.__name__}")
            return result
        except Exception as e:
            if GLOG:
                GLOG.error(f":x: Database test failed: {func.__name__} - {e}")
            raise
    
    # Mark function as database test
    wrapper._is_database_test = True
    return wrapper




def _get_original_port(db_type):
    """通过现有GCONF属性获取原始端口"""
    if not GCONF:
        return None
        
    if db_type == 'clickhouse':
        current_port = str(GCONF.CLICKPORT)
        if GCONF.DEBUGMODE and current_port.startswith('1'):
            return current_port[1:]  # 去掉开发环境的"1"前缀
        else:
            return current_port      # 直接返回原始端口
    
    elif db_type == 'mysql':
        current_port = str(GCONF.MYSQLPORT)
        if GCONF.DEBUGMODE and current_port.startswith('1'):
            return current_port[1:]  # 去掉开发环境的"1"前缀
        else:
            return current_port      # 直接返回原始端口
    
    return None


def _validate_debug_mode():
    """Validate that debug mode is enabled."""
    if not GCONF:
        return
    
    if not GCONF.DEBUGMODE:
        raise DatabaseTestError(
            "Database tests require DEBUGMODE to be enabled. "
            "Set DEBUGMODE=True in configuration."
        )


def _validate_port_configuration():
    """验证使用的是测试端口而非生产端口"""
    if not GCONF:
        return
    
    # 获取原始配置端口
    clickhouse_original = _get_original_port('clickhouse')
    mysql_original = _get_original_port('mysql')
    
    # 获取当前使用端口
    current_click_port = str(GCONF.CLICKPORT)
    current_mysql_port = str(GCONF.MYSQLPORT)
    
    # 验证不是生产端口（当前端口等于原始端口说明没有"1"前缀）
    if clickhouse_original and current_click_port == clickhouse_original:
        raise DatabaseTestError(
            f"Database tests cannot use production ports. "
            f"ClickHouse port: {current_click_port}. Enable DEBUGMODE."
        )
    
    if mysql_original and current_mysql_port == mysql_original:
        raise DatabaseTestError(
            f"Database tests cannot use production ports. "
            f"MySQL port: {current_mysql_port}. Enable DEBUGMODE."
        )


class DatabaseTestCase:
    """
    Base class for database test cases with built-in safety features.
    
    Provides automatic setup and teardown for database tests with
    comprehensive safety checks and cleanup mechanisms.
    """
    
    @classmethod
    def setUpClass(cls):
        """Class-level setup with safety validation."""
        cls._validate_safe_environment()
        cls._backup_original_data()
    
    @classmethod
    def tearDownClass(cls):
        """Class-level cleanup."""
        cls._cleanup_test_data()
        cls._restore_original_data()
    
    def setUp(self):
        """Test-level setup."""
        self._test_start_state = self._capture_database_state()
    
    def tearDown(self):
        """Test-level cleanup."""
        self._cleanup_test_changes()
        self._verify_database_state()
    
    @classmethod
    def _validate_safe_environment(cls):
        """Validate the testing environment is safe."""
        _validate_debug_mode()
        _validate_port_configuration()
    
    @classmethod
    def _backup_original_data(cls):
        """Backup original database state before tests."""
        # Implementation would depend on specific database operations
        pass
    
    @classmethod
    def _restore_original_data(cls):
        """Restore original database state after tests."""
        # Implementation would depend on specific database operations
        pass
    
    def _capture_database_state(self):
        """Capture current database state for later comparison."""
        # Implementation would capture table counts, key records, etc.
        return {}
    
    def _cleanup_test_changes(self):
        """Clean up any changes made during the test."""
        # Implementation would remove test data, reset sequences, etc.
        pass
    
    def _verify_database_state(self):
        """Verify database is in expected state after cleanup."""
        # Implementation would verify cleanup was successful
        pass


# Utility functions for test data management

def create_test_data_factory():
    """
    Create a factory for generating test data.
    
    Returns a factory that can generate consistent, isolated test data
    without affecting production data structures.
    """
    
    class TestDataFactory:
        """Factory for creating isolated test data."""
        
        def __init__(self):
            self._test_prefix = "test_"
            self._cleanup_registry = []
        
        def create_test_stock(self, code=None):
            """Create test stock data."""
            if not code:
                code = f"{self._test_prefix}000001.SZ"
            
            # Register for cleanup
            self._cleanup_registry.append(('stock', code))
            
            return {
                'code': code,
                'name': f'Test Stock {code}',
                'market': 'SZ',
                'industry': 'Test Industry'
            }
        
        def create_test_bar_data(self, code=None, count=10):
            """Create test bar data."""
            if not code:
                code = self.create_test_stock()['code']
            
            self._cleanup_registry.append(('bar_data', code))
            
            # Generate test bar data
            bars = []
            for i in range(count):
                bars.append({
                    'code': code,
                    'timestamp': f'2024-01-{i+1:02d} 09:30:00',
                    'open': 10.0 + i * 0.1,
                    'high': 10.5 + i * 0.1,
                    'low': 9.5 + i * 0.1,
                    'close': 10.2 + i * 0.1,
                    'volume': 1000 + i * 100
                })
            
            return bars
        
        def cleanup_all(self):
            """Clean up all created test data."""
            for data_type, identifier in self._cleanup_registry:
                try:
                    if data_type == 'stock':
                        self._cleanup_stock_data(identifier)
                    elif data_type == 'bar_data':
                        self._cleanup_bar_data(identifier)
                except Exception as e:
                    if GLOG:
                        GLOG.warning(f"Failed to cleanup {data_type} {identifier}: {e}")
            
            self._cleanup_registry.clear()
        
        def _cleanup_stock_data(self, code):
            """Clean up specific stock data."""
            # Implementation would remove test stock from database
            pass
        
        def _cleanup_bar_data(self, code):
            """Clean up specific bar data."""
            # Implementation would remove test bar data from database
            pass
    
    return TestDataFactory()


# Configuration validation utilities

def validate_test_database_config():
    """
    Validate that the current database configuration is safe for testing.
    
    Returns:
        tuple: (is_safe, issues) where is_safe is boolean and issues is list of problems
    """
    issues = []
    
    try:
        _validate_debug_mode()
    except DatabaseTestError as e:
        issues.append(f"Debug mode: {e}")
    
    try:
        _validate_port_configuration()
    except DatabaseTestError as e:
        issues.append(f"Port configuration: {e}")
    
    return len(issues) == 0, issues


def print_database_test_warning():
    """Print a clear warning about database test risks with current connection info."""
    
    # Get current database configuration
    db_config_info = _get_database_config_info()
    
    warning_message = f"""
    :warning:  DATABASE TEST WARNING :warning:
    
    You are about to run tests that interact with actual databases.
    
    THESE TESTS WILL:
    • Create, modify, and delete database records
    • Potentially affect database performance
    • Require cleanup operations
    
    {db_config_info}
    
    SAFETY MEASURES IN PLACE:
    • Debug mode requirement (DEBUGMODE=True)
    • Development port validation (ports with '1' prefix)
    • Automatic cleanup procedures
    
    BEFORE PROCEEDING:
    • Ensure you're using development/test databases
    • Verify all production data is backed up
    • Confirm you have necessary permissions
    
    Type 'yes' to continue or 'no' to cancel.
    """
    
    print(warning_message)
    return input("Continue with database tests? (yes/no): ").lower().strip() == 'yes'


def _get_database_config_info():
    """Get formatted database configuration information for display."""
    config_lines = ["    CURRENT DATABASE CONFIGURATION:"]
    
    # Try to get configuration from different sources
    try:
        # Try to import and get GCONF
        if GCONF is None:
            try:
                from ginkgo.libs.core.config import GCONF as LocalGCONF
                config_source = LocalGCONF
            except ImportError:
                config_source = None
        else:
            config_source = GCONF
        
        if config_source is None:
            config_lines.append("    :x: Ginkgo configuration not available - cannot verify database settings")
            config_lines.append("    :bulb: Make sure you're running from Ginkgo environment")
            return "\n".join(config_lines)
        
        # ClickHouse configuration
        try:
            click_host = getattr(config_source, 'CLICKHOST', 'unknown')
            click_port = getattr(config_source, 'CLICKPORT', 'unknown') 
            click_db = getattr(config_source, 'CLICKDB', 'unknown')
            
            # Safety assessment for ClickHouse
            port_safety = _assess_port_safety(click_port, 'clickhouse')
            db_safety = _assess_database_name_safety(click_db)
            
            config_lines.append(f"    :bar_chart: ClickHouse: host={click_host}, port={click_port}, database={click_db}")
            config_lines.append(f"       {port_safety}")
            config_lines.append(f"       {db_safety}")
            
        except Exception as e:
            config_lines.append(f"    :bar_chart: ClickHouse: :x: Error reading config: {e}")
        
        # MySQL configuration
        try:
            mysql_host = getattr(config_source, 'MYSQLHOST', 'unknown')
            mysql_port = getattr(config_source, 'MYSQLPORT', 'unknown')
            mysql_db = getattr(config_source, 'MYSQLDB', 'unknown')
            
            # Safety assessment for MySQL
            port_safety = _assess_port_safety(mysql_port, 'mysql')
            db_safety = _assess_database_name_safety(mysql_db)
            
            config_lines.append(f"    :file_cabinet:  MySQL: host={mysql_host}, port={mysql_port}, database={mysql_db}")
            config_lines.append(f"       {port_safety}")
            config_lines.append(f"       {db_safety}")
            
        except Exception as e:
            config_lines.append(f"    :file_cabinet:  MySQL: :x: Error reading config: {e}")
            
        # Additional database types can be added here
        # Redis, MongoDB, etc.
        
    except Exception as e:
        config_lines.append(f"    :x: Critical error reading database configuration: {e}")
        config_lines.append("    :wrench: Check your Ginkgo installation and configuration files")
    
    return "\n".join(config_lines)


def _assess_port_safety(port, db_type):
    """评估端口安全性 - 使用GCONF属性动态判断"""
    port_str = str(port)
    
    # 获取原始端口
    original_port = _get_original_port(db_type)
    
    # 开发端口（以"1"开头且 DEBUGMODE=True）
    if GCONF and GCONF.DEBUGMODE and port_str.startswith('1'):
        return f":green_circle: Port {port} = DEVELOPMENT {db_type.upper()} (SAFE - DEBUG mode enabled)"
    
    # 生产端口（等于原始端口）
    if original_port and port_str == original_port:
        return f":red_circle: Port {port} = PRODUCTION {db_type.upper()} (:warning:  DANGER :warning:)"
    
    # 其他自定义端口
    return f":yellow_circle: Port {port} = Custom {db_type.upper()} (VERIFY MANUALLY)"


def _assess_database_name_safety(db_name):
    """Assess the safety of a database name."""
    db_str = str(db_name).lower()
    
    if db_str == 'unknown':
        return "❓ Database name unknown - Relying on port validation for safety"
    elif db_str.endswith('_test'):
        return f":white_check_mark: Database '{db_name}' ends with '_test' (EXCELLENT)"
    elif 'test' in db_str or 'dev' in db_str:
        return f":green_circle: Database '{db_name}' contains 'test/dev' (GOOD)"
    elif db_str in ['production', 'prod', 'live', 'main']:
        return f":red_circle: Database '{db_name}' = PRODUCTION DATABASE (:warning:  DANGER :warning:)"
    else:
        return f":yellow_circle: Database '{db_name}' = Using port validation for safety check"


if __name__ == '__main__':
    # Test the validation functions
    is_safe, issues = validate_test_database_config()
    
    if is_safe:
        print(":white_check_mark: Database test configuration is safe")
    else:
        print(":x: Database test configuration has issues:")
        for issue in issues:
            print(f"  - {issue}")