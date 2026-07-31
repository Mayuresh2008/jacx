"""Rule Distiller for Jacx Auto-QA.

Analyzes failed commands from QA batches, extracts root causes,
and distills them into permanent generalized rules stored in jacx_brain/rules/.

Supports:
- Pattern-based root cause extraction
- Rule generalization (abstracting specific commands into categories)
- Duplicate detection against existing rules
- Automatic merge with similar existing rules
"""

import os
import json
import re
from typing import Dict, Any, List, Optional
from collections import Counter, defaultdict


BRAIN_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BRAIN_MANAGER_PATH = os.path.join(BRAIN_ROOT, "brain_manager.py")

import sys
sys.path.insert(0, BRAIN_ROOT)
from brain_manager import BrainManager


BUG_TYPE_ROOT_CAUSES = {
    "query_extraction_bug": {
        "component": "query_extractor",
        "general_cause": "Search query retains browser control phrases, memory references, or platform names that should be stripped before web routing.",
        "remediation": "Update extract_search_query() to strip additional control/memory phrases before passing query to search handler.",
    },
    "route_selection_bug": {
        "component": "intent_router",
        "general_cause": "Command is misrouted to wrong handler (e.g., file_search for web queries, web search for file queries, or unknown fallback for recognized patterns).",
        "remediation": "Refine route classification signals in intent_router.py to better distinguish between similar command patterns.",
    },
    "memory_resolution_bug": {
        "component": "memory_system",
        "general_cause": "Memory save/read commands fail due to key normalization mismatches, missing pattern recognition, or inconsistent canonical key handling.",
        "remediation": "Standardize memory key normalization and expand pattern recognition for save/read/get/inspect commands.",
    },
    "response_pipeline_bug": {
        "component": "response_pipeline",
        "general_cause": "Pipeline returns empty or unhelpful response for recognized command patterns.",
        "remediation": "Ensure all pipeline paths return non-empty, contextually appropriate responses.",
    },
    "skill_execution_bug": {
        "component": "skill_manager",
        "general_cause": "Skill pattern matched but execution handler failed to produce correct output.",
        "remediation": "Verify skill execution pipeline connects pattern matches to correct action handlers.",
    },
    "safety_bug": {
        "component": "safety_classifier",
        "general_cause": "Safe commands incorrectly blocked, or dangerous commands incorrectly allowed.",
        "remediation": "Audit safety classification boundaries to reduce false positives/negatives.",
    },
}

CATEGORY_ROUTE_MAP = {
    "memory_save": "memory_command",
    "memory_read": "memory_command",
    "explicit_browser_search": "browser_search_explicit",
    "preferred_browser_search": "browser_search_memory",
    "general_web_search": "browser_search_explicit",
    "local_file_search": "file_search",
    "prompt_generation": "prompt_generator",
    "planning_command": "planning",
    "skill_execution": "skill_command",
    "app_launcher": "app_open",
}


