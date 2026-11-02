"""Offline planning calendar based on the Cyprus Deputy Ministry of Tourism.

Source checked 2026-11-02. Movable dates cross-checked against the published
2025-2029 Easter table. Its Pentecost 2029 June typo is corrected by Easter+50.
Bank-only Easter Tuesday is not part of this calendar.
"""
from datetime import date,timedelta
from functools import lru_cache

SOURCE_URL='https://www.visitcyprus.com/useful-info/time-working-hours-holidays/'
CHECKED_ON='2026-11-02'
FIXED=((1,1,"New Year's Day"),(1,6,'Epiphany'),(3,25,'Greek National Day'),
       (4,1,'National Anniversary Day'),(5,1,'Labour Day'),(8,15,'Assumption Day'),
       (10,1,'Cyprus Independence Day'),(10,28,'Greek National Anniversary Day'),
       (12,24,'Christmas Eve'),(12,25,'Christmas Day'),(12,26,'Boxing Day'))


def orthodox_easter(year):
    # Julian computus followed by the Gregorian offset for March/April.
    date(year,1,1)
    a,b,c=year%4,year%7,year%19
    d=(19*c+15)%30
    e=(2*a+4*b-d+34)%7
    month=(d+e+114)//31;day=(d+e+114)%31+1
    return date(year,month,day)+timedelta(days=year//100-year//400-2)


@lru_cache(maxsize=128)
def _items(year):
    easter=orthodox_easter(year);days={}
    for month,day,name in FIXED:days.setdefault(date(year,month,day),[]).append(name)
    for offset,name in ((-48,'Green Monday'),(-2,'Orthodox Good Friday'),(0,'Orthodox Easter Sunday'),
                        (1,'Orthodox Easter Monday'),(50,'Pentecost Monday / Kataklysmos')):
        days.setdefault(easter+timedelta(days=offset),[]).append(name)
    return tuple((day,' / '.join(names)) for day,names in sorted(days.items()))


def cyprus_holidays(year):
    return dict(_items(year))


def holiday_name(day):
    if isinstance(day,str):day=date.fromisoformat(day)
    return cyprus_holidays(day.year).get(day,'')
