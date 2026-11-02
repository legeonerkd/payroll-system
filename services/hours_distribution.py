"""Whole-hour allocation with modest variation across Monday through Saturday."""
from datetime import timedelta
import random

from core.validation import number


def distribute_hours(start, end, total):
    if start > end or (end-start).days > 365:
        raise ValueError('Select a period of 1 to 366 days with From before To')
    total = number(str(total).replace(',', '.'), 'Total hours')
    if total != total.to_integral_value():
        raise ValueError('Enter a whole number of total hours for automatic distribution')
    dates = [start+timedelta(days=i) for i in range((end-start).days+1)]
    working = [day for day in dates if day.weekday() < 6]
    if not working:
        raise ValueError('The selected period has no Monday-Saturday working days')
    if total > len(working)*24:
        raise ValueError('Total hours exceed 24 hours per Monday-Saturday working day')
    base, remainder = divmod(int(total), len(working))
    allocations = [base + (i < remainder) for i in range(len(working))]
    random.shuffle(allocations)
    # Move one or two hours between pairs, preserving the total and keeping
    # each day close to the average. Equal days remain possible and natural.
    lower, upper = max(0, base-2), min(24, base+2)
    for i in range(0, len(allocations)-1, 2):
        donor, receiver = (i,i+1) if allocations[i] <= allocations[i+1] else (i+1,i)
        capacity = min(2, allocations[donor]-lower, upper-allocations[receiver])
        if capacity > 0:
            moved = random.randint(1, capacity)
            allocations[donor] -= moved
            allocations[receiver] += moved
    random.shuffle(allocations)
    result = {day.isoformat(): 0 for day in dates}
    for index, day in enumerate(working):
        result[day.isoformat()] = allocations[index]
    return result
