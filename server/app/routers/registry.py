import json
from datetime import datetime

from fastapi import APIRouter, Body, Depends, Form, HTTPException
from sqlmodel import Session, select

from app.core.auth import get_lan_client, require_local_admin
from app.db import get_session
from app.models import Course, CoursePackageRecord, CourseRegistryItem, RegistrySource
from app.services.course_diff import diff_courses
from app.services.course_merge import apply_merge_decisions, compute_merge_plan
from app.services.registry_scan import grouped_available, install_package, scan_source

router = APIRouter(prefix='/api', tags=['registry'])


@router.post('/registry/sources', dependencies=[Depends(require_local_admin)])
def add_source(kind: str = Form(...), name: str = Form(...), path: str = Form(...), profile_id: int = Form(1), session: Session = Depends(get_session)):
    src = RegistrySource(profile_id=profile_id, kind=kind, name=name, path_or_url=path, enabled=True)
    session.add(src); session.commit(); session.refresh(src)
    return src


@router.get('/registry/sources', dependencies=[Depends(require_local_admin)])
def list_sources(profile_id: int = 1, session: Session = Depends(get_session)):
    return session.exec(select(RegistrySource).where(RegistrySource.profile_id == profile_id)).all()


@router.post('/registry/sources/{source_id}/scan', dependencies=[Depends(require_local_admin)])
def scan(source_id: int, profile_id: int = Form(1), session: Session = Depends(get_session)):
    src = session.get(RegistrySource, source_id)
    if not src:
        raise HTTPException(404, 'Source not found')
    found = scan_source(session, profile_id, src)
    return {'found': len(found)}


@router.get('/registry/available', dependencies=[Depends(require_local_admin)])
def available(profile_id: int = 1, session: Session = Depends(get_session)):
    return grouped_available(session, profile_id)


@router.get('/registry/packages', dependencies=[Depends(require_local_admin)])
def packages(profile_id: int = 1, session: Session = Depends(get_session)):
    return session.exec(select(CoursePackageRecord).where(CoursePackageRecord.profile_id == profile_id)).all()


@router.get('/registry/installed', dependencies=[Depends(require_local_admin)])
def installed(profile_id: int = 1, session: Session = Depends(get_session)):
    items = session.exec(select(CourseRegistryItem).where(CourseRegistryItem.profile_id == profile_id)).all()
    avail = {a['registry_slug']: a for a in grouped_available(session, profile_id)}
    out = []
    for i in items:
        a = avail.get(i.registry_slug, {})
        out.append({**i.model_dump(mode='json'), 'latest_available_version': a.get('latest', i.installed_version), 'has_update': a.get('latest', i.installed_version) != i.installed_version})
    return out


@router.post('/registry/install', dependencies=[Depends(require_local_admin)])
def install(package_record_id: int = Form(...), profile_id: int = Form(1), session: Session = Depends(get_session)):
    return install_package(session, profile_id, package_record_id)


@router.post('/registry/update/prepare', dependencies=[Depends(require_local_admin)])
def prepare_update(registry_slug: str = Form(...), target_version: str = Form(...), profile_id: int = Form(1), session: Session = Depends(get_session)):
    item = session.exec(select(CourseRegistryItem).where(CourseRegistryItem.profile_id == profile_id, CourseRegistryItem.registry_slug == registry_slug)).first()
    rec = session.exec(select(CoursePackageRecord).where(CoursePackageRecord.profile_id == profile_id, CoursePackageRecord.registry_slug == registry_slug, CoursePackageRecord.version == target_version)).first()
    if not item or not rec:
        raise HTTPException(404, 'Registry item/package not found')
    staged = install_package(session, profile_id, rec.id)
    course = session.get(Course, staged['course_id'])
    course.title = f"[STAGED] {course.title}"; session.add(course); session.commit()
    return {'old_course_id': item.course_id, 'staged_course_id': course.id, 'target_version': target_version}


@router.post('/registry/update/commit', dependencies=[Depends(require_local_admin)])
def commit_update(registry_slug: str = Form(...), staged_course_id: int = Form(...), profile_id: int = Form(1), session: Session = Depends(get_session)):
    item = session.exec(select(CourseRegistryItem).where(CourseRegistryItem.profile_id == profile_id, CourseRegistryItem.registry_slug == registry_slug)).first()
    staged = session.get(Course, staged_course_id)
    if not item or not staged:
        raise HTTPException(404, 'Staged or registry item not found')
    old = session.get(Course, item.course_id)
    if old:
        session.add(old)
    staged.title = staged.title.replace('[STAGED] ', '')
    item.course_id = staged.id
    latest = session.exec(select(CoursePackageRecord).where(CoursePackageRecord.profile_id == profile_id, CoursePackageRecord.registry_slug == registry_slug).order_by(CoursePackageRecord.imported_at.desc())).first()
    if latest:
        item.installed_version = latest.version
    session.add(staged); session.add(item); session.commit()
    return {'ok': True, 'course_id': staged.id}


@router.post('/registry/rollback', dependencies=[Depends(require_local_admin)])
def rollback(registry_slug: str = Form(...), version: str = Form(...), profile_id: int = Form(1), session: Session = Depends(get_session)):
    rec = session.exec(select(CoursePackageRecord).where(CoursePackageRecord.profile_id == profile_id, CoursePackageRecord.registry_slug == registry_slug, CoursePackageRecord.version == version)).first()
    if not rec:
        raise HTTPException(404, 'Package version not found')
    return install_package(session, profile_id, rec.id)


@router.get('/registry/diff', dependencies=[Depends(require_local_admin)])
def diff(old_course_id: int, new_course_id: int, session: Session = Depends(get_session)):
    return diff_courses(session, old_course_id, new_course_id)


@router.post('/registry/merge/compute', dependencies=[Depends(require_local_admin)])
def merge_compute(old_course_id: int = Form(...), staged_course_id: int = Form(...), session: Session = Depends(get_session)):
    return compute_merge_plan(session, old_course_id, staged_course_id)


@router.post('/registry/merge/apply', dependencies=[Depends(require_local_admin)])
def merge_apply(staged_course_id: int = Form(...), decisions_json: str = Form('[]'), session: Session = Depends(get_session)):
    return apply_merge_decisions(session, staged_course_id, json.loads(decisions_json))


# optional LAN catalog
_LAN_CATALOG_ENABLED = False


@router.post('/lan/catalog/enable', dependencies=[Depends(require_local_admin)])
def lan_catalog_enable(enabled: bool = Form(True)):
    global _LAN_CATALOG_ENABLED
    _LAN_CATALOG_ENABLED = enabled
    return {'enabled': _LAN_CATALOG_ENABLED}


@router.get('/lan/catalog/list')
def lan_catalog_list(client=Depends(get_lan_client), session: Session = Depends(get_session)):
    if not _LAN_CATALOG_ENABLED:
        raise HTTPException(403, 'LAN catalog disabled')
    return grouped_available(session, client.profile_id_optional or 1)


@router.post('/lan/catalog/request')
def lan_catalog_request(registry_slug: str = Form(...), version: str = Form(...), client=Depends(get_lan_client), session: Session = Depends(get_session)):
    if not _LAN_CATALOG_ENABLED:
        raise HTTPException(403, 'LAN catalog disabled')
    rec = session.exec(select(CoursePackageRecord).where(CoursePackageRecord.registry_slug == registry_slug, CoursePackageRecord.version == version)).first()
    if not rec:
        raise HTTPException(404, 'Package not found')
    return {'ok': True, 'file_path': rec.file_path}
