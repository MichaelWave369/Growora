from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'dist' / 'growora-github-ready.zip'
EXCLUDE_DIRS = {'.git', '.venv', 'node_modules', 'dist', 'server/data'}

OUT.parent.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED) as zf:
    for p in ROOT.rglob('*'):
        rel = p.relative_to(ROOT)
        if any(str(rel).startswith(x) for x in EXCLUDE_DIRS):
            continue
        if p.is_file():
            zf.write(p, rel.as_posix())
print(OUT)
