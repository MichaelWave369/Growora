import difflib
import json
from collections import defaultdict

from sqlmodel import Session, select

from app.models import Lesson


def diff_courses(session: Session, old_course_id: int, new_course_id: int):
    old_lessons = session.exec(select(Lesson).where(Lesson.course_id == old_course_id).order_by(Lesson.order_index, Lesson.id)).all()
    new_lessons = session.exec(select(Lesson).where(Lesson.course_id == new_course_id).order_by(Lesson.order_index, Lesson.id)).all()

    old_by_title = {l.title: l for l in old_lessons}
    new_by_title = {l.title: l for l in new_lessons}
    added = [t for t in new_by_title if t not in old_by_title]
    removed = [t for t in old_by_title if t not in new_by_title]
    changed = []
    lesson_diffs = []

    for title in sorted(set(old_by_title) & set(new_by_title)):
        o = old_by_title[title]; n = new_by_title[title]
        if o.content_md != n.content_md or o.quiz_json != n.quiz_json or o.exercises_json != n.exercises_json:
            changed.append(title)
            ud = list(difflib.unified_diff(o.content_md.splitlines(), n.content_md.splitlines(), fromfile='old', tofile='new', lineterm=''))
            oq = json.loads(o.quiz_json or '{}').get('questions', [])
            nq = json.loads(n.quiz_json or '{}').get('questions', [])
            lesson_diffs.append({
                'title': title,
                'content_diff': ud[:200],
                'content_changed_lines': len([x for x in ud if x.startswith('+') or x.startswith('-')]),
                'quiz_added': max(0, len(nq)-len(oq)),
                'quiz_removed': max(0, len(oq)-len(nq)),
            })

    return {
        'summary': {
            'lessons_added': len(added),
            'lessons_removed': len(removed),
            'lessons_changed': len(changed),
            'breaking_changes': len(removed),
        },
        'added_lessons': added,
        'removed_lessons': removed,
        'changed_lessons': changed,
        'lesson_diffs': lesson_diffs,
    }