class RuleDistiller:
    """Distills failed QA commands into permanent generalized rules."""

    def __init__(self):
        self.brain = BrainManager()

    def distill_from_batch(self, batch_results: List[Dict[str, Any]], batch_id: str = "") -> Dict[str, Any]:
        """Analyze batch failures and distill into rules."""
        failed = [r for r in batch_results if not r.get("passed", False)]
        if not failed:
            return {"distilled": 0, "merged": 0, "skipped": 0, "rules": []}

        grouped = defaultdict(list)
        for f in failed:
            bug_type = f.get("bug_type", "unknown")
            grouped[bug_type].append(f)

        distilled_rules = []
        merged_count = 0
        skipped_count = 0

        for bug_type, failures in grouped.items():
            rule = self._distill_rule(bug_type, failures, batch_id)
            if rule is None:
                skipped_count += len(failures)
                continue

            was_merged, rule_id = self.brain.merge_or_create_rule(rule)
            if was_merged:
                merged_count += 1
            else:
                distilled_rules.append(rule)

        stats = self.brain.load_stats()
        stats["total_batches_analyzed"] = stats.get("total_batches_analyzed", 0) + 1
        stats["total_failures_distilled"] = stats.get("total_failures_distilled", 0) + len(failed)
        stats["last_distilled_at"] = self._now_iso()
        self.brain.save_stats(stats)

        return {
            "distilled": len(distilled_rules),
            "merged": merged_count,
            "skipped": skipped_count,
            "rules": distilled_rules,
        }

    def _distill_rule(self, bug_type: str, failures: List[Dict[str, Any]], batch_id: str) -> Optional[Dict[str, Any]]:
        """Create a generalized rule from a group of failures."""
        template = BUG_TYPE_ROOT_CAUSES.get(bug_type, {
            "component": "unknown",
            "general_cause": f"Unknown root cause for {bug_type}.",
            "remediation": "Investigate failure pattern manually.",
        })

        categories = Counter(f.get("category", "unknown") for f in failures)
        top_category = categories.most_common(1)[0][0] if categories else "unknown"

        routes = Counter(f.get("route", "unknown") for f in failures)
        top_route = routes.most_common(1)[0][0] if routes else "unknown"

        fail_reasons = []
        for f in failures:
            fail_reasons.extend(f.get("fail_reasons", []))
        reason_counts = Counter(fail_reasons)
        top_reasons = [r for r, _ in reason_counts.most_common(3)]

        example_commands = []
        for f in failures[:5]:
            example_commands.append({
                "command": f.get("input", ""),
                "actual_response": f.get("actual_response", ""),
                "fail_reasons": f.get("fail_reasons", []),
            })

        root_cause = self._generalize_root_cause(bug_type, top_category, top_reasons, failures)
        remediation = self._generalize_remediation(bug_type, top_category, template)

        confidence = self._calculate_initial_confidence(len(failures), bug_type)

        rule = {
            "bug_type": bug_type,
            "category": top_category,
            "expected_route": CATEGORY_ROUTE_MAP.get(top_category, top_route),
            "root_cause": root_cause,
            "remediation": remediation,
            "component": template["component"],
            "confidence": confidence,
            "occurrences": len(failures),
            "example_failures": example_commands,
            "top_fail_reasons": top_reasons,
            "source_batch": batch_id,
        }

        return rule

    def _generalize_root_cause(self, bug_type: str, category: str, reasons: List[str], failures: List[Dict[str, Any]]) -> str:
        """Create a generalized root cause description."""
        template = BUG_TYPE_ROOT_CAUSES.get(bug_type, {})
        base = template.get("general_cause", f"Pattern of {bug_type} failures in {category}.")

        if bug_type == "query_extraction_bug":
            commands = [f.get("input", "") for f in failures[:3]]
            phrases = self._extract_common_phrases(commands)
            if phrases:
                return f"{base} Common triggering phrases: {', '.join(phrases[:5])}."
        elif bug_type == "route_selection_bug":
            routes = [f.get("route", "") for f in failures[:3]]
            unique_routes = list(set(r for r in routes if r))
            if unique_routes:
                return f"{base} Misrouted to: {', '.join(unique_routes)}."
        elif bug_type == "memory_resolution_bug":
            commands = [f.get("input", "") for f in failures[:3]]
            patterns = self._extract_memory_patterns(commands)
            if patterns:
                return f"{base} Unrecognized patterns: {', '.join(patterns[:3])}."

        return base

    def _generalize_remediation(self, bug_type: str, category: str, template: Dict[str, str]) -> str:
        """Create a generalized remediation instruction."""
        base = template.get("remediation", "Investigate and fix the root cause.")

        if bug_type == "query_extraction_bug":
            return f"{base} Specifically handle {category} commands. Reference: intent_router.py extract_search_query()."
        elif bug_type == "route_selection_bug":
            return f"{base} For {category} category, verify signals in intent_router.py _classify_{category.split('_')[0]}()."
        elif bug_type == "memory_resolution_bug":
            return f"{base} For {category} pattern, verify memory key normalization and pattern matching."

        return base

    def _calculate_initial_confidence(self, failure_count: int, bug_type: str) -> float:
        """Calculate initial confidence for a new rule."""
        base = 0.5
        if failure_count >= 5:
            base = 0.7
        elif failure_count >= 3:
            base = 0.6
        elif failure_count == 2:
            base = 0.55

        if bug_type in ("safety_bug", "response_pipeline_bug"):
            base = min(1.0, base + 0.1)

        return round(base, 2)

    def _extract_common_phrases(self, commands: List[str]) -> List[str]:
        """Extract common phrases from failing commands."""
        word_counter = Counter()
        for cmd in commands:
            words = cmd.lower().split()
            for i in range(len(words)):
                for j in range(i + 1, min(i + 4, len(words) + 1)):
                    phrase = " ".join(words[i:j])
                    if len(phrase) > 3:
                        word_counter[phrase] += 1
        return [phrase for phrase, count in word_counter.most_common(10) if count >= 2]

    def _extract_memory_patterns(self, commands: List[str]) -> List[str]:
        """Extract memory-related patterns from commands."""
        patterns = []
        memory_verbs = ["save", "remember", "store", "get", "what", "show", "inspect", "check"]
        for cmd in commands[:5]:
            words = cmd.lower().split()
            for i, word in enumerate(words):
                if word in memory_verbs:
                    pattern = " ".join(words[i:i + 3])
                    patterns.append(pattern)
        return list(set(patterns))

    def _now_iso(self) -> str:
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
