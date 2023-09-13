from datetime import datetime

from .models import Attempt


async def time_is_between(
    start_time: datetime, 
    time_to_check: datetime,
    end_time: datetime
) -> bool:
    return start_time.time() <= time_to_check.time() <= end_time.time()


async def attempt_is_completed(
    attempt: Attempt, 
    time_to_check: datetime
) -> bool:
    if not await time_is_between(
        start_time=attempt.start_time,
        time_to_check=time_to_check,
        end_time=attempt.end_time
    ):
        return True
    elif int(attempt.spent_time.split(":")[0]) != attempt.quiz.completion_time:
        return True
    else:
        return False
