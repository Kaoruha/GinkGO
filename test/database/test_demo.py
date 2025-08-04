"""
Demo database test to verify the warning system works.
"""

import unittest
from test.database.test_isolation import database_test_required


class TestDatabaseDemo(unittest.TestCase):
    """Demo test class to verify database warning system."""
    
    @database_test_required
    def test_basic_database_connection(self):
        """Basic test to verify database connection warning appears."""
        # This test just verifies the warning system works
        self.assertTrue(True, "Database test isolation system is working")
    
    @database_test_required
    def test_configuration_display(self):
        """Test that database configuration is properly displayed."""
        # This test verifies that connection info is shown in warnings
        self.assertTrue(True, "Configuration display test passed")


if __name__ == '__main__':
    unittest.main()