import sys, os, re, time
sys.path.insert(0, 'veyra-openjarvis-base/src')
sys.path.insert(0, 'jacx_qa/scripts')
os.environ['ENABLE_SUPABASE'] = 'true'
os.environ['ENABLE_STEP_1_BASIC_COMMANDS'] = 'true'
os.environ['ENABLE_LOCAL_APP_OPENING'] = 'true'
os.environ['ENABLE_STEP_2_BROWSER_SEARCH'] = 'true'
os.environ['ENABLE_LOCAL_WEBSITE_OPENING'] = 'true'
os.environ['ENABLE_LOCAL_BROWSER_SEARCH'] = 'true'
os.environ['OMNIROUTE_ENABLED'] = 'false'

from intelligence_evaluation import get_expected_intent, _setup_direct_pipeline
from openjarvis.step1.intent_pipeline import get_pipeline_debugger

pipeline = _setup_direct_pipeline()

pipeline_to_expected = {
    "remember": "write", "record": "write", "save": "write", "store": "write",
    "note": "write", "list": "read", "display": "read", "show": "read",
    "view": "read", "retain": "write", "memorize": "write", "log": "write",
    "keep": "write", "discard": "delete", "drop": "delete", "unlearn": "delete",
    "clear": "delete", "remove": "delete", "forget": "delete",
    "change": "write", "update": "write", "set": "write", "modify": "write",
    "edit": "write", "adjust": "write", "configure": "write", "switch": "write",
    "toggle": "write", "enable": "write", "disable": "write",
    "grasp": "learn", "ask": "learn", "explain": "learn", "describe": "learn",
    "clarify": "learn", "summarize": "learn", "understand": "learn",
    "teach": "learn", "tell": "learn", "study": "learn", "master": "learn",
    "vs": "compare", "evaluate": "compare", "assess": "compare",
    "contrast": "compare", "review": "compare", "analyze": "compare",
    "versus": "compare", "propose": "recommend", "suggest": "recommend",
    "advise": "recommend", "setup": "create", "generate": "create",
    "launch": "open", "fire": "open", "initiate": "open", "begin": "open",
    "trigger": "open", "proceed": "continue", "carry on": "continue",
    "keep going": "continue", "resume": "continue",
    "status": "show", "plan": "create",
    "deny": "reject", "decline": "reject", "refuse": "reject",
    "abort": "reject", "stop": "reject", "cancel": "reject",
    "accept": "approve", "confirm": "approve", "validate": "approve",
    "authorize": "approve", "permit": "approve", "allow": "approve",
}

test_cases = [
    ("Remember my preference for dark mode", "memory"),
    ("I usually use Celsius for temperature unit", "memory"),
    ("Toggle my preferred browser to Chrome", "memory"),
    ("List my saved items", "memory"),
    ("Can you change my theme to light theme", "memory"),
    ("Discard my default news source preference", "memory"),
    ("Stop remembering my default news source", "reject"),
    ("Cancel that", "reject"),
    ("Create a new file", "create"),
    ("Write a PDF about Kafka", "create"),
    ("Compose a text file for JavaScript", "create"),
    ("Describe philosophy in detail", "learn"),
    ("Teach me Linux", "learn"),
    ("Why is Prometheus important", "learn"),
    ("Quantum computing vs Apache", "compare"),
    ("Any good options for Linux", "recommend"),
    ("Propose something for Azure", "recommend"),
    ("Keep going", "continue"),
    ("I need to search blockchain on Opera", "search"),
]

for cmd, expected_cat in test_cases:
    exp = get_expected_intent(cmd)
    response = pipeline.run(cmd)
    trace = get_pipeline_debugger().get_trace()

    actual_action = ""
    actual_confidence = 0.0
    for stage in trace.get("stages", []):
        if stage.get("stage") == "intent_understanding":
            m = re.search(r"action=(\S+)", stage.get("output", ""))
            if m:
                actual_action = m.group(1)
            m2 = re.search(r"confidence=([\d.]+)", stage.get("output", ""))
            if m2:
                actual_confidence = float(m2.group(1))

    normalized = pipeline_to_expected.get(actual_action, actual_action)
    expected_action = exp["action"]
    expected_route = exp["route"]
    actual_route = getattr(response, "route", "")

    intent_ok = (normalized == expected_action)
    route_ok = (expected_route == actual_route)
    memory_ok = True
    clarification_ok = True

    if expected_cat == "memory":
        memory_ok = actual_action in ("write", "read", "update", "delete", "show", "remember", "save", "store", "list", "display", "modify", "change", "toggle", "record", "note", "log", "keep", "retain", "memorize")
    elif expected_cat == "reject":
        memory_ok = True
    elif expected_cat == "create":
        memory_ok = True
    elif expected_cat == "learn":
        memory_ok = True
    elif expected_cat == "compare":
        memory_ok = True
    elif expected_cat == "recommend":
        memory_ok = True
    elif expected_cat == "continue":
        memory_ok = True
    elif expected_cat == "search":
        memory_ok = True
    else:
        memory_ok = True

    overall_ok = intent_ok and route_ok and memory_ok and clarification_ok
    status = "OK" if overall_ok else "FAIL"
    fail_reasons = []
    if not intent_ok:
        fail_reasons.append(f"intent({normalized}!={expected_action})")
    if not route_ok:
        def normalize_route(rt):
            return rt.replace("_memory", "").replace("_explicit", "")
        norm_exp = normalize_route(expected_route)
        norm_act = normalize_route(actual_route)
        fail_reasons.append(f"route({actual_route}!={expected_route} norm:{norm_act}!={norm_exp} match={norm_act==norm_exp})")
    if not memory_ok:
        fail_reasons.append("memory")
    if not clarification_ok:
        fail_reasons.append("clarification")

    print(f"[{status:4s}] {cmd[:45]:45s} => exp_action={expected_action:10s} act_action={actual_action:15s} norm={normalized:10s} exp_route={expected_route:20s} act_route={actual_route:20s} {' '.join(fail_reasons)}")
