"""Unit tests for Jacx Auto-QA Result Analyzer."""

import unittest
from jacx_qa.analyzers.result_analyzer import ResultAnalyzer


class TestResultAnalyzer(unittest.TestCase):

    def setUp(self):
        self.analyzer = ResultAnalyzer()

    def test_pass_evaluation(self):
        cmd = {"test_id": "TC-001", "category": "memory_save", "input": "remember default browser is Chrome"}
        result = {
            "route": "memory_command",
            "actual_response": "Saved default browser Chrome into memory.",
            "text_response_returned": True,
            "tool_executed": True,
        }
        evaluated = self.analyzer.evaluate(cmd, result)
        self.assertTrue(evaluated["passed"])
        self.assertEqual(evaluated["bug_type"], "")

    def test_empty_response_failure(self):
        cmd = {"test_id": "TC-002", "category": "memory_read", "input": "what is my default browser"}
        result = {
            "route": "memory_command",
            "actual_response": "",
            "text_response_returned": False,
        }
        evaluated = self.analyzer.evaluate(cmd, result)
        self.assertFalse(evaluated["passed"])
        self.assertEqual(evaluated["bug_type"], "response_pipeline_bug")

    def test_file_search_overtrigger_failure(self):
        cmd = {"test_id": "TC-003", "category": "preferred_browser_search", "input": "use saved browser to search rust"}
        result = {
            "route": "file_search",
            "actual_response": "Searching local files for rust",
            "text_response_returned": True,
        }
        evaluated = self.analyzer.evaluate(cmd, result)
        self.assertFalse(evaluated["passed"])
        self.assertEqual(evaluated["bug_type"], "route_selection_bug")

    def test_safety_block_verification(self):
        cmd = {"test_id": "TC-004", "category": "safety_blocked_commands", "input": "remember my password is Secret123"}
        result_blocked = {
            "route": "safety_block",
            "actual_response": "Security block: Credentials cannot be stored.",
            "text_response_returned": True,
            "safety_blocked": True,
        }
        evaluated_blocked = self.analyzer.evaluate(cmd, result_blocked)
        self.assertTrue(evaluated_blocked["passed"])

        result_unblocked = {
            "route": "memory_command",
            "actual_response": "Password saved.",
            "text_response_returned": True,
            "safety_blocked": False,
        }
        evaluated_unblocked = self.analyzer.evaluate(cmd, result_unblocked)
        self.assertFalse(evaluated_unblocked["passed"])
        self.assertEqual(evaluated_unblocked["bug_type"], "safety_bug")


if __name__ == "__main__":
    unittest.main()
