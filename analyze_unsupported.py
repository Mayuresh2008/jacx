import sys
sys.path.insert(0, "C:\\jarvis\\veyra-openjarvis-base\\src")
sys.path.insert(0, "C:\\jarvis\\jacx_qa\\scripts")
import os
os.environ["ENABLE_SUPABASE"] = "true"
os.environ["ENABLE_STEP_1_BASIC_COMMANDS"] = "true"
os.environ["ENABLE_LOCAL_APP_OPENING"] = "true"
os.environ["ENABLE_STEP_2_BROWSER_SEARCH"] = "true"
os.environ["ENABLE_LOCAL_WEBSITE_OPENING"] = "true"
from openjarvis.step1.intent_pipeline import get_intent_pipeline
from intelligence_evaluation import generate_commands, get_expected_intent

pipeline = get_intent_pipeline()
commands = generate_commands()

unsupported_cmds = []
for cmd in commands:
    exp = get_expected_intent(cmd)
    if exp.get("category") == "unknown":
        result = pipeline.run(cmd)
        if result.route == "unsupported":
            unsupported_cmds.append({
                "cmd": cmd,
                "target": result.intent_target,
                "confidence": result.route_confidence,
                "action": result.intent_action,
            })

from collections import Counter
target_counts = Counter(x["target"] for x in unsupported_cmds)
print("=== Targets for unsupported unknown commands ===")
for target, count in target_counts.most_common(10):
    print(f"  {target}: {count}")

print(f"\n=== Total unsupported unknown: {len(unsupported_cmds)} ===")
print("\n=== Sample commands (first 30) ===")
for x in unsupported_cmds[:30]:
    print(f"  [{x['target']:>12}|{x['confidence']:.2f}] {x['cmd'][:80]}")

print("\n=== Commands with empty action (first 30) ===")
empty_action = [x for x in unsupported_cmds if not x["action"]]
for x in empty_action[:30]:
    print(f"  [{x['target']:>12}|{x['confidence']:.2f}] {x['cmd'][:80]}")
