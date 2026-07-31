import requests, json

url = 'http://127.0.0.1:8000/v1/step1/commands/execute'

tests = [
    ('please open github and look for flask tutorials', 'AI fallback - compound command'),
    ('I need you to search for python courses on udemy', 'AI fallback - polite command'),
    ('search for funny cat videos on youtube', 'NLU - search on platform'),
    ('who are you', 'Conversational - should not reach backend'),
]

for cmd, desc in tests:
    try:
        r = requests.post(url, json={'text': cmd, 'input_source': 'text'}, timeout=120)
        data = r.json()
        print(f'--- {desc} ---')
        print(f'  Input: {cmd}')
        print(f'  Success: {data.get("success")}, Route: {data.get("route", "?")}, AI: {data.get("ai_called", False)}')
        msg = data.get('message', '')
        print(f'  Message: {msg[:200]}')
        print()
    except Exception as e:
        print(f'  ERROR: {e}')
