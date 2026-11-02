"""Whole-hour allocation with modest variation across Monday through Saturday."""
from datetime import timedelta
import random

from core.validation import number
from core.validation import iso_date
from decimal import Decimal
from core.cyprus_holidays import holiday_name

MAX_DISTRIBUTED_HOURS = 14


def distribute_hours(start, end, total, *, minimum=0, maximum=MAX_DISTRIBUTED_HOURS, locked=None, excluded=None):
    if start > end or (end-start).days > 365:
        raise ValueError('Select a period of 1 to 366 days with From before To')
    total = number(str(total).replace(',', '.'), 'Total hours')
    minimum=number(minimum,'Minimum daily hours',maximum=24)
    maximum=number(maximum,'Maximum daily hours',maximum=24)
    if minimum!=minimum.to_integral_value() or maximum!=maximum.to_integral_value() or minimum>maximum:
        raise ValueError('Daily range must use whole numbers with 0 <= Min <= Max <= 24')
    minimum,maximum=int(minimum),int(maximum)
    # Older saved preferences can reach 24; apply the current distribution cap.
    minimum=min(minimum,MAX_DISTRIBUTED_HOURS)
    maximum=min(maximum,MAX_DISTRIBUTED_HOURS)
    dates = [start+timedelta(days=i) for i in range((end-start).days+1)]
    keys={day.isoformat() for day in dates}
    locked={iso_date(day):number(hours,'Locked hours',maximum=24) for day,hours in (locked or {}).items()}
    excluded={iso_date(day) for day in (excluded or ())}
    if not set(locked).issubset(keys) or not excluded.issubset(keys):
        raise ValueError('Locked and excluded dates must belong to the selected period')
    if set(locked)&excluded:
        raise ValueError('A date cannot be both locked and excluded')
    if any(hours>MAX_DISTRIBUTED_HOURS for hours in locked.values()):
        raise ValueError('A locked date exceeds 14 hours. Edit its hours before distributing; locked hours will not be changed automatically.')
    remaining=total-sum(locked.values(),Decimal(0))
    if remaining<0:
        raise ValueError('Total hours are less than the locked hours')
    if remaining!=remaining.to_integral_value():
        raise ValueError('The total minus locked hours must be a whole number. Adjust the total or locked hours.')
    working = [day for day in dates if day.weekday()<6 and not holiday_name(day) and day.isoformat() not in locked and day.isoformat() not in excluded]
    result = {day.isoformat(): 0 for day in dates}
    result.update({day:float(hours) for day,hours in locked.items()})
    if not working:
        if remaining==0: return result
        raise ValueError('No available Monday-Saturday days remain after Cyprus holidays, locks and exclusions')
    if remaining>len(working)*MAX_DISTRIBUTED_HOURS:
        fixed=sum(locked.values(),Decimal(0))
        raise ValueError(f'This period can hold at most {fixed+len(working)*MAX_DISTRIBUTED_HOURS:g} hours '
                         'with 14 hours per available non-holiday day. Extend the period or adjust locked dates.')
    # The requested total takes priority over the preferred daily range. Relax
    # only the side that cannot accommodate it; locks and exclusions remain hard.
    if remaining<len(working)*minimum:
        minimum=0
    if remaining>len(working)*maximum:
        maximum=MAX_DISTRIBUTED_HOURS
    base, remainder = divmod(int(remaining), len(working))
    allocations = [base + (i < remainder) for i in range(len(working))]
    random.shuffle(allocations)
    # Move one or two hours between pairs, preserving the total and keeping
    # each day close to the average. Equal days remain possible and natural.
    lower, upper = max(minimum, base-2), min(maximum, base+2)
    for i in range(0, len(allocations)-1, 2):
        donor, receiver = (i,i+1) if allocations[i] <= allocations[i+1] else (i+1,i)
        capacity = min(2, allocations[donor]-lower, upper-allocations[receiver])
        if capacity > 0:
            moved = random.randint(1, capacity)
            allocations[donor] -= moved
            allocations[receiver] += moved
    random.shuffle(allocations)
    for index, day in enumerate(working):
        result[day.isoformat()] = allocations[index]
    return result
