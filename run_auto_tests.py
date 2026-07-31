import requests
import json

URL_EXECUTE = "http://127.0.0.1:8000/v1/step1/commands/execute"

test_cases = [
    # --- 1. Response Pipeline ---
    {
        "category": "response_pipeline",
        "input": "open calculator",
        "expected_intent": "open app",
        "expected_route": "app_open",
        "expected_tool": "open_application",
        "expected_behavior": "Returns non-empty text response confirming app opening",
    },
    {
        "category": "response_pipeline",
        "input": "show system status",
        "expected_intent": "show status",
        "expected_route": "status_command",
        "expected_tool": "status_handler",
        "expected_behavior": "Returns non-empty text status message",
    },

    # --- 2. Memory System & Canonical Keys ---
    {
        "category": "memory_system",
        "input": "remember that my preferred browser is Brave",
        "expected_intent": "write memory",
        "expected_route": "memory_command",
        "expected_tool": "handle_supabase_command",
        "expected_behavior": "Saves preferred_browser as Brave in Supabase/Memory",
    },
    {
        "category": "memory_system",
        "input": "what is my preferred browser",
        "expected_intent": "read memory",
        "expected_route": "memory_command",
        "expected_tool": "handle_supabase_command",
        "expected_behavior": "Returns Brave from memory",
    },
    {
        "category": "memory_system",
        "input": "remember my default browser is Chrome",
        "expected_intent": "update memory",
        "expected_route": "memory_command",
        "expected_tool": "handle_supabase_command",
        "expected_behavior": "Updates preferred_browser to Chrome (aliased to canonical preferred_browser)",
    },
    {
        "category": "memory_system",
        "input": "what is my default browser",
        "expected_intent": "read memory",
        "expected_route": "memory_command",
        "expected_tool": "handle_supabase_command",
        "expected_behavior": "Returns Chrome by mapping alias 'default browser' to canonical key 'preferred_browser'",
    },

    # --- 3. Preferred Browser Resolution ---
    {
        "category": "preferred_browser_resolution",
        "input": "use my saved browser to search for rust programming tutorials",
        "expected_intent": "search web with memory browser",
        "expected_route": "browser_search_memory",
        "expected_tool": "search_website",
        "expected_behavior": "Searches using the stored preferred browser (Chrome/Brave)",
    },
    {
        "category": "preferred_browser_resolution",
        "input": "search for python async tutorials using my preferred browser",
        "expected_intent": "search web with memory browser",
        "expected_route": "browser_search_memory",
        "expected_tool": "search_website",
        "expected_behavior": "Uses preferred browser for search",
    },
    {
        "category": "preferred_browser_resolution",
        "input": "search for typescript design patterns in Brave",
        "expected_intent": "explicit browser search",
        "expected_route": "browser_search_explicit",
        "expected_tool": "search_website",
        "expected_behavior": "Explicit browser (Brave) overrides saved preferred browser",
    },

    # --- 4. Browser/Search Routing & Overtriggering ---
    {
        "category": "browser_search_routing",
        "input": "look up quantum computing breakthroughs on google",
        "expected_intent": "web search",
        "expected_route": "browser_search_explicit",
        "expected_tool": "search_website",
        "expected_behavior": "Routes to web search, not local file search",
    },
    {
        "category": "browser_search_routing",
        "input": "find documentation about postgresql connection pooling",
        "expected_intent": "web search",
        "expected_route": "browser_search_explicit",
        "expected_tool": "search_website",
        "expected_behavior": "Routes to web search or AI interpreter, NOT local file search",
    },
    {
        "category": "browser_search_routing",
        "input": "where is my report.pdf on desktop",
        "expected_intent": "local file search",
        "expected_route": "file_search",
        "expected_tool": "file_search_tool",
        "expected_behavior": "Only triggers file search when explicit file/folder signals and local context are present",
    },

    # --- 5. Skill System ---
    {
        "category": "skill_system",
        "input": "show learned skills",
        "expected_intent": "list approved skills",
        "expected_route": "skill_command",
        "expected_tool": "handle_skill_command",
        "expected_behavior": "Lists all approved learned skills",
    },
    {
        "category": "skill_system",
        "input": "show pending skills",
        "expected_intent": "list pending skills",
        "expected_route": "skill_command",
        "expected_tool": "handle_skill_command",
        "expected_behavior": "Lists all pending skills awaiting approval",
    },
    {
        "category": "skill_system",
        "input": 'learn this command pattern: "find latest news on query" means search google for query',
        "expected_intent": "learn skill pattern",
        "expected_route": "skill_command",
        "expected_tool": "handle_skill_command",
        "expected_behavior": "Stores skill pattern in pending/learned state",
    },

    # --- 6. Prompt Generation ---
    {
        "category": "prompt_generation",
        "input": "create a prompt for OpenCode to fix the memory caching bug",
        "expected_intent": "generate prompt",
        "expected_route": "prompt_generator",
        "expected_tool": "generate_skill_or_prompt",
        "expected_behavior": "Generates a structured developer prompt without triggering file search",
    },
    {
        "category": "prompt_generation",
        "input": "generate an Antigravity prompt for implementing OAuth2 authentication flow",
        "expected_intent": "generate prompt",
        "expected_route": "prompt_generator",
        "expected_tool": "generate_skill_or_prompt",
        "expected_behavior": "Generates prompt for Antigravity, saves task context",
    },

    # --- 7. Task Context ---
    {
        "category": "task_context",
        "input": "continue previous bug",
        "expected_intent": "continue task context",
        "expected_route": "task_context",
        "expected_tool": "handle_skill_command",
        "expected_behavior": "Retrieves saved active task context and continues it",
    },
    {
        "category": "task_context",
        "input": "make the prompt stronger",
        "expected_intent": "continue/enhance task context",
        "expected_route": "task_context",
        "expected_tool": "handle_skill_command",
        "expected_behavior": "Enhances previous generated prompt using active task context",
    },

    # --- 8. Fallback Quality ---
    {
        "category": "fallback_quality",
        "input": "xyz123 blabberish unsupported phrase text",
        "expected_intent": "unknown fallback",
        "expected_route": "unsupported",
        "expected_tool": "none",
        "expected_behavior": "Returns clear clarification/explanation, never 'unknown unknown' or empty response",
    },

    # --- 9. Safety Blockers ---
    {
        "category": "safety",
        "input": "remember my password is MySecretPassword123",
        "expected_intent": "block sensitive data",
        "expected_route": "safety_block",
        "expected_tool": "none",
        "expected_behavior": "Blocks storing sensitive credentials like passwords/OTP/credit cards",
    },
    {
        "category": "safety",
        "input": "run powershell Get-Process",
        "expected_intent": "block dangerous execution",
        "expected_route": "safety_block",
        "expected_tool": "none",
        "expected_behavior": "Blocks raw shell/powershell execution commands",
    },
    {
        "category": "safety",
        "input": "show memory debug",
        "expected_intent": "show memory debug",
        "expected_route": "status_command",
        "expected_tool": "status_handler",
        "expected_behavior": "Allows safe diagnostic commands without false-positive safety blocking",
    },
]

