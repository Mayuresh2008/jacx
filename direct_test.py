import sys
import os
import json
import time

sys.path.insert(0, r"C:\jarvis\veyra-openjarvis-base\src")

# Set required environment variables mirroring start-step7.bat
os.environ["ENABLE_STEP_1_BASIC_COMMANDS"] = "true"
os.environ["ENABLE_LOCAL_APP_OPENING"] = "true"
os.environ["ENABLE_STEP_2_BROWSER_SEARCH"] = "true"
os.environ["ENABLE_LOCAL_WEBSITE_OPENING"] = "true"
os.environ["ENABLE_LOCAL_BROWSER_SEARCH"] = "true"
os.environ["ENABLE_STEP_3_FILE_CREATION"] = "true"
os.environ["ENABLE_LOCAL_FILE_CREATION"] = "true"
os.environ["ENABLE_PERMISSION_SYSTEM"] = "true"
os.environ["ENABLE_STEP_4_NATURAL_LANGUAGE"] = "true"
os.environ["ENABLE_LOCAL_NATURAL_LANGUAGE_ROUTER"] = "true"
os.environ["ENABLE_STEP_5_AI_FALLBACK"] = "false" # Turn off network AI fallback to keep test instant & deterministic
os.environ["ENABLE_OPENROUTER_AI_FALLBACK"] = "false"
os.environ["ENABLE_STEP_7_SKILLS"] = "true"

from openjarvis.step1.orchestrator import execute_command

test_cases = [
    # Category 1: Response pipeline
    {"id": 1, "category": "response_pipeline", "input": "open calculator", "exp_route": "app_open"},
    {"id": 2, "category": "response_pipeline", "input": "show system status", "exp_route": "status_command"},

    # Category 2: Memory system & canonical keys
    {"id": 3, "category": "memory_system", "input": "remember that my preferred browser is Brave", "exp_route": "memory_command"},
    {"id": 4, "category": "memory_system", "input": "what is my preferred browser", "exp_route": "memory_command"},
    {"id": 5, "category": "memory_system", "input": "remember my default browser is Chrome", "exp_route": "memory_command"},
    {"id": 6, "category": "memory_system", "input": "what is my default browser", "exp_route": "memory_command"},

    # Category 3: Preferred browser resolution
    {"id": 7, "category": "preferred_browser_resolution", "input": "use my saved browser to search for rust programming tutorials", "exp_route": "browser_search_memory"},
    {"id": 8, "category": "preferred_browser_resolution", "input": "search for python async tutorials using my preferred browser", "exp_route": "browser_search_memory"},
    {"id": 9, "category": "preferred_browser_resolution", "input": "search for typescript design patterns in Brave", "exp_route": "browser_search_explicit"},

    # Category 4: Browser/search routing & file search overtrigger
    {"id": 10, "category": "browser_search_routing", "input": "look up quantum computing breakthroughs on google", "exp_route": "browser_search_explicit"},
    {"id": 11, "category": "browser_search_routing", "input": "find documentation about postgresql connection pooling", "exp_route": "browser_search_explicit"},
    {"id": 12, "category": "browser_search_routing", "input": "where is my report.pdf on desktop", "exp_route": "file_search"},

    # Category 5: Skill system
    {"id": 13, "category": "skill_system", "input": "show learned skills", "exp_route": "skill_command"},
    {"id": 14, "category": "skill_system", "input": "show pending skills", "exp_route": "skill_command"},
    {"id": 15, "category": "skill_system", "input": 'learn this command pattern: "find latest news on query" means search google for query', "exp_route": "skill_command"},

    # Category 6: Prompt generation
    {"id": 16, "category": "prompt_generation", "input": "create a prompt for OpenCode to fix the memory caching bug", "exp_route": "prompt_generator"},
    {"id": 17, "category": "prompt_generation", "input": "generate an Antigravity prompt for implementing OAuth2 authentication flow", "exp_route": "prompt_generator"},

    # Category 7: Task context
    {"id": 18, "category": "task_context", "input": "continue previous bug", "exp_route": "task_context"},
    {"id": 19, "category": "task_context", "input": "make the prompt stronger", "exp_route": "task_context"},

    # Category 8: Fallback quality
    {"id": 20, "category": "fallback_quality", "input": "xyz123 blabberish unsupported phrase text", "exp_route": "unsupported"},

    # Category 9: Safety
    {"id": 21, "category": "safety", "input": "remember my password is MySecretPassword123", "exp_route": "safety_block"},
    {"id": 22, "category": "safety", "input": "run powershell Get-Process", "exp_route": "safety_block"},
    {"id": 23, "category": "safety", "input": "show memory debug", "exp_route": "status_command"},
]

results = []
for tc in test_cases:
    inp = tc["input"]
    t0 = time.time()
    try:
        res = execute_command(inp, input_source="test")
        act_route = res.get("route", "")
        act_msg = res.get("message", "")
        act_tool = res.get("tool", "")
        success = res.get("success", False)

        passed = True
        bug_type = None
        notes = []

        if not act_msg or not act_msg.strip():
            passed = False
            bug_type = "response_pipeline_bug"
            notes.append("Empty response")

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

        if "unknown unknown" in act_msg.lower() or "processed unknown" in act_msg.lower():
            passed = False
            bug_type = "fallback_quality_bug"
            notes.append("Weak fallback phrase")

        results.append({
            "test_id": tc["id"],
            "category": tc["category"],
            "input": inp,
            "expected_route": tc["exp_route"],
            "actual_route": act_route,
            "actual_tool": act_tool,
            "actual_message": act_msg,
            "passed": passed,
            "bug_type": bug_type if not passed else "",
            "notes": "; ".join(notes) if notes else "PASS"
        })
        print(f"[{tc['id']:02d}] {inp[:40]:<40} | Exp: {tc['exp_route']:<22} | Act: {act_route:<22} | Pass: {passed}")
    except Exception as e:
        results.append({
            "test_id": tc["id"],
            "category": tc["category"],
            "input": inp,
            "expected_route": tc["exp_route"],
            "actual_route": "EXCEPTION",
            "actual_tool": "",
            "actual_message": str(e),
            "passed": False,
            "bug_type": "execution_bug",
            "notes": str(e)
        })
        print(f"[{tc['id']:02d}] {inp[:40]:<40} | ERROR: {e}")

with open(r"C:\jarvis\direct_test_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

print("\nSaved results to C:\\jarvis\\direct_test_results.json")
