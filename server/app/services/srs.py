from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class SM2State:
    repetitions: int = 0
    interval_days: int = 0
    ease: float = 2.5


def sm2_review(state: SM2State, rating: int, now: datetime | None = None):
    now = now or datetime.utcnow()
    rating = max(0, min(5, rating))

    if rating < 3:
        state.repetitions = 0
        state.interval_days = 1
    else:
        if state.repetitions == 0:
            state.interval_days = 1
        elif state.repetitions == 1:
            state.interval_days = 6
        else:
            state.interval_days = int(round(state.interval_days * state.ease))
        state.repetitions += 1

    state.ease = max(1.3, state.ease + (0.1 - (5 - rating) * (0.08 + (5 - rating) * 0.02)))
    due_at = now + timedelta(days=state.interval_days)
    return state, due_at