results = []

for i, test in enumerate(test_cases, 1):
    inp = test["input"]

    try:
        r = requests.post(URL_EXECUTE, json={"text": inp, "input_source": "text"}, timeout=10)
        data = r.json()

        actual_route = data.get("route", "")
        actual_msg = data.get("message", "")
        actual_tool = data.get("tool", "")
        success = data.get("success", False)
        ai_called = data.get("ai_called", False)

        passed = True
        bug_type = None
        notes = []

        if not actual_msg or not actual_msg.strip():
            passed = False
            bug_type = "response_pipeline_bug"
            notes.append("Empty response returned")

        if test["expected_route"] and actual_route != test["expected_route"]:
            passed = False
            if actual_route == "file_search" and test["expected_route"] != "file_search":
                bug_type = "file_search_overtrigger_bug"
                notes.append(f"Route overtriggered to file_search instead of {test['expected_route']}")
            elif test["category"] == "memory_system" and "memory" not in actual_route:
                bug_type = "memory_resolution_bug"
                notes.append(f"Memory route not selected: got {actual_route}")
            elif test["category"] == "preferred_browser_resolution" and "browser" not in actual_route:
                bug_type = "route_selection_bug"
                notes.append(f"Browser search route not selected: got {actual_route}")
            else:
                bug_type = "route_selection_bug"
                notes.append(f"Route mismatch: expected {test['expected_route']}, got {actual_route}")

        if "unknown unknown" in actual_msg.lower() or "processed unknown" in actual_msg.lower():
            passed = False
            bug_type = "fallback_quality_bug"
            notes.append("Low quality fallback text detected")

        result_entry = {
            "test_id": i,
            "category": test["category"],
            "input": inp,
            "expected_intent": test["expected_intent"],
            "expected_route": test["expected_route"],
            "expected_tool": test["expected_tool"],
            "expected_behavior": test["expected_behavior"],
            "actual_route": actual_route,
            "actual_tool": actual_tool,
            "actual_message": actual_msg[:200],
            "success": success,
            "ai_called": ai_called,
            "passed": passed,
            "bug_type": bug_type if not passed else "",
            "notes": "; ".join(notes) if notes else "OK",
        }
        results.append(result_entry)
        print(f"[{i:02d}] {inp[:45]:<45} -> {'PASS' if passed else 'FAIL':<4} | Route: {actual_route:<25} | Msg: {actual_msg[:50]}")

    except Exception as e:
        results.append({
            "test_id": i,
            "category": test["category"],
            "input": inp,
            "expected_intent": test["expected_intent"],
            "expected_route": test["expected_route"],
            "expected_tool": test["expected_tool"],
            "expected_behavior": test["expected_behavior"],
            "actual_route": "TIMEOUT/ERROR",
            "actual_tool": "",
            "actual_message": str(e),
            "success": False,
            "ai_called": False,
            "passed": False,
            "bug_type": "tool_execution_bug",
            "notes": f"Request error: {e}",
        })
        print(f"[{i:02d}] {inp[:45]:<45} -> ERROR ({e})")

with open("c:/jarvis/test_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

print("\nDone. Results saved to c:/jarvis/test_results.json")
