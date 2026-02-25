import json
from pathlib import Path

out = Path('dist')
out.mkdir(parents=True, exist_ok=True)
pack = {
    'manifest': {'format': 'triad369-course@1', 'title': 'Demo Guitar Course'},
    'skill_graph_snapshot': {
        'concepts': [{'id': 1, 'title': 'Chords'}, {'id': 2, 'title': 'Rhythm'}],
        'edges': [{'src': 1, 'dst': 2, 'kind': 'prereq'}]
    }
}
path = out / 'demo_triad369_with_skillgraph.json'
path.write_text(json.dumps(pack, indent=2), encoding='utf-8')
print(path)
