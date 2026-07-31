import requests, json

url = 'http://127.0.0.1:8000/v1/step1/commands/execute'

tests = [
    ('open youtube', 'Exact parser - open website'),
    ('go to steam', 'NLU - flexible open'),
    ('find me the best react dashboards on github', 'AI fallback - complex search'),
    ('create a spreadsheet called budget tracker', 'NLU - file creation'),
    ('what is the capital of France', 'Fallthrough - general question'),
]

for cmd, desc in tests:
    try:
        r = requests.post(url, json={'text': cmd, 'input_source': 'text'}, timeout=120)
        data = r.json()
        print(f'--- {desc} ---')
        print(f'  Input: {cmd}')
        print(f'  Success: {data.get("success")}, Route: {data.get("route", "?")}, AI: {data.get("ai_called", False)}')
        msg = data.get('message', '')
        print(f'  Message: {msg[:150]}')
        print()
    except Exception as e:
        print(f'  ERROR: {e}')
