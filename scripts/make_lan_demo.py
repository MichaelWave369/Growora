import json
import random
import string
from pathlib import Path

code = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(8))
obj = {
    'classroom': {'id': 1, 'name': 'LAN Multiplayer Demo'},
    'session': {'id': 1, 'title': 'LAN Demo Session'},
    'room_code': code,
    'join_link': f'http://192.168.1.10:8000/join/{code}'
}
out = Path('dist')
out.mkdir(parents=True, exist_ok=True)
path = out / 'lan_demo.json'
path.write_text(json.dumps(obj, indent=2), encoding='utf-8')
print(path)
print(obj['join_link'])
