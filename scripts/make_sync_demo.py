import json
from pathlib import Path

from sqlmodel import Session

from app.db import init_db, engine
from app.models import EvidenceEvent, Profile
from app.services.sync_merge import merge_sync_payload
from app.services.sync_packager import build_sync_zip, parse_sync_zip


def main():
    init_db()
    with Session(engine) as s:
        p1 = Profile(display_name='Sync A', role='adult', timezone='UTC', day_start_time='06:00')
        p2 = Profile(display_name='Sync B', role='adult', timezone='UTC', day_start_time='06:00')
        s.add(p1); s.add(p2); s.commit(); s.refresh(p1); s.refresh(p2)
        s.add(EvidenceEvent(profile_id=p1.id, course_id=1, concept_id=1, kind='quiz', score=0.9, meta_json='{}'))
        s.commit()

        blob = build_sync_zip(s, p1.id, 'learning_record_only', days=30, events=200, passphrase='demo-pass')
        manifest, cipher = parse_sync_zip(blob)
        first = merge_sync_payload(s, manifest, cipher, passphrase='demo-pass', target_profile_id=p2.id)
        second = merge_sync_payload(s, manifest, cipher, passphrase='demo-pass', target_profile_id=p2.id)

    out = Path('dist')
    out.mkdir(parents=True, exist_ok=True)
    path = out / 'sync_demo_summary.json'
    path.write_text(json.dumps({'first_import': first, 'second_import': second}, indent=2), encoding='utf-8')
    print(path)
    print('Idempotent import demonstration complete')


if __name__ == '__main__':
    main()
