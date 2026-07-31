"""Pattern Analyzer for Jacx Auto-QA.

Analyzes failed command test cases across a batch, groups them by root cause,
and extracts architectural, system-level diagnosis insights.
"""

from typing import Dict, Any, List
from collections import Counter, defaultdict


class PatternAnalyzer:
    """Groups failed command tests by bug type and extracts root cause patterns."""

    def __init__(self):
        pass

    def analyze(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Perform comprehensive pattern analysis on a batch of test results."""
        total_count = len(results)
        failed_tests = [r for r in results if not r.get("passed", False)]
        passed_count = total_count - len(failed_tests)
        pass_rate = round((passed_count / total_count * 100), 1) if total_count > 0 else 0.0

        bug_type_counts = Counter()
        category_failure_counts = Counter()
        route_failure_counts = Counter()
        grouped_failures = defaultdict(list)

        for test in failed_tests:
            bug = test.get("bug_type", "unknown_bug")
            cat = test.get("category", "unknown_category")
            route = test.get("route", "unknown_route")

            bug_type_counts[bug] += 1
            category_failure_counts[cat] += 1
            route_failure_counts[route] += 1

            grouped_failures[bug].append({
                "test_id": test.get("test_id", ""),
                "input": test.get("input", ""),
                "category": cat,
                "route": route,
                "fail_reasons": test.get("fail_reasons", []),
            })

        system_diagnoses = self._derive_system_diagnoses(bug_type_counts, category_failure_counts, grouped_failures)

        top_bug_category = bug_type_counts.most_common(1)[0][0] if bug_type_counts else "None"

        return {
            "total_tested": total_count,
            "passed_count": passed_count,
            "failed_count": len(failed_tests),
            "pass_rate_percent": pass_rate,
            "top_bug_category": top_bug_category,
            "bug_type_counts": dict(bug_type_counts),
            "category_failure_counts": dict(category_failure_counts),
            "route_failure_counts": dict(route_failure_counts),
            "system_diagnoses": system_diagnoses,
            "grouped_failures": dict(grouped_failures),
        }

    def _derive_system_diagnoses(
        self,
        bug_counts: Counter,
        cat_counts: Counter,
        grouped: Dict[str, List[Dict[str, Any]]],
    ) -> List[Dict[str, str]]:
        """Derive system-level root cause diagnoses based on observed failure patterns."""
        diagnoses = []

        if bug_counts.get("query_extraction_bug", 0) > 0:
            diagnoses.append({
                "component": "query_extractor",
                "root_cause": "Browser search query extractor is not removing browser trigger words or memory keywords before forming target search URL.",
                "remediation": "Update query_extraction module to strip phrases like 'saved browser', 'in Brave', and 'using preferred browser' before web routing.",
            })

        if bug_counts.get("route_selection_bug", 0) > 0:
            diagnoses.append({
                "component": "intent_router",
                "root_cause": "Router classifier overtriggers to file_search or misroutes prompt/planning commands.",
                "remediation": "Refine route priority rules in intent_router.py so file_search requires explicit file extensions or path keywords.",
            })

        if bug_counts.get("memory_resolution_bug", 0) > 0:
            diagnoses.append({
                "component": "memory_system",
                "root_cause": "Memory write and read handlers use inconsistent canonical key normalization (e.g. default_browser vs preferred_browser).",
                "remediation": "Standardize key normalization across local memory and Supabase persistence layers in normalize_memory_key().",
            })

        if bug_counts.get("response_pipeline_bug", 0) > 0:
            diagnoses.append({
                "component": "response_pipeline",
                "root_cause": "Response builder returned empty or unhandled null text message for specific route branches.",
                "remediation": "Enforce fallback non-empty message formatting across all command pipeline return paths.",
            })

        if bug_counts.get("skill_execution_bug", 0) > 0:
            diagnoses.append({
                "component": "skill_manager",
                "root_cause": "Skill matcher identified skill pattern but skill execution handler failed to dispatch response.",
                "remediation": "Ensure skill_manager correctly connects pending/approved skill patterns to command execution pipeline.",
            })

        if bug_counts.get("cloud_fallback_bug", 0) > 0:
            diagnoses.append({
                "component": "cloud_brain_omniroute",
                "root_cause": "OmniRoute cloud fallback validation failed or fell through incorrectly.",
                "remediation": "Validate OmniRoute response schema and ensure local command execution remains safe when cloud brain fails.",
            })

        if bug_counts.get("safety_bug", 0) > 0:
            diagnoses.append({
                "component": "safety_classifier",
                "root_cause": "Safety classifier mismatched security boundaries for credentials or safe commands.",
                "remediation": "Audit regex and keyword rules in safety.py to cleanly separate sensitive credentials from normal status commands.",
            })

        return diagnoses


if __name__ == "__main__":
    analyzer = PatternAnalyzer()
    dummy_results = [
        {"test_id": "TC-1", "passed": False, "bug_type": "query_extraction_bug", "category": "preferred_browser_search", "route": "browser_search_memory"},
        {"test_id": "TC-2", "passed": True, "bug_type": "", "category": "memory_save", "route": "memory_command"},
    ]
    diag = analyzer.analyze(dummy_results)
    print("Test PatternAnalyzer analysis:", diag)
