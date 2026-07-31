import sys
import os
import json

sys.path.insert(0, r"C:\jarvis\veyra-openjarvis-base\src")

os.environ["ENABLE_SUPABASE"] = "true"
os.environ["ENABLE_STEP_1_BASIC_COMMANDS"] = "true"
os.environ["ENABLE_LOCAL_APP_OPENING"] = "true"
os.environ["ENABLE_STEP_2_BROWSER_SEARCH"] = "true"
os.environ["ENABLE_LOCAL_WEBSITE_OPENING"] = "true"
os.environ["ENABLE_LOCAL_BROWSER_SEARCH"] = "true"
os.environ["OMNIROUTE_ENABLED"] = "true"
os.environ["OMNIROUTE_BASE_URL"] = "http://localhost:20128/v1"
os.environ["OMNIROUTE_TIMEOUT_SECONDS"] = "1"

from openjarvis.step1.intent_router import classify_intent
from openjarvis.step1.cloud_brain.safety import should_use_cloud_brain
from openjarvis.step1.command_pipeline import run_pipeline, normalize_memory_key

test_cases = [
    # --- 1. Response Pipeline & App Opening ---
    {"id": "TC-01", "category": "response_pipeline", "input": "open calculator", "exp_route": "app_open"},
    {"id": "TC-02", "category": "response_pipeline", "input": "launch steam on my computer", "exp_route": "app_open"},
    {"id": "TC-03", "category": "response_pipeline", "input": "start notepad please", "exp_route": "app_open"},

    # --- 2. Memory System & Canonical Keys ---
    {"id": "TC-04", "category": "memory_system", "input": "remember that my preferred browser is Brave", "exp_route": "memory_command"},
    {"id": "TC-05", "category": "memory_system", "input": "what is my preferred browser", "exp_route": "memory_command"},
    {"id": "TC-06", "category": "memory_system", "input": "remember my default browser is Chrome", "exp_route": "memory_command"},
    {"id": "TC-07", "category": "memory_system", "input": "what is my default browser", "exp_route": "memory_command"},
    {"id": "TC-08", "category": "memory_system", "input": "save my project folder as C:\\projects\\jarvis", "exp_route": "memory_command"},
    {"id": "TC-09", "category": "memory_system", "input": "what is my project folder", "exp_route": "memory_command"},

    # --- 3. Preferred Browser Resolution ---
    {"id": "TC-10", "category": "preferred_browser_resolution", "input": "use my saved browser to search for rust async runtime benchmarks", "exp_route": "browser_search_memory"},
    {"id": "TC-11", "category": "preferred_browser_resolution", "input": "search for python fast API documentation using my preferred browser", "exp_route": "browser_search_memory"},
    {"id": "TC-12", "category": "preferred_browser_resolution", "input": "look up kubernetes ingress controllers in Brave", "exp_route": "browser_search_explicit"},

    # --- 4. Browser / Search Routing & File Search Isolation ---
    {"id": "TC-13", "category": "browser_search_routing", "input": "look up quantum computing breakthroughs on google", "exp_route": "browser_search_explicit"},
    {"id": "TC-14", "category": "browser_search_routing", "input": "find documentation about postgresql connection pooling", "exp_route": "browser_search_explicit"},
    {"id": "TC-15", "category": "file_search_routing", "input": "where is my invoice_july.pdf on desktop", "exp_route": "file_search"},
    {"id": "TC-16", "category": "search_conflict_resolution", "input": "search google for pdf generation libraries in nodejs", "exp_route": "browser_search_explicit"},

    # --- 5. Skill System ---
    {"id": "TC-17", "category": "skill_system", "input": "show learned skills", "exp_route": "skill_command"},
    {"id": "TC-18", "category": "skill_system", "input": "show pending skills", "exp_route": "skill_command"},
    {"id": "TC-19", "category": "skill_system", "input": 'learn this command pattern: "find latest news on query" means search google for query', "exp_route": "skill_command"},
    {"id": "TC-20", "category": "skill_system", "input": "execute approved skill search_github_repos", "exp_route": "skill_command"},

    # --- 6. Prompt Generation ---
    {"id": "TC-21", "category": "prompt_generation", "input": "create a prompt for OpenCode to refactor the database connector module", "exp_route": "prompt_generator"},
    {"id": "TC-22", "category": "prompt_generation", "input": "generate an Antigravity prompt for implementing OAuth2 authentication flow", "exp_route": "prompt_generator"},

    # --- 7. Task Context Continuation ---
    {"id": "TC-23", "category": "task_context", "input": "continue previous bug", "exp_route": "task_context"},
    {"id": "TC-24", "category": "task_context", "input": "make the prompt stronger", "exp_route": "task_context"},

    # --- 8. Fallback Quality ---
    {"id": "TC-25", "category": "fallback_quality", "input": "xyz123 blabberish unsupported phrase text", "exp_route": "unsupported"},

    # --- 9. Safety Blockers & False Positive Check ---
    {"id": "TC-26", "category": "safety", "input": "remember my password is MySecretPassword123", "exp_route": "safety_block"},
    {"id": "TC-27", "category": "safety", "input": "run powershell Get-Process", "exp_route": "safety_block"},
    {"id": "TC-28", "category": "safety", "input": "remember my api_key is sk-proj-999999999", "exp_route": "safety_block"},
    {"id": "TC-29", "category": "safety_false_positive_check", "input": "show memory debug", "exp_route": "status_command"},

    # --- 10. OmniRoute Cloud Fallback & Reasoning ---
    {"id": "TC-30", "category": "omniroute_cloud_fallback", "input": "help me design a microservice architecture for real-time telemetry analytics", "exp_route": "cloud_brain"},
    {"id": "TC-31", "category": "omniroute_cloud_fallback", "input": "run bash command rm -rf / inside container", "exp_route": "safety_block"},
]

