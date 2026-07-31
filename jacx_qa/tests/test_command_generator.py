"""Unit tests for Jacx Auto-QA Command Generator."""

import unittest
from jacx_qa.generators.command_generator import CommandGenerator, CATEGORIES


class TestCommandGenerator(unittest.TestCase):

    def setUp(self):
        self.generator = CommandGenerator(seed=42)

    def test_batch_size_and_indexing(self):
        batch = self.generator.generate_batch(100)
        self.assertEqual(len(batch), 100)
        self.assertEqual(batch[0]["test_id"], "TC-001")
        self.assertEqual(batch[-1]["test_id"], "TC-100")

    def test_category_coverage(self):
        batch = self.generator.generate_batch(100)
        generated_cats = set(cmd["category"] for cmd in batch)
        for cat in CATEGORIES:
            self.assertIn(cat, generated_cats, f"Category {cat} missing from generated batch")

    def test_command_structure(self):
        cmd = self.generator.generate_command("memory_save")
        self.assertIn("category", cmd)
        self.assertIn("variation_type", cmd)
        self.assertIn("input", cmd)
        self.assertIn("timestamp", cmd)
        self.assertTrue(len(cmd["input"]) > 0)


if __name__ == "__main__":
    unittest.main()
