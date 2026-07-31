import sys
sys.path.insert(0, "C:\\jarvis\\veyra-openjarvis-base\\src")
from openjarvis.step1.intent_understanding import IntentUnderstanding

iu = IntentUnderstanding()

test_commands = [
    "Give me an overview of JavaScript",
    "I am curious about SQLite",
    "I need a good Vue option",
    "Help me pick a chemistry solution",
    "Where can I find React",
    "I want to use Zoom",
    "I have a question about space exploration",
    "Point me toward something for Flask",
    "Any good options for Linux",
    "Give me a comparison of space exploration and philosophy",
    "Which is better, Kubernetes or blockchain",
    "I want to open Teams",
    "I need info about neuroscience",
    "Help me pick",
    "I need a good neuroscience option",
]

for cmd in test_commands:
    r = iu.understand(cmd)
    print(f"action={r.action} family={r.action_family} target={r.target_family} confidence={r.confidence:.2f} cmd={cmd}")
    normalized = iu._normalize(cmd)
    wrappers = iu._detect_wrappers(normalized)
    if wrappers["removed_phrases"]:
        print(f"  removed: {wrappers['removed_phrases']}")
        print(f"  clean: {wrappers['clean_text']}")
    words = wrappers["clean_text"].split()
    action_result = iu._extract_action_family(words, wrappers["clean_text"])
    print(f"  action_result: {action_result}")
