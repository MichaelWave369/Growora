from app.models import Course
from app.services.adaptive_planner import build_today_plan


class DummyTask:
    def __init__(self, lesson_id, done_at, label='x', estimated_minutes=10):
        self.lesson_id = lesson_id; self.done_at = done_at; self.label = label; self.estimated_minutes = estimated_minutes


class DummyLesson:
    def __init__(self, id, course_id, order_index=0):
        self.id = id; self.course_id = course_id; self.order_index = order_index


class DummyAttempt:
    def __init__(self, score, total, lesson_id):
        self.score = score; self.total = total; self.lesson_id = lesson_id


class DummyExec:
    def __init__(self, data): self._data = data
    def all(self): return self._data


class DummySession:
    def __init__(self, lessons, tasks, attempts): self.lessons, self.tasks, self.attempts, self.calls = lessons, tasks, attempts, 0
    def exec(self, _):
        self.calls += 1
        return DummyExec(self.lessons if self.calls == 1 else self.tasks if self.calls == 2 else self.attempts)


def test_planner_rules():
    c = Course(id=1, profile_id=1, title='t', topic='x', learner_profile_json='{}', day_start_time='18:00', minutes_per_day=20)
    plan = build_today_plan(c, DummySession([DummyLesson(1,1)], [DummyTask(1,None,'a',10), DummyTask(1,None,'b',10)], [DummyAttempt(1,5,1)]))
    assert plan['rolled_over_count'] >= 1
    assert plan['used_minutes'] <= 20
