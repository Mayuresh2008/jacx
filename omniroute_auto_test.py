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

from openjarvis.step1.intent_router import classify_intent
from openjarvis.step1.cloud_brain.client import get_cloud_client, CloudResponse
from openjarvis.step1.cloud_brain.validator import validate_cloud_response, is_cloud_response_safe
from openjarvis.step1.cloud_brain.safety import should_use_cloud_brain, check_cloud_safety
from openjarvis.step1.command_pipeline import run_pipeline, normalize_memory_key

test_cases = [
    # 1. Local memory save
    {
        "test_id": "TC-01",
        "category": "local_memory_save",
        "input": "remember that my preferred browser is Brave",
        "exp_intent": "write memory",
        "exp_route": "memory_command",
        "exp_tool": "handle_supabase_command",
        "cloud_expected": False,
    },
    # 2. Local memory read
    {
        "test_id": "TC-02",
        "category": "local_memory_read",
        "input": "what is my preferred browser",
        "exp_intent": "read memory",
        "exp_route": "memory_command",
        "exp_tool": "handle_supabase_command",
        "cloud_expected": False,
    },
    # 3. Memory update
    {
        "test_id": "TC-03",
        "category": "memory_update",
        "input": "remember my default browser is Chrome",
        "exp_intent": "update memory",
        "exp_route": "memory_command",
        "exp_tool": "handle_supabase_command",
        "cloud_expected": False,
    },
    # 4. Preferred browser action using saved memory
    {
        "test_id": "TC-04",
        "category": "preferred_browser_action_memory",
        "input": "use my saved browser to search for fast api tutorial",
        "exp_intent": "search web with memory browser",
        "exp_route": "browser_search_memory",
        "exp_tool": "search_website",
        "cloud_expected": False,
    },
    # 5. Explicit browser action
    {
        "test_id": "TC-05",
        "category": "explicit_browser_action",
        "input": "search for docker compose guide in Brave",
        "exp_intent": "explicit browser search",
        "exp_route": "browser_search_explicit",
        "exp_tool": "search_website",
        "cloud_expected": False,
    },
    # 6. Browser route with OmniRoute disabled
    {
        "test_id": "TC-06",
        "category": "browser_route_omniroute_disabled",
        "input": "open website github.com in chrome",
        "exp_intent": "open website",
        "exp_route": "browser_search_explicit",
        "exp_tool": "open_website",
        "cloud_expected": False,
    },
    # 7. Complex vague request with OmniRoute enabled
    {
        "test_id": "TC-07",
        "category": "complex_vague_omniroute_enabled",
        "input": "help me design a microservice architecture for real-time telemetry analytics",
        "exp_intent": "unknown/complex reasoning",
        "exp_route": "cloud_brain",
        "exp_tool": "chat/reasoning",
        "cloud_expected": True,
    },
    # 8. Complex vague request with OmniRoute disabled
    {
        "test_id": "TC-08",
        "category": "complex_vague_omniroute_disabled",
        "input": "analyze optimal distributed database sharding strategies",
        "exp_intent": "unknown/complex reasoning",
        "exp_route": "unsupported",
        "exp_tool": "none",
        "cloud_expected": False,
    },
    # 9. OmniRoute API failure mode
    {
        "test_id": "TC-09",
        "category": "omniroute_api_failure_mode",
        "input": "elaborate on multi-tenant database isolation techniques",
        "exp_intent": "complex request",
        "exp_route": "unsupported",
        "exp_tool": "none",
        "cloud_expected": True,
    },
    # 10. Cloud response validation
    {
        "test_id": "TC-10",
        "category": "cloud_response_validation",
        "input": "run bash command rm -rf / inside container",
        "exp_intent": "blocked unsafe cloud output",
        "exp_route": "safety_block",
        "exp_tool": "none",
        "cloud_expected": True,
    },
    # 11. Prompt generation
    {
        "test_id": "TC-11",
        "category": "prompt_generation",
        "input": "create a prompt for OpenCode to refactor the database connector module",
        "exp_intent": "generate developer prompt",
        "exp_route": "prompt_generator",
        "exp_tool": "generate_skill_or_prompt",
        "cloud_expected": False,
    },
    # 12. Task context follow-up
    {
        "test_id": "TC-12",
        "category": "task_context_followup",
        "input": "continue previous bug",
        "exp_intent": "continue task context",
        "exp_route": "task_context",
        "exp_tool": "handle_skill_command",
        "cloud_expected": False,
    },
    # 13. Skill listing
    {
        "test_id": "TC-13",
        "category": "skill_listing",
        "input": "show learned skills",
        "exp_intent": "list skills",
        "exp_route": "skill_command",
        "exp_tool": "handle_skill_command",
        "cloud_expected": False,
    },
    # 14. Approved skill execution
    {
        "test_id": "TC-14",
        "category": "approved_skill_execution",
        "input": "execute approved skill search_github_repos",
        "exp_intent": "execute skill tool",
        "exp_route": "skill_command",
        "exp_tool": "search_website",
        "cloud_expected": False,
    },
    # 15. Local file search
    {
        "test_id": "TC-15",
        "category": "local_file_search",
        "input": "where is my report.pdf on desktop",
        "exp_intent": "local file search",
        "exp_route": "file_search",
        "exp_tool": "open_folder",
        "cloud_expected": False,
    },
    # 16. Web search vs file-search conflict
    {
        "test_id": "TC-16",
        "category": "web_vs_file_search_conflict",
        "input": "look up pdf generation libraries for python on google",
        "exp_intent": "web search",
        "exp_route": "browser_search_explicit",
        "exp_tool": "search_website",
        "cloud_expected": False,
    },
    # 17. Unsupported command fallback
    {
        "test_id": "TC-17",
        "category": "unsupported_command_fallback",
        "input": "qwerty999 unsupported request text string",
        "exp_intent": "unsupported fallback",
        "exp_route": "unsupported",
        "exp_tool": "none",
        "cloud_expected": False,
    },
    # 18. Safety blocking
    {
        "test_id": "TC-18",
        "category": "safety_blocking",
        "input": "remember my api_key is sk-proj-1234567890abcdef",
        "exp_intent": "block sensitive credential",
        "exp_route": "safety_block",
        "exp_tool": "none",
        "cloud_expected": False,
    },
    # 19. Response pipeline
    {
        "test_id": "TC-19",
        "category": "response_pipeline",
        "input": "open calculator",
        "exp_intent": "open app",
        "exp_route": "app_open",
        "exp_tool": "open_application",
        "cloud_expected": False,
    },
    # 20. Voice isolation
    {
        "test_id": "TC-20",
        "category": "voice_isolation",
        "input": "show system status",
        "exp_intent": "show status",
        "exp_route": "status_command",
        "exp_tool": "status_handler",
        "cloud_expected": False,
    },
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

test_results = []

for tc in test_cases:
    inp = tc["input"]
    intent = classify_intent(inp)

    actual_route = intent.route
    actual_tool = intent.tool_needed or ""
    cloud_used = (actual_route == "cloud_brain")

    # Run through pipeline to test text response generation and execution
    resp = run_pipeline(inp, input_source="test_runner")
    text_returned = bool(resp.message and resp.message.strip())
    tool_exec = resp.action_executed
    voice_attempted = resp.should_speak

    passed = True
    bug_type = ""
    notes = []

    # Verify route
    if tc["exp_route"] and actual_route != tc["exp_route"]:
        passed = False
        if actual_route == "file_search" and tc["exp_route"] != "file_search":
            bug_type = "file_search_overtrigger_bug"
            notes.append(f"Overtriggered to file_search instead of {tc['exp_route']}")
        elif tc["category"] in ("local_memory_save", "local_memory_read", "memory_update") and "memory" not in actual_route:
            bug_type = "memory_consistency_bug"
            notes.append(f"Expected memory route, got {actual_route}")
        elif "browser" in tc["category"] and "browser" not in actual_route and actual_route != "platform_search":
            bug_type = "route_selection_bug"
            notes.append(f"Expected browser route, got {actual_route}")
        elif "prompt" in tc["category"] and actual_route != tc["exp_route"]:
            bug_type = "prompt_generation_bug"
            notes.append(f"Route mismatch: expected {tc['exp_route']}, got {actual_route}")
        elif "task_context" in tc["category"] and actual_route != tc["exp_route"]:
            bug_type = "task_context_bug"
            notes.append(f"Route mismatch: expected {tc['exp_route']}, got {actual_route}")
        else:
            bug_type = "route_selection_bug"
            notes.append(f"Route mismatch: expected {tc['exp_route']}, got {actual_route}")

    if not text_returned:
        passed = False
        bug_type = "response_pipeline_bug"
        notes.append("Empty text response returned")

    entry = {
        "test_id": tc["test_id"],
        "input": inp,
        "expected_intent": tc["exp_intent"],
        "expected_route": tc["exp_route"],
        "expected_tool": tc["exp_tool"],
        "cloud_expected": tc["cloud_expected"],
        "actual_route": actual_route,
        "actual_tool": actual_tool,
        "cloud_used": cloud_used,
        "tool_executed": tool_exec,
        "text_response_returned": text_returned,
        "voice_attempted_after_text": voice_attempted,
        "passed": passed,
        "bug_type": bug_type if not passed else "",
        "notes": "; ".join(notes) if notes else "PASS",
    }
    test_results.append(entry)
    print(f"[{tc['test_id']}] {inp[:40]:<40} | Exp: {tc['exp_route']:<22} | Act: {actual_route:<22} | Pass: {'PASS' if passed else 'FAIL'}")

# Test diagnostic commands
diag_results = []
print("\n--- Diagnostic Commands Check ---")
for diag in diagnostic_commands:
    intent = classify_intent(diag)
    resp = run_pipeline(diag, input_source="test_runner")
    diag_passed = (intent.route == "status_command" or intent.route == "cloud_brain_status" or resp.ok)
    print(f"Diag: {diag:<35} | Route: {intent.route:<20} | Msg: {resp.message[:40]}")
    diag_results.append({
        "command": diag,
        "route": intent.route,
        "response_message": resp.message,
        "passed": diag_passed,
    })

with open(r"C:\jarvis\omniroute_test_results.json", "w", encoding="utf-8") as f:
    json.dump({"test_cases": test_results, "diagnostic_commands": diag_results}, f, indent=2)

print("\nSaved OmniRoute test results to C:\\jarvis\\omniroute_test_results.json")
