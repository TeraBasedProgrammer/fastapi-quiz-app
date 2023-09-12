from datetime import datetime

from .models import Attemp


async def time_is_between(
    start_time: datetime, 
    time_to_check: datetime,
    end_time: datetime
) -> bool:
    return start_time.time() <= time_to_check.time() <= end_time.time()


async def attemp_is_completed(
    attemp: Attemp, 
    time_to_check: datetime
) -> bool:
    if not await time_is_between(
        start_time=attemp.start_time,
        time_to_check=time_to_check,
        end_time=attemp.end_time
    ) or attemp.spent_time is not None:
        return True
    else:
        return False
