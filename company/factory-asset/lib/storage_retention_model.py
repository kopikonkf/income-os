from __future__ import annotations
GIB=1024**3;TIB=1024**4

def scenario(per_master_bytes:int,masters_per_day:int=1000,days:int=30)->dict:
    if min(per_master_bytes,masters_per_day,days)<=0:raise ValueError('positive values required')
    day=per_master_bytes*masters_per_day;period=day*days
    return {'per_master_bytes':per_master_bytes,'masters_per_day':masters_per_day,'retention_days':days,'daily_bytes':day,'daily_gib':round(day/GIB,3),'period_bytes':period,'period_tib':round(period/TIB,3)}

def hot_retention_days(free_bytes:int,daily_bytes:int,reserve_fraction:float=.25)->float:
    if free_bytes<=0 or daily_bytes<=0 or not 0<=reserve_fraction<1:raise ValueError('invalid values')
    return round((free_bytes*(1-reserve_fraction))/daily_bytes,3)
