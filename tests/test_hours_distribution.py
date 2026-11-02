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


@pytest.mark.parametrize('total',range(37,58))
def test_bounded_distribution_preserves_locked_and_excluded(total):
    if total>53:
        with pytest.raises(ValueError,match='from 37 to 53'):
            distribute_hours(date(2026,5,4),date(2026,5,10),total,minimum=8,maximum=12,
                locked={'2026-05-04':5},excluded={'2026-05-05'})
        return
    result=distribute_hours(date(2026,5,4),date(2026,5,10),total,minimum=8,maximum=12,
        locked={'2026-05-04':5},excluded={'2026-05-05'})
    assert sum(result.values())==total
    assert result['2026-05-04']==5 and result['2026-05-05']==0 and result['2026-05-10']==0
    assert all(isinstance(result[d],int) and 8<=result[d]<=12 for d in ('2026-05-06','2026-05-07','2026-05-08','2026-05-09'))


def test_fractional_locked_sunday_and_matching_fractional_total():
    result=distribute_hours(date(2026,5,4),date(2026,5,10),'60.5',minimum=8,maximum=12,
        locked={'2026-05-10':.5})
    assert result['2026-05-10']==.5 and sum(result.values())==60.5
    with pytest.raises(ValueError,match='minus locked'):
        distribute_hours(date(2026,5,4),date(2026,5,10),60,locked={'2026-05-10':.5})


def test_all_dates_fixed_and_infeasible_cases():
    start,end=date(2026,5,1),date(2026,5,3)
    assert distribute_hours(start,end,8.5,locked={'2026-05-01':8.5},excluded={'2026-05-02'})=={
        '2026-05-01':8.5,'2026-05-02':0,'2026-05-03':0}
    for total in (7,9.5):
        with pytest.raises(ValueError):
            distribute_hours(start,end,total,locked={'2026-05-01':8.5},excluded={'2026-05-02'})


@pytest.mark.parametrize('options',[
    {'minimum':12,'maximum':8},{'minimum':8.5},{'maximum':25},
    {'locked':{'2026-05-01':25}}, {'locked':{'2026-04-30':8}},
    {'excluded':{'2026-06-01'}}, {'locked':{'2026-05-01':8},'excluded':{'2026-05-01'}},
    {'minimum':12,'maximum':12},
])
def test_invalid_constraints_rejected(options):
    with pytest.raises(ValueError):
        distribute_hours(date(2026,5,1),date(2026,5,2),16,**options)
