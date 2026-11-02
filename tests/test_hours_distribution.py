from datetime import date, timedelta
from decimal import Decimal

import pytest

from services.hours_distribution import distribute_hours


@pytest.mark.parametrize('length,total',[(1,'0'),(6,'48'),(31,'173'),(60,'1'),(366,'4000'),(7,'10,00')])
def test_exact_total_and_monday_saturday_only(length,total):
    start = date(2026,5,1)
    values = distribute_hours(start,start+timedelta(days=length-1),total)
    assert len(values) == length
    assert sum(Decimal(str(v)) for v in values.values()) == Decimal(total.replace(',','.'))
    working = []
    for day,hours in values.items():
        assert 0 <= hours <= 14
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


@pytest.mark.parametrize('total',range(85))
def test_every_total_in_a_six_day_week(total):
    values = list(distribute_hours(date(2026,5,4),date(2026,5,9),total).values())
    assert sum(values) == total
    assert all(isinstance(v,int) and 0<=v<=14 for v in values)
    if 0<total<84:
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


@pytest.mark.parametrize('total',range(5,62))
def test_bounded_distribution_preserves_locked_and_excluded(total):
    result=distribute_hours(date(2026,5,4),date(2026,5,10),total,minimum=8,maximum=12,
        locked={'2026-05-04':5},excluded={'2026-05-05'})
    assert sum(result.values())==total
    assert result['2026-05-04']==5 and result['2026-05-05']==0 and result['2026-05-10']==0
    flexible=[result[d] for d in ('2026-05-06','2026-05-07','2026-05-08','2026-05-09')]
    assert all(isinstance(v,int) and 0<=v<=14 for v in flexible)
    if 37<=total<=53:assert all(8<=v<=12 for v in flexible)


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
])
def test_invalid_constraints_rejected(options):
    with pytest.raises(ValueError):
        distribute_hours(date(2026,5,1),date(2026,5,2),16,**options)


@pytest.mark.parametrize('total',[0,1,27,157,158,159,215,216,324,325,377,378])
def test_october_total_takes_priority_over_preferred_eight_to_twelve(total):
    result=distribute_hours(date(2026,10,1),date(2026,10,31),total,minimum=8,maximum=12)
    working=[hours for day,hours in result.items() if date.fromisoformat(day).weekday()<6]
    assert len(working)==27 and sum(result.values())==total
    assert all(isinstance(v,int) and 0<=v<=14 for v in working)
    assert all(v==0 for day,v in result.items() if date.fromisoformat(day).weekday()==6)
    if total==158:assert len(set(working))>1
    if 216<=total<=324:assert all(8<=v<=12 for v in working)


@pytest.mark.parametrize('minimum,maximum',[(0,0),(8,8),(12,12),(24,24)])
@pytest.mark.parametrize('total',[0,1,16,27,28])
def test_fixed_preference_does_not_block_feasible_total(minimum,maximum,total):
    result=distribute_hours(date(2026,5,1),date(2026,5,2),total,minimum=minimum,maximum=maximum)
    assert sum(result.values())==total
    assert all(isinstance(v,int) and 0<=v<=14 for v in result.values())


def test_physical_capacity_remains_explicit():
    with pytest.raises(ValueError,match='at most 378'):
        distribute_hours(date(2026,10,1),date(2026,10,31),379,minimum=8,maximum=12)


def test_old_twenty_four_hour_preferences_respect_fourteen_hour_cap():
    result=distribute_hours(date(2026,5,4),date(2026,5,9),84,minimum=20,maximum=24)
    assert set(result.values())=={14}
    with pytest.raises(ValueError,match='at most 84'):
        distribute_hours(date(2026,5,4),date(2026,5,9),85,maximum=24)


def test_lock_above_fourteen_requires_explicit_manual_correction():
    locked={'2026-05-04':15}
    with pytest.raises(ValueError,match='locked date exceeds 14'):
        distribute_hours(date(2026,5,4),date(2026,5,9),60,locked=locked)
    assert locked=={'2026-05-04':15}
