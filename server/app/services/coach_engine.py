def coach_message(missed_days: int, quiz_score: float, time_ratio: float, streak: int, frustration: bool) -> str:
    if frustration:
        return "Take a breath. We'll simplify the next step and build momentum."
    if missed_days > 1:
        return "You missed a few days—no stress. We'll start with a quick review block today."
    if quiz_score < 0.6:
        return "Let's reinforce fundamentals with bite-size repetitions before moving on."
    if quiz_score > 0.85 and time_ratio >= 1.0:
        return "Great momentum! Unlocking a challenge task to stretch your skills."
    if streak >= 5:
        return "Fantastic streak. Keep consistency and protect your study window."
    return "Nice progress. Finish today's core task and reflect in one sentence."
