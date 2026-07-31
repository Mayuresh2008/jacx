import sys
import os
import json

sys.path.insert(0, r"C:\jarvis\veyra-openjarvis-base\src")

os.environ["ENABLE_SUPABASE"] = "true"
os.environ["ENABLE_STEP_1_BASIC_COMMANDS"] = "true"

from openjarvis.step1.intent_router import classify_intent

test_cases = [
    # Category 1: Response pipeline & status
    {"id": 1, "category": "response_pipeline", "input": "open calculator", "exp_route": "app_open"},
    {"id": 2, "category": "response_pipeline", "input": "show system status", "exp_route": "status_command"},
    {"id": 3, "category": "response_pipeline", "input": "show memory debug", "exp_route": "status_command"},

    # Category 2: Memory system & canonical keys
    {"id": 4, "category": "memory_system", "input": "remember that my preferred browser is Brave", "exp_route": "memory_command"},
    {"id": 5, "category": "memory_system", "input": "what is my preferred browser", "exp_route": "memory_command"},
    {"id": 6, "category": "memory_system", "input": "remember my default browser is Chrome", "exp_route": "memory_command"},
    {"id": 7, "category": "memory_system", "input": "what is my default browser", "exp_route": "memory_command"},

    # Category 3: Preferred browser resolution
    {"id": 8, "category": "preferred_browser_resolution", "input": "use my saved browser to search for rust programming tutorials", "exp_route": "browser_search_memory"},
    {"id": 9, "category": "preferred_browser_resolution", "input": "search for python async tutorials using my preferred browser", "exp_route": "browser_search_memory"},
    {"id": 10, "category": "preferred_browser_resolution", "input": "search for typescript design patterns in Brave", "exp_route": "browser_search_explicit"},

    # Category 4: Browser/search routing & file search overtrigger
    {"id": 11, "category": "browser_search_routing", "input": "look up quantum computing breakthroughs on google", "exp_route": "browser_search_explicit"},
    {"id": 12, "category": "browser_search_routing", "input": "find documentation about postgresql connection pooling", "exp_route": "browser_search_explicit"},
    {"id": 13, "category": "browser_search_routing", "input": "where is my report.pdf on desktop", "exp_route": "file_search"},

    # Category 5: Skill system
    {"id": 14, "category": "skill_system", "input": "show learned skills", "exp_route": "skill_command"},
    {"id": 15, "category": "skill_system", "input": "show pending skills", "exp_route": "skill_command"},
    {"id": 16, "category": "skill_system", "input": 'learn this command pattern: "find latest news on query" means search google for query', "exp_route": "skill_command"},

    # Category 6: Prompt generation
    {"id": 17, "category": "prompt_generation", "input": "create a prompt for OpenCode to fix the memory caching bug", "exp_route": "prompt_generator"},
    {"id": 18, "category": "prompt_generation", "input": "generate an Antigravity prompt for implementing OAuth2 authentication flow", "exp_route": "prompt_generator"},

    # Category 7: Task context
    {"id": 19, "category": "task_context", "input": "continue previous bug", "exp_route": "task_context"},
    {"id": 20, "category": "task_context", "input": "make the prompt stronger", "exp_route": "task_context"},

    # Category 8: Fallback quality
    {"id": 21, "category": "fallback_quality", "input": "xyz123 blabberish unsupported phrase text", "exp_route": "unsupported"},

    # Category 9: Safety
    {"id": 22, "category": "safety", "input": "remember my password is MySecretPassword123", "exp_route": "safety_block"},
    {"id": 23, "category": "safety", "input": "run powershell Get-Process", "exp_route": "safety_block"},
]

results = []
for tc in test_cases:
    inp = tc["input"]
    intent = classify_intent(inp)

    act_route = intent.route
    act_action = intent.action
    act_target = intent.target
    is_blocked = intent.is_blocked
    block_reason = intent.block_reason

    passed = True
    bug_type = None
    notes = []

    if tc["exp_route"] and act_route != tc["exp_route"]:
        passed = False
        if act_route == "file_search" and tc["exp_route"] != "file_search":
            bug_type = "file_search_overtrigger_bug"
            notes.append(f"Overtriggered to file_search instead of {tc['exp_route']}")
        elif tc["category"] == "memory_system" and "memory" not in act_route:
            bug_type = "memory_resolution_bug"
            notes.append(f"Expected memory route, got {act_route}")
        elif tc["category"] == "preferred_browser_resolution" and "browser" not in act_route:
            bug_type = "route_selection_bug"
            notes.append(f"Expected browser route, got {act_route}")
        else:
            bug_type = "route_selection_bug"
            notes.append(f"Expected {tc['exp_route']}, got {act_route}")

    results.append({
        "test_id": tc["id"],
        "category": tc["category"],
        "input": inp,
        "expected_route": tc["exp_route"],
        "actual_route": act_route,
        "action": act_action,
        "target": act_target,
        "is_blocked": is_blocked,
        "block_reason": block_reason,
        "passed": passed,
        "bug_type": bug_type if not passed else "",
        "notes": "; ".join(notes) if notes else "PASS"
    })

    print(f"[{tc['id']:02d}] {inp[:42]:<42} | Exp: {tc['exp_route']:<22} | Act: {act_route:<22} | Pass: {'PASS' if passed else 'FAIL'}")

with open(r"C:\jarvis\router_test_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

print("\nSaved router test results to C:\\jarvis\\router_test_results.json")
