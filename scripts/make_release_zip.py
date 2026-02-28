from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'dist' / 'growora-github-ready.zip'

EXCLUDE_PARTS = {
    '.git',
    '.venv',
    'node_modules',
    '__pycache__',
    '.pytest_cache',
}
EXCLUDE_SUFFIXES = {'.pyc', '.pyo'}


def should_skip(rel: Path) -> bool:
    if any(part in EXCLUDE_PARTS for part in rel.parts):
        return True
    # keep generated release output directory excluded from recursive input
    if rel.parts and rel.parts[0] == 'dist':
        return True
    # keep runtime mutable data out of source release artifact
    if len(rel.parts) >= 2 and rel.parts[0] == 'server' and rel.parts[1] == 'data':
        return True
    if rel.suffix in EXCLUDE_SUFFIXES:
        return True
    return False


OUT.parent.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED) as zf:
    for p in ROOT.rglob('*'):
        rel = p.relative_to(ROOT)
        if should_skip(rel):
            continue
        if p.is_file():
            zf.write(p, rel.as_posix())

print(OUT)
