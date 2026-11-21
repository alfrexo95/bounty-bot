"""
Unit Test Suite for Issue #64
"""

import unittest
from solution import SolutionHandler

class TestSolutionHandler(unittest.TestCase):
    def setUp(self):
        self.handler = SolutionHandler()

    def test_execution_status(self):
        result = self.handler.execute()
        self.assertEqual(result.get("status"), "SUCCESS")
        self.assertEqual(result.get("issue"), 64)

if __name__ == "__main__":
    unittest.main()
