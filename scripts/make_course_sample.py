import json
from pathlib import Path

sample = {
    "topic": "Guitar",
    "goal": "Night shift beginner progression",
    "level": "beginner",
    "schedule_days_per_week": 5,
    "daily_minutes": 30,
    "constraints": "night shift",
    "learner_type": "adult",
    "preferred_style": "guided",
    "day_starts_at": "18:00",
}
out = Path('dist/sample_course_spec.json')
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(sample, indent=2), encoding='utf-8')
print(out)
