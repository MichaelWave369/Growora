import json
import zipfile
from pathlib import Path

from sqlmodel import Session, select

from app.db import init_db, engine
from app.models import CourseEditLog, RegistrySource
from app.services.course_diff import diff_courses
from app.services.course_merge import apply_merge_decisions, compute_merge_plan
from app.services.registry_scan import install_package, scan_source


def write_pkg(path: Path, slug: str, version: str, lesson_text: str):
    manifest = {'format': 'triad369-course@1', 'registry_slug': slug, 'version': version, 'title': 'Demo Algebra', 'topic': 'Math'}
    course = {'course': {'title': 'Demo Algebra', 'topic': 'Math', 'learner_profile_json': '{}'}, 'lessons': [{'title': 'Lesson 1', 'content_md': lesson_text, 'exercises_json': ['Q1'], 'quiz_json': {'questions':[{'q':'1+1'}]}}]}
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('manifest.json', json.dumps(manifest))
        zf.writestr('course.json', json.dumps(course))


def main():
    init_db()
    fixture = Path('dist/registry_demo')
    fixture.mkdir(parents=True, exist_ok=True)
    write_pkg(fixture / 'demo-algebra-1.0.0.triad369.zip', 'demo-algebra', '1.0.0', '# Intro\nA')
    write_pkg(fixture / 'demo-algebra-1.1.0.triad369.zip', 'demo-algebra', '1.1.0', '# Intro\nA plus update')

    with Session(engine) as s:
        src = RegistrySource(profile_id=1, kind='folder', name='demo', path_or_url=str(fixture))
        s.add(src); s.commit(); s.refresh(src)
        scan_source(s, 1, src)
        from app.models import CoursePackageRecord
        v1 = s.exec(select(CoursePackageRecord).where(CoursePackageRecord.registry_slug=='demo-algebra', CoursePackageRecord.version=='1.0.0')).first()
        v2 = s.exec(select(CoursePackageRecord).where(CoursePackageRecord.registry_slug=='demo-algebra', CoursePackageRecord.version=='1.1.0')).first()
        inst = install_package(s, 1, v1.id)
        old_id = inst['course_id']

        # simulate local edit
        from app.models import Lesson
        l = s.exec(select(Lesson).where(Lesson.course_id == old_id)).first()
        l.content_md += '\nLOCAL EDIT'
        l.user_edited = True
        s.add(l); s.add(CourseEditLog(profile_id=1, course_id=old_id, lesson_id=l.id, edit_kind='content', base_version='1.0.0')); s.commit()

        st = install_package(s, 1, v2.id)
        staged_id = st['course_id']
        d = diff_courses(s, old_id, staged_id)
        plan = compute_merge_plan(s, old_id, staged_id)
        applied = apply_merge_decisions(s, staged_id, [{'lesson_title':'Lesson 1','decision':'keep_local'}])

    out = Path('dist/registry_demo_summary.json')
    out.write_text(json.dumps({'installed_v1': old_id, 'staged_v11': staged_id, 'diff_summary': d['summary'], 'conflicts': plan['conflicts'], 'merge_apply': applied}, indent=2), encoding='utf-8')
    print(out)


if __name__ == '__main__':
    main()
