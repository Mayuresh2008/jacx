"""Result Analyzer for Jacx Auto-QA.

Evaluates command execution outputs against general expected behavior contract rules
(`must` and `must_not`), categorizing failures into standardized bug types.
"""

import os
import json
from typing import Dict, Any, List, Tuple

CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config")
RULES_PATH = os.path.join(CONFIG_DIR, "expected_behavior_rules.json")


class ResultAnalyzer:
    """Evaluates pass/fail status and root bug categories for test command outputs."""

    def __init__(self, rules_path: str = RULES_PATH):
        self.rules = self._load_rules(rules_path)

    def _load_rules(self, path: str) -> Dict[str, Any]:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[ResultAnalyzer] Error loading rules: {e}")
        return {}

    def evaluate(self, cmd_obj: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate captured result object and return full test output entry."""
        category = cmd_obj.get("category", "")
        rule = self.rules.get(category, {})

        passed = True
        fail_reasons: List[str] = []
        bug_type = ""

        # 1. Timeout / Error check
        if result.get("error") and "timeout" in result["error"].lower():
            passed = False
            bug_type = "tool_execution_timeout"
            fail_reasons.append(f"Request timed out: {result['error']}")

        # 2. Text response returned check
        if passed and not result.get("text_response_returned"):
            passed = False
            bug_type = "response_pipeline_bug"
            fail_reasons.append("No visible text response returned from Jacx pipeline")

        act_route = result.get("route", "")
        inp_lower = cmd_obj.get("input", "").lower()
        resp_lower = result.get("actual_response", "").lower()

        # 3. Category-specific rule checks
        if passed:
            rule_passed, rule_bug, rule_reasons = self._check_rule_constraints(category, cmd_obj, result, rule)
            if not rule_passed:
                passed = False
                bug_type = rule_bug
                fail_reasons.extend(rule_reasons)

        # 4. Global bug checks (Query extraction, safety, route mismatches)
        if passed:
            # Check safety
            if category == "safety_blocked_commands":
                if not result.get("safety_blocked") and act_route != "safety_block":
                    passed = False
                    bug_type = "safety_bug"
                    fail_reasons.append("Unsafe command was not blocked by safety system")

            elif category != "safety_blocked_commands" and result.get("safety_blocked"):
                passed = False
                bug_type = "safety_bug"
                fail_reasons.append("Harmless command was falsely blocked by safety system")

            # Check query extraction quality for search routes
            if "search" in act_route or "browser" in act_route:
                query = result.get("query_used_by_browser_tool", "") or result.get("query_used", "") or resp_lower
                if query == cmd_obj.get("input", ""):
                    passed = False
                    bug_type = "query_extraction_bug"
                    fail_reasons.append("Query extractor returned full raw command without cleaning")
                elif any(phrase in query.lower() for phrase in ["saved browser", "preferred browser", "in brave", "in chrome"]):
                    passed = False
                    bug_type = "query_extraction_bug"
                    fail_reasons.append("Search query retained control/browser phrases")

            # Check route overtriggering (e.g. file_search overtrigger)
            if act_route == "file_search" and category not in ("local_file_search", "unsupported_vague_commands"):
                passed = False
                bug_type = "route_selection_bug"
                fail_reasons.append(f"Overtriggered to file_search instead of handling {category}")

        # Construct final evaluation entry
        evaluated_entry = dict(result)
        evaluated_entry["test_id"] = cmd_obj.get("test_id", "")
        evaluated_entry["category"] = category
        evaluated_entry["variation_type"] = cmd_obj.get("variation_type", "")
        evaluated_entry["expected_intent_category"] = category
        evaluated_entry["passed"] = passed
        evaluated_entry["bug_type"] = bug_type if not passed else ""
        evaluated_entry["fail_reasons"] = fail_reasons

        return evaluated_entry

    def _check_rule_constraints(self, category: str, cmd_obj: Dict[str, Any], result: Dict[str, Any], rule: Dict[str, Any]) -> Tuple[bool, str, List[str]]:
        reasons = []
        bug = "route_selection_bug"
        act_route = result.get("route", "")

        must_list = rule.get("must", [])
        must_not_list = rule.get("must_not", [])

        # Check 'must_not' rules
        for item in must_not_list:
            if "route to file_search" in item and act_route == "file_search":
                reasons.append(f"Violated must_not constraint: {item}")
                bug = "route_selection_bug"
            elif "return empty response" in item and not result.get("text_response_returned"):
                reasons.append(f"Violated must_not constraint: {item}")
                bug = "response_pipeline_bug"

        # Check category expected routes
        if category == "memory_save" and act_route not in ("memory_command", "memory_save"):
            reasons.append(f"Expected memory route, got {act_route}")
            bug = "memory_resolution_bug"
        elif category == "memory_read" and act_route not in ("memory_command", "memory_read"):
            reasons.append(f"Expected memory read route, got {act_route}")
            bug = "memory_resolution_bug"
        elif category in ("preferred_browser_search", "explicit_browser_search", "general_web_search") and "browser" not in act_route and "platform" not in act_route and act_route != "web_search":
            reasons.append(f"Expected browser/search route, got {act_route}")
            bug = "route_selection_bug"
        elif category == "prompt_generation" and act_route not in ("prompt_generator", "prompt_generation"):
            reasons.append(f"Expected prompt_generator route, got {act_route}")
            bug = "route_selection_bug"
        elif category == "local_file_search" and act_route not in ("file_search", "local_file_search"):
            reasons.append(f"Expected file_search route, got {act_route}")
            bug = "route_selection_bug"
        elif category == "skill_listing" and act_route not in ("skill_command", "status_command"):
            reasons.append(f"Expected skill_command route, got {act_route}")
            bug = "skill_execution_bug"

        if reasons:
            return False, bug, reasons
        return True, "", []


if __name__ == "__main__":
    analyzer = ResultAnalyzer()
    dummy_cmd = {"test_id": "TC-001", "category": "preferred_browser_search", "input": "use saved browser to search rust"}
    dummy_res = {"route": "file_search", "actual_response": "Searching files", "text_response_returned": True}
    eval_res = analyzer.evaluate(dummy_cmd, dummy_res)
    print("Test ResultAnalyzer evaluation:", eval_res)
