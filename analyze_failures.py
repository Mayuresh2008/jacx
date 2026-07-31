import sys
sys.path.insert(0, "C:\\jarvis\\veyra-openjarvis-base\\src")
import os
os.environ["ENABLE_SUPABASE"] = "true"
os.environ["ENABLE_STEP_1_BASIC_COMMANDS"] = "true"
os.environ["ENABLE_LOCAL_APP_OPENING"] = "true"
os.environ["ENABLE_STEP_2_BROWSER_SEARCH"] = "true"
os.environ["ENABLE_LOCAL_WEBSITE_OPENING"] = "true"
os.environ["ENABLE_LOCAL_BROWSER_SEARCH"] = "true"
from openjarvis.step1.intent_pipeline import get_intent_pipeline
import sys
sys.path.insert(0, "C:\\jarvis\\jacx_qa\\scripts")
from intelligence_evaluation import generate_commands, get_expected_intent

pipeline = get_intent_pipeline()
commands = generate_commands()

unknown_fails = []
learn_fails = []
for cmd in commands:
    exp = get_expected_intent(cmd)
    cat = exp.get("category", "unknown")
    result = pipeline.run(cmd)
    pipeline_action = result.intent_action
    
    if cat == "unknown" and pipeline_action in ("", "unknown"):
        unknown_fails.append({"cmd": cmd, "pipeline_action": pipeline_action, "pipeline_route": result.route})
    elif cat == "learn" and pipeline_action not in ("learn", "search", "explain", "describe", "teach", "ask", "what", "how", "why"):
        learn_fails.append({"cmd": cmd, "pipeline_action": pipeline_action, "pipeline_route": result.route})

print(f"=== Unknown category failures: {len(unknown_fails)} ===")
from collections import Counter
action_counts = Counter(x["pipeline_action"] for x in unknown_fails)
route_counts = Counter(x["pipeline_route"] for x in unknown_fails)
print("Pipeline actions:", action_counts.most_common(10))
print("Pipeline routes:", route_counts.most_common(10))
print("\nSample unknown failures:")
for x in unknown_fails[:20]:
    pa = x["pipeline_action"]
    pr = x["pipeline_route"]
    cmd = x["cmd"][:70]
    print(f"  [{pa:>12}|{pr:>25}] {cmd}")

print(f"\n=== Learn category failures: {len(learn_fails)} ===")
action_counts = Counter(x["pipeline_action"] for x in learn_fails)
route_counts = Counter(x["pipeline_route"] for x in learn_fails)
print("Pipeline actions:", action_counts.most_common(10))
print("Pipeline routes:", route_counts.most_common(10))
print("\nSample learn failures:")
for x in learn_fails[:20]:
    pa = x["pipeline_action"]
    pr = x["pipeline_route"]
    cmd = x["cmd"][:70]
    print(f"  [{pa:>12}|{pr:>25}] {cmd}")
