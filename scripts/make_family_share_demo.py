import json
from pathlib import Path

from sqlmodel import Session

from app.db import init_db, engine
from app.models import Course, EvidenceEvent, Profile
from app.services.family_share_importer import import_course_push, import_progress_pull
from app.services.family_share_packager import build_course_push_zip, build_progress_pull_zip, parse_family_share_zip


def main():
    init_db()
    with Session(engine) as s:
        parent = Profile(display_name='Parent Demo', role='adult', timezone='UTC', day_start_time='06:00')
        kid = Profile(display_name='Kid Demo', role='kid', timezone='UTC', day_start_time='06:00')
        s.add(parent); s.add(kid); s.commit(); s.refresh(parent); s.refresh(kid)

        course = Course(profile_id=parent.id, title='Shared Piano', topic='Piano', learner_profile_json='{}')
        s.add(course); s.commit(); s.refresh(course)

        push_blob = build_course_push_zip(s, parent.id, 'Kid Demo', course.id, include_flashcards=True, include_certificate_template=False, passphrase='demo')
        m1, c1 = parse_family_share_zip(push_blob)
        push_summary = import_course_push(s, m1, c1, 'demo', kid.id)

        s.add(EvidenceEvent(profile_id=kid.id, course_id=course.id, concept_id=1, kind='quiz', score=0.9, meta_json='{}'))
        s.commit()
        pull_blob = build_progress_pull_zip(s, kid.id, course.id, 30, 'demo')
        m2, c2 = parse_family_share_zip(pull_blob)
        pull_summary_1 = import_progress_pull(s, m2, c2, 'demo', parent.id)
        pull_summary_2 = import_progress_pull(s, m2, c2, 'demo', parent.id)

    out = Path('dist'); out.mkdir(parents=True, exist_ok=True)
    p = out / 'family_share_demo_summary.json'
    p.write_text(json.dumps({'course_push': push_summary, 'progress_pull_first': pull_summary_1, 'progress_pull_second': pull_summary_2}, indent=2), encoding='utf-8')
    print(p)


if __name__ == '__main__':
    main()
