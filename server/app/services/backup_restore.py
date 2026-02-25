import json
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

from sqlmodel import Session

from app.models import Profile


def create_backup(include_attachments: bool = False, include_exports: bool = True) -> Path:
    out_dir = Path('server/data/exports'); out_dir.mkdir(parents=True, exist_ok=True)
    zpath = out_dir / f"backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.zip"
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as zf:
        db = Path('server/data/growora.db')
        if db.exists(): zf.write(db, 'growora.db')
        meta = {'created_at': datetime.utcnow().isoformat(), 'include_attachments': include_attachments, 'include_exports': include_exports}
        zf.writestr('backup_meta.json', json.dumps(meta, indent=2))
        if include_attachments:
            up = Path('server/data/uploads')
            for p in up.glob('*'):
                if p.is_file(): zf.write(p, f'uploads/{p.name}')
        if include_exports:
            ex = Path('server/data/exports')
            for p in ex.glob('*.zip'):
                if p != zpath: zf.write(p, f'exports/{p.name}')
    return zpath


def restore_backup(session: Session, backup_zip: Path, overwrite: bool = False):
    with zipfile.ZipFile(backup_zip, 'r') as zf:
        if overwrite and 'growora.db' in zf.namelist():
            Path('server/data/growora.db').write_bytes(zf.read('growora.db'))
            return {'mode': 'overwrite'}
        p = Profile(display_name=f"Restored - {datetime.utcnow().date()}", role='adult', timezone='UTC', day_start_time='06:00')
        session.add(p); session.commit(); session.refresh(p)
        return {'mode': 'new_profile', 'profile_id': p.id}
