from datetime import date
import pytest
from core.cyprus_holidays import cyprus_holidays,holiday_name,orthodox_easter
from services.hours_distribution import distribute_hours


@pytest.mark.parametrize('year,green,good,easter,monday,pentecost',[
    (2025,'03-03','04-18','04-20','04-21','06-09'),
    (2026,'02-23','04-10','04-12','04-13','06-01'),
    (2027,'03-15','04-30','05-02','05-03','06-21'),
    (2028,'02-28','04-14','04-16','04-17','06-05'),
    # Visit Cyprus has a June typo for Pentecost 2029; Easter + 50 = May 28.
    (2029,'02-19','04-06','04-08','04-09','05-28')])
def test_published_visit_cyprus_movable_dates(year,green,good,easter,monday,pentecost):
    days=cyprus_holidays(year)
    for suffix,name in [(green,'Green Monday'),(good,'Orthodox Good Friday'),(easter,'Orthodox Easter Sunday'),
                         (monday,'Orthodox Easter Monday'),(pentecost,'Pentecost Monday / Kataklysmos')]:
        assert days[date.fromisoformat(f'{year}-{suffix}')]==name
    assert orthodox_easter(year)==date.fromisoformat(f'{year}-{easter}')
    assert len(days)==16


def test_fixed_dates_weekend_holidays_and_calendar_scope():
    days=cyprus_holidays(2026)
    for suffix in ('01-01','01-06','03-25','04-01','05-01','08-15','10-01','10-28','12-24','12-25','12-26'):
        assert date.fromisoformat('2026-'+suffix) in days
    assert not holiday_name('2026-04-14')  # Easter Tuesday is bank-only.
    assert not holiday_name('2026-04-11')  # No general Holy Saturday rule.
    assert not holiday_name('2026-12-28')  # No invented substitute Monday.
    assert holiday_name('2026-08-15') and date(2026,8,15).weekday()==5


def test_colliding_holidays_share_one_date_and_cache_cannot_be_mutated():
    days=cyprus_holidays(2000)
    assert 'Labour Day' in days[date(2000,5,1)] and 'Easter Monday' in days[date(2000,5,1)]
    days.clear()
    assert cyprus_holidays(2000)


def test_new_year_boundary_skips_holidays_in_both_years():
    result=distribute_hours(date(2026,12,24),date(2027,1,6),60)
    assert sum(result.values())==60
    for day in ('2026-12-24','2026-12-25','2026-12-26','2027-01-01','2027-01-06'):
        assert result[day]==0
    assert result['2026-12-28']>=0
    assert all(0<=v<=14 for v in result.values())


def test_locked_manual_holiday_hours_are_counted_and_kept():
    result=distribute_hours(date(2026,4,10),date(2026,4,14),24,
        locked={'2026-04-10':8,'2026-04-12':4})
    assert result['2026-04-10']==8 and result['2026-04-12']==4
    assert result['2026-04-13']==0 and sum(result.values())==24
    assert result['2026-04-14']>=0  # Bank-only Easter Tuesday remains eligible.


def test_all_holidays_or_sundays_allow_zero_but_not_positive_total():
    assert set(distribute_hours(date(2026,12,24),date(2026,12,27),0).values())=={0}
    with pytest.raises(ValueError,match='Cyprus holidays'):
        distribute_hours(date(2026,12,24),date(2026,12,27),1)


def test_holiday_saturday_is_skipped_but_ordinary_saturday_is_working():
    assert distribute_hours(date(2026,8,15),date(2026,8,17),10)['2026-08-15']==0
    assert distribute_hours(date(2026,8,22),date(2026,8,22),10)['2026-08-22']==10