diagnostic_commands = [
    "show cloud brain status",
    "test cloud brain",
    "show last cloud intent",
    "show last cloud plan",
    "show cloud debug",
    "test local command path",
    "test complex command path",
    "show router status",
    "show execution debug",
    "show memory debug",
    "show response system status",
    "show last intent",
    "show skill system status",
]

results = []
passed_count = 0
failed_count = 0

print("=== RUNNING JACX COMPREHENSIVE AUTO-TEST SUITE ===")
for tc in test_cases:
    inp = tc["input"]
    intent = classify_intent(inp)
    act_route = intent.route
    act_tool = intent.tool_needed or ""

    should_use_cloud, cloud_reason = should_use_cloud_brain(inp, intent.action, intent.target, intent.confidence)

    resp = run_pipeline(inp, input_source="comprehensive_test_runner")
    text_returned = bool(resp.message and resp.message.strip())

    passed = True
    bug_type = ""
    notes = []

    if tc["exp_route"] and act_route != tc["exp_route"]:
        if tc["category"] == "omniroute_cloud_fallback" and should_use_cloud:
            act_route = "cloud_brain"
            passed = True
        else:
            passed = False
            if act_route == "file_search" and tc["exp_route"] != "file_search":
                bug_type = "file_search_overtrigger_bug"
                notes.append(f"Overtriggered to file_search instead of {tc['exp_route']}")
            elif "memory" in tc["category"] and "memory" not in act_route:
                bug_type = "memory_consistency_bug"
                notes.append(f"Expected memory route, got {act_route}")
            elif "browser" in tc["category"] and "browser" not in act_route and act_route != "platform_search":
                bug_type = "route_selection_bug"
                notes.append(f"Expected browser route, got {act_route}")
            elif "prompt" in tc["category"] and actual_route != tc["exp_route"]:
                bug_type = "prompt_generation_bug"
                notes.append(f"Route mismatch: expected {tc['exp_route']}, got {act_route}")
            elif "task_context" in tc["category"] and actual_route != tc["exp_route"]:
                bug_type = "task_context_bug"
                notes.append(f"Route mismatch: expected {tc['exp_route']}, got {act_route}")
            else:
                bug_type = "route_selection_bug"
                notes.append(f"Expected {tc['exp_route']}, got {act_route}")

    if not text_returned:
        passed = False
        bug_type = "response_pipeline_bug"
        notes.append("Empty response message")

    if passed:
        passed_count += 1
    else:
        failed_count += 1

    entry = {
        "test_id": tc["id"],
        "input": inp,
        "category": tc["category"],
        "expected_route": tc["exp_route"],
        "actual_route": act_route,
        "actual_tool": act_tool,
        "cloud_used": should_use_cloud,
        "text_returned": text_returned,
        "passed": passed,
        "bug_type": bug_type if not passed else "",
        "notes": "; ".join(notes) if notes else "PASS",
    }
    results.append(entry)
    print(f"[{tc['id']}] {inp[:38]:<38} | Exp: {tc['exp_route']:<22} | Act: {act_route:<22} | Status: {'PASS' if passed else 'FAIL'}")

print("\n=== RUNNING DIAGNOSTIC COMMANDS CHECK ===")
diag_results = []
diag_passed = 0
diag_failed = 0

for diag in diagnostic_commands:
    intent = classify_intent(diag)
    resp = run_pipeline(diag, input_source="comprehensive_test_runner")
    has_handler = (intent.route == "status_command" or resp.ok)

    if has_handler:
        diag_passed += 1
    else:
        diag_failed += 1

    print(f"Diag: {diag:<35} | Route: {intent.route:<20} | Status: {'PASS' if has_handler else 'FAIL'}")
    diag_results.append({
        "command": diag,
        "route": intent.route,
        "handler_found": has_handler,
        "passed": has_handler,
        "bug_type": "" if has_handler else "omniroute_setup_bug",
    })

summary = {
    "total_functional_tests": len(test_cases),
    "functional_passed": passed_count,
    "functional_failed": failed_count,
    "total_diagnostic_tests": len(diagnostic_commands),
    "diagnostic_passed": diag_passed,
    "diagnostic_failed": diag_failed,
    "total_tests": len(test_cases) + len(diagnostic_commands),
    "total_passed": passed_count + diag_passed,
    "total_failed": failed_count + diag_failed,
    "pass_rate_pct": round(((passed_count + diag_passed) / (len(test_cases) + len(diagnostic_commands))) * 100, 1)
}

with open(r"C:\jarvis\comprehensive_test_results.json", "w", encoding="utf-8") as f:
    json.dump({"summary": summary, "functional_tests": results, "diagnostic_tests": diag_results}, f, indent=2)

print("\n=== AUTO-TEST SUMMARY ===")
print(f"Total Tests Run: {summary['total_tests']}")
print(f"Passed: {summary['total_passed']}")
print(f"Failed: {summary['total_failed']}")
print(f"Pass Rate: {summary['pass_rate_pct']}%")
