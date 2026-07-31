import sys, os
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

pipeline = _setup_direct_pipeline()

def normalize_route(rt):
    return rt.replace("_memory", "").replace("_explicit", "")

test_cases = [
    "Describe philosophy in detail",
    "Teach me Linux",
    "Why is Prometheus important",
    "Quantum computing vs Apache",
    "Propose something for Azure",
    "I need to search blockchain on Opera",
    "Write a PDF about Kafka",
]

for cmd in test_cases:
    exp = get_expected_intent(cmd)
    response = pipeline.run(cmd)
    actual_route = getattr(response, "route", "")
    expected_route = exp["route"]
    norm_actual = normalize_route(actual_route)
    norm_expected = normalize_route(expected_route)
    match = norm_expected == norm_actual
    print(f"{cmd[:45]:45s} => exp={expected_route:25s} act={actual_route:25s} norm_exp={norm_expected:20s} norm_act={norm_actual:20s} match={match}")
