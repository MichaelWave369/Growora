import json

from sqlmodel import Session, select

from app.models import CourseEditLog, CourseMergePlan, Lesson


def compute_merge_plan(session: Session, old_course_id: int, staged_course_id: int):
    old_lessons = session.exec(select(Lesson).where(Lesson.course_id == old_course_id)).all()
    staged_lessons = session.exec(select(Lesson).where(Lesson.course_id == staged_course_id)).all()
    old_by_title = {l.title: l for l in old_lessons}
    staged_by_title = {l.title: l for l in staged_lessons}

    edits = session.exec(select(CourseEditLog).where(CourseEditLog.course_id == old_course_id)).all()
    edited_ids = {e.lesson_id for e in edits}

    conflicts = []
    merged = []
    for title, s in staged_by_title.items():
        o = old_by_title.get(title)
        if not o:
            merged.append({'title': title, 'action': 'add'})
            continue
        locally_edited = o.id in edited_ids or o.user_edited
        upstream_changed = (o.content_md != s.content_md) or (o.quiz_json != s.quiz_json)
        if locally_edited and upstream_changed:
            conflicts.append({'lesson_title': title, 'old_lesson_id': o.id, 'staged_lesson_id': s.id, 'options': ['keep_local', 'take_upstream', 'auto_merge']})
        else:
            merged.append({'title': title, 'action': 'accept_upstream'})

    plan = {'old_course_id': old_course_id, 'staged_course_id': staged_course_id, 'conflicts': conflicts, 'merged': merged}
    rec = CourseMergePlan(staged_course_id=staged_course_id, old_course_id=old_course_id, detail_json=json.dumps(plan))
    session.add(rec); session.commit(); session.refresh(rec)
    plan['plan_id'] = rec.id
    return plan


def apply_merge_decisions(session: Session, staged_course_id: int, decisions: list[dict]):
    plan_rec = session.exec(select(CourseMergePlan).where(CourseMergePlan.staged_course_id == staged_course_id).order_by(CourseMergePlan.id.desc())).first()
    if not plan_rec:
        raise ValueError('No merge plan found')
    plan = json.loads(plan_rec.detail_json or '{}')
    old_course_id = plan.get('old_course_id')

    old_lessons = session.exec(select(Lesson).where(Lesson.course_id == old_course_id)).all()
    staged_lessons = session.exec(select(Lesson).where(Lesson.course_id == staged_course_id)).all()
    old_by_id = {l.id: l for l in old_lessons}
    staged_by_id = {l.id: l for l in staged_lessons}

    dec_by_title = {d['lesson_title']: d['decision'] for d in decisions}
    for c in plan.get('conflicts', []):
        title = c['lesson_title']
        decision = dec_by_title.get(title, 'keep_local')
        old_l = old_by_id.get(c['old_lesson_id'])
        staged_l = staged_by_id.get(c['staged_lesson_id'])
        if not old_l or not staged_l:
            continue
        if decision == 'keep_local':
            staged_l.content_md = old_l.content_md
            staged_l.quiz_json = old_l.quiz_json
            staged_l.exercises_json = old_l.exercises_json
        elif decision == 'auto_merge':
            staged_l.content_md = f"{old_l.content_md}\n\n<<<<<<< LOCAL\n{old_l.content_md}\n=======\n{staged_l.content_md}\n>>>>>>> UPSTREAM"
        # take_upstream = no-op
        session.add(staged_l)
    session.commit()
    return {'ok': True, 'applied_conflicts': len(plan.get('conflicts', []))}
