import json
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.db import engine
from app.main import app
from app.models import Course, CourseEditLog, CoursePackageRecord, Lesson, RegistrySource

client = TestClient(app)


def mk_profile(name):
    return client.post('/api/profiles', json={'display_name': name, 'role':'adult', 'timezone':'UTC', 'day_start_time':'06:00'}).json()['id']


def _write_pkg(path: Path, slug: str, version: str, text: str):
    manifest = {'format':'triad369-course@1','registry_slug':slug,'version':version,'title':'Demo','topic':'Math'}
    payload = {'course': {'title':'Demo','topic':'Math','learner_profile_json':'{}'}, 'lessons':[{'title':'L1','content_md':text,'exercises_json':['x'],'quiz_json':{'questions':[{'q':'1+1'}]}}]}
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('manifest.json', json.dumps(manifest))
        zf.writestr('course.json', json.dumps(payload))


def test_registry_scan_grouping_install_update_diff_merge(tmp_path):
    pid = mk_profile('RegUser')
    srcdir = tmp_path / 'registry'
    srcdir.mkdir()
    _write_pkg(srcdir / 'demo-1.0.0.triad369.zip', 'demo-course', '1.0.0', '# A')
    _write_pkg(srcdir / 'demo-1.1.0.triad369.zip', 'demo-course', '1.1.0', '# A updated')

    add = client.post('/api/registry/sources', data={'kind':'folder','name':'tmp','path':str(srcdir),'profile_id':str(pid)})
    assert add.status_code == 200
    sid = add.json()['id']
    scan = client.post(f'/api/registry/sources/{sid}/scan', data={'profile_id':str(pid)})
    assert scan.status_code == 200

    av = client.get(f'/api/registry/available?profile_id={pid}')
    assert av.status_code == 200
    g = av.json()[0]
    assert g['registry_slug'] == 'demo-course'
    assert g['latest'] == '1.1.0'

    pkgs = client.get(f'/api/registry/packages?profile_id={pid}').json()
    p1 = [p for p in pkgs if p['version'] == '1.0.0'][0]
    p2 = [p for p in pkgs if p['version'] == '1.1.0'][0]

    inst = client.post('/api/registry/install', data={'package_record_id':str(p1['id']),'profile_id':str(pid)})
    assert inst.status_code == 200
    old_course_id = inst.json()['course_id']

    # simulate local edit log
    with Session(engine) as s:
        l = s.exec(select(Lesson).where(Lesson.course_id == old_course_id)).first()
        l.content_md += '\nlocal'
        l.user_edited = True
        s.add(l)
        s.add(CourseEditLog(profile_id=pid, course_id=old_course_id, lesson_id=l.id, edit_kind='content', base_version='1.0.0'))
        s.commit()

    prep = client.post('/api/registry/update/prepare', data={'registry_slug':'demo-course','target_version':'1.1.0','profile_id':str(pid)})
    assert prep.status_code == 200
    staged_id = prep.json()['staged_course_id']

    d = client.get(f'/api/registry/diff?old_course_id={old_course_id}&new_course_id={staged_id}')
    assert d.status_code == 200
    assert d.json()['summary']['lessons_changed'] >= 1

    plan = client.post('/api/registry/merge/compute', data={'old_course_id':str(old_course_id),'staged_course_id':str(staged_id)})
    assert plan.status_code == 200
    decisions = [{'lesson_title':'L1','decision':'keep_local'}]
    apply = client.post('/api/registry/merge/apply', data={'staged_course_id':str(staged_id),'decisions_json':json.dumps(decisions)})
    assert apply.status_code == 200

    commit = client.post('/api/registry/update/commit', data={'registry_slug':'demo-course','staged_course_id':str(staged_id),'profile_id':str(pid)})
    assert commit.status_code == 200

    rb = client.post('/api/registry/rollback', data={'registry_slug':'demo-course','version':'1.0.0','profile_id':str(pid)})
    assert rb.status_code == 200


def test_lan_catalog_list_requires_auth():
    r = client.get('/api/lan/catalog/list')
    assert r.status_code in (401, 403)
