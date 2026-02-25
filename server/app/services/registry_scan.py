import hashlib
import json
import re
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

from sqlmodel import Session, select

from app.models import Course, CoursePackageRecord, CourseRegistryItem, Lesson, RegistrySource, Week

PKG_DIR = Path('server/data/registry/packages')


def _parse_semver(v: str):
    m = re.match(r'^(\d+)\.(\d+)\.(\d+)', (v or '').strip())
    if not m:
        return (0, 0, 0)
    return tuple(int(x) for x in m.groups())


def _sha256(path: Path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def read_course_package(path: Path):
    with zipfile.ZipFile(path, 'r') as zf:
        if 'manifest.json' not in zf.namelist():
            raise ValueError('manifest.json missing')
        manifest = json.loads(zf.read('manifest.json').decode('utf-8'))
        payload = json.loads(zf.read('course.json').decode('utf-8')) if 'course.json' in zf.namelist() else {}
    return manifest, payload


def scan_source(session: Session, profile_id: int, source: RegistrySource):
    base = Path(source.path_or_url)
    if not base.exists() or not base.is_dir():
        raise ValueError('Source path not found')
    found = []
    for p in sorted(base.glob('*.zip')):
        if not (p.name.endswith('.triad369.zip') or p.name.endswith('.course.zip') or p.name.endswith('.zip')):
            continue
        try:
            manifest, _ = read_course_package(p)
        except Exception:
            continue
        slug = manifest.get('registry_slug') or manifest.get('slug') or p.stem
        version = manifest.get('version', '0.0.0')
        dst = PKG_DIR / f'{slug}-{version}.zip'
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not dst.exists():
            shutil.copy2(p, dst)
        rec = session.exec(select(CoursePackageRecord).where(CoursePackageRecord.profile_id == profile_id, CoursePackageRecord.registry_slug == slug, CoursePackageRecord.version == version)).first()
        if not rec:
            rec = CoursePackageRecord(profile_id=profile_id, registry_slug=slug, version=version, file_path=str(dst), sha256=_sha256(dst))
        else:
            rec.file_path = str(dst); rec.sha256 = _sha256(dst); rec.imported_at = datetime.utcnow()
        session.add(rec); found.append(rec)
    source.last_scan_at = datetime.utcnow(); session.add(source); session.commit()
    return found


def grouped_available(session: Session, profile_id: int):
    records = session.exec(select(CoursePackageRecord).where(CoursePackageRecord.profile_id == profile_id)).all()
    grouped = {}
    for r in records:
        g = grouped.setdefault(r.registry_slug, {'registry_slug': r.registry_slug, 'versions': [], 'latest': '0.0.0'})
        g['versions'].append(r.version)
    for g in grouped.values():
        g['versions'] = sorted(set(g['versions']), key=_parse_semver)
        g['latest'] = g['versions'][-1] if g['versions'] else '0.0.0'
    return sorted(grouped.values(), key=lambda x: x['registry_slug'])


def install_package(session: Session, profile_id: int, package_record_id: int):
    rec = session.get(CoursePackageRecord, package_record_id)
    if not rec:
        raise ValueError('Package record not found')
    manifest, payload = read_course_package(Path(rec.file_path))
    cdata = payload.get('course') or {}
    course = Course(
        profile_id=profile_id,
        title=cdata.get('title') or manifest.get('title') or rec.registry_slug,
        topic=cdata.get('topic') or manifest.get('topic') or 'Imported',
        learner_profile_json=cdata.get('learner_profile_json', '{}'),
        day_start_time=cdata.get('day_start_time', '06:00'),
        days_per_week=int(cdata.get('days_per_week', 5)),
        minutes_per_day=int(cdata.get('minutes_per_day', 30)),
        difficulty=cdata.get('difficulty', 'beginner'),
        auto_use_library=bool(cdata.get('auto_use_library', False)),
        context_doc_ids_json='[]',
    )
    session.add(course); session.commit(); session.refresh(course)
    week = Week(course_id=course.id, index=1, objectives_json=json.dumps(['Imported']))
    session.add(week); session.commit(); session.refresh(week)
    lessons = payload.get('lessons') or []
    if not lessons:
        lessons = [{'title': 'Intro', 'content_md': '# Intro', 'exercises_json': ['Read'], 'quiz_json': {'questions': []}}]
    for i, l in enumerate(lessons, start=1):
        session.add(Lesson(course_id=course.id, week_id=week.id, day_index=i, order_index=i, title=l.get('title','Lesson'), content_md=l.get('content_md','# Lesson'), exercises_json=json.dumps(l.get('exercises_json',[])), quiz_json=json.dumps(l.get('quiz_json',{'questions':[]}))))
    session.commit()

    item = session.exec(select(CourseRegistryItem).where(CourseRegistryItem.profile_id == profile_id, CourseRegistryItem.registry_slug == rec.registry_slug)).first()
    if not item:
        item = CourseRegistryItem(profile_id=profile_id, course_id=course.id, registry_slug=rec.registry_slug, title=course.title, topic=course.topic, source='imported', installed_version=rec.version, package_format=manifest.get('format','triad369-course@1'), upstream_id_optional=str(manifest.get('course_id') or ''))
    else:
        item.course_id = course.id; item.title = course.title; item.topic = course.topic; item.installed_version = rec.version
    item.last_checked_at = datetime.utcnow()
    session.add(item); session.commit(); session.refresh(item)
    return {'course_id': course.id, 'installed_version': rec.version, 'registry_slug': rec.registry_slug}
