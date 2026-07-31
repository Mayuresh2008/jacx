"""Prompt Generator for Jacx Auto-QA.

Generates system-level, non-hardcoded OpenCode fix prompts based on pattern analysis
of failed test cases.
"""

import os
import time
from typing import Dict, Any, List


class PromptGenerator:
    """Produces structured OpenCode fix prompts targeting general system architectural bugs."""

    def __init__(self):
        pass

    def generate_fix_prompt(self, analysis: Dict[str, Any]) -> str:
        """Generate ready-to-paste OpenCode prompt content in markdown format."""
        top_bug = analysis.get("top_bug_category", "General Router Quality")
        pass_rate = analysis.get("pass_rate_percent", 0.0)
        failed_count = analysis.get("failed_count", 0)
        diagnoses = analysis.get("system_diagnoses", [])

        fixes_markdown = ""
        if diagnoses:
            for idx, diag in enumerate(diagnoses, 1):
                fixes_markdown += f"### Fix {idx}: {diag['component'].upper()}\n"
                fixes_markdown += f"- **Issue**: {diag['root_cause']}\n"
                fixes_markdown += f"- **Action Required**: {diag['remediation']}\n\n"
        else:
            fixes_markdown = "### Fix 1: GENERAL ROUTER POLISH\n- Audit intent classification thresholding and response builder formatting to maintain high precision.\n\n"

        prompt_text = f"""# Fix Jacx QA-detected router/intent bugs without hardcoded command patches.

## 1. Current Issue
In recent automated QA batch testing, Jacx achieved a pass rate of **{pass_rate}%** across system test cases.
A total of **{failed_count}** test failures were recorded, with the top bug category identified as **{top_bug}**.

## 2. Root Cause
Analysis of failed command patterns indicates systemic architectural gaps rather than isolated command typos:
1. Search query extraction retain control modifiers or browser keywords in memory-referenced searches.
2. Route classifier overtriggers to default fallback handlers (e.g. file search) when intent ambiguity exists.
3. Key normalization between memory write/read operations lacks uniform canonical resolution.
4. Pipeline response builder occasionally emits empty or unformatted string responses under specific tool branches.

## 3. Goal
Refactor Jacx router, query extraction, memory, and response builder components to resolve these systemic failure patterns generally across all natural language inputs.

## 4. Do Not Do
- **DO NOT** add hardcoded sentence patches (e.g. `if command == "use saved browser..."`).
- **DO NOT** add exact match string check tables or `if/else` command shortcuts.
- **DO NOT** disable safety classifications or bypass permission verification.
- **DO NOT** modify test suites to pass by swallowing errors or returning dummy success.

## 5. Required System-Level Fixes

{fixes_markdown}
## 6. Debug Logs to Add
- Add structured debug telemetry logging in `intent_router.py` printing raw input, cleaned query, selected route, and confidence score.
- Log canonical key resolution steps in `command_pipeline.py` during memory read/write commands.
- Log browser launch parameters and query strings in `browser_search` tool execution.

## 7. Regression Test Categories
Ensure systemic fixes maintain 100% pass rates across all 21 core test categories:
- Memory Save / Read / Update
- Preferred & Explicit Browser Search
- General Web & Platform Search
- Local File Search & Creation
- Prompt Generation & Planning/Reasoning
- Task Context Follow-up
- Skill Management (Listing, Creation, Approval, Execution)
- Status/Debug Commands & Response Pipeline
- OmniRoute Cloud Fallback & Safety Blockers

## 8. Final Report Requirements
After applying architectural refactoring, run the comprehensive QA test suite:
`python jacx_qa/loops/qa_loop.py --batch-size 100 --max-batches 1`
Verify that all 100 commands pass cleanly, zero QA resources leak, and report files are updated.
"""
        return prompt_text


if __name__ == "__main__":
    gen = PromptGenerator()
    sample_analysis = {
        "pass_rate_percent": 88.0,
        "failed_count": 12,
        "top_bug_category": "query_extraction_bug",
        "system_diagnoses": [
            {
                "component": "query_extractor",
                "root_cause": "Browser query extractor retains control words.",
                "remediation": "Clean query in query_extraction module.",
            }
        ],
    }
    prompt_out = gen.generate_fix_prompt(sample_analysis)
    print("Sample generated fix prompt preview:\n", prompt_out[:400])
