from datetime import date, timedelta
from decimal import Decimal

import pytest

from services.hours_distribution import distribute_hours


@pytest.mark.parametrize('length,total',[(1,'0'),(6,'48'),(31,'173'),(60,'1'),(366,'5000'),(7,'10,00')])
def test_exact_total_and_monday_saturday_only(length,total):
    start = date(2026,5,1)
    values = distribute_hours(start,start+timedelta(days=length-1),total)
    assert len(values) == length
    assert sum(Decimal(str(v)) for v in values.values()) == Decimal(total.replace(',','.'))
    working = []
    for day,hours in values.items():
        assert 0 <= hours <= 24
        assert isinstance(hours,int)
        if date.fromisoformat(day).weekday() == 6:
            assert hours == 0
        else:
            working.append(Decimal(str(hours)))
    assert max(working)-min(working) <= 4


def test_saturday_included_and_equal_average_varies():
    values = distribute_hours(date(2026,5,1),date(2026,5,4),'30')
    assert values['2026-05-02'] > 0
    assert values['2026-05-03'] == 0
    assert sum(values.values()) == 30
    assert len({v for d,v in values.items() if date.fromisoformat(d).weekday()<6}) > 1


@pytest.mark.parametrize('total',range(145))
def test_every_total_in_a_six_day_week(total):
    values = list(distribute_hours(date(2026,5,4),date(2026,5,9),total).values())
    assert sum(values) == total
    assert all(isinstance(v,int) and 0<=v<=24 for v in values)
    if 0<total<144:
        assert len(set(values))>1


@pytest.mark.parametrize('total',['-1','nan','inf','','abc','0.001','10.5','49'])
def test_invalid_total_rejected(total):
    with pytest.raises(ValueError):
        distribute_hours(date(2026,5,1),date(2026,5,2),total)


@pytest.mark.parametrize('start,end',[(date(2026,5,3),date(2026,5,3)),
    (date(2026,5,2),date(2026,5,1)),(date(2026,1,1),date(2027,1,2))])
def test_invalid_period_rejected(start,end):
    with pytest.raises(ValueError):
        distribute_hours(start,end,'8')
