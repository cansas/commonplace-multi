"""SM-2 spaced repetition algorithm."""

from datetime import datetime, timedelta


def sm2_calc(quality: int, prev_ease: float, prev_interval: int, prev_reps: int):
    """
    Calculate next review schedule using SM-2 algorithm.
    
    quality: 0=forgot, 1=hard, 2=good, 3=easy
    Returns: (new_ease, new_interval, new_reps)
    """
    quality_map = {0: 0, 1: 1, 2: 3, 3: 5}
    q = quality_map.get(quality, 2)
    
    if q < 3:
        # Reset
        return (prev_ease, 1, 0)
    
    # Calculate new ease factor
    new_ease = prev_ease + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
    if new_ease < 1.3:
        new_ease = 1.3
    
    # Calculate new interval
    if prev_reps == 0:
        new_interval = 1
    elif prev_reps == 1:
        new_interval = 6
    else:
        new_interval = round(prev_interval * new_ease)
    
    return (round(new_ease, 2), new_interval, prev_reps + 1)


def get_next_review_date(interval_days: int) -> datetime:
    return datetime.utcnow() + timedelta(days=interval_days)
