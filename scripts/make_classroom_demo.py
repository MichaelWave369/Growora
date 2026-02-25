import json
from pathlib import Path

out = Path('dist')
out.mkdir(parents=True, exist_ok=True)
demo = {
    'classroom': {'name': 'Demo Classroom'},
    'session': {'title': 'Fractions Live Session', 'mode': 'live'},
    'events': [
        {'type': 'draw', 'payload': {'x': 10, 'y': 20}},
        {'type': 'present', 'payload': {'deck_id': 1, 'slide_index': 1}},
        {'type': 'quiz_answer', 'payload': {'profile_id': 2, 'score': 0.8}},
        {'type': 'teachback_submit', 'payload': {'profile_id': 2}},
    ]
}
path = out / 'classroom_demo.json'
path.write_text(json.dumps(demo, indent=2), encoding='utf-8')
print(path)
