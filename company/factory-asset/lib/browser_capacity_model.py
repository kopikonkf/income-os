from __future__ import annotations
import math
GIB=1024**3;MIB=1024**2

def owner_ceiling(*,total_ram_bytes:int,combined_two_owner_peak_mib:float,reserve_gib:float=8.0,recovery_owner_reserve:int=1)->dict:
    if total_ram_bytes<=0 or combined_two_owner_peak_mib<=0 or reserve_gib<=0 or recovery_owner_reserve<1:raise ValueError('invalid capacity input')
    per=(combined_two_owner_peak_mib*MIB)/2;usable=total_ram_bytes-reserve_gib*GIB
    raw=max(0,math.floor(usable/per));safe=max(0,raw-recovery_owner_reserve)
    projected=safe*per+reserve_gib*GIB
    return {'total_ram_bytes':total_ram_bytes,'combined_two_owner_peak_mib':combined_two_owner_peak_mib,'conservative_per_owner_peak_mib':combined_two_owner_peak_mib/2,'system_recovery_reserve_gib':reserve_gib,'raw_ram_owner_limit':raw,'recovery_owner_reserve':recovery_owner_reserve,'active_browser_owner_ceiling':safe,'projected_bytes_at_ceiling_plus_reserve':int(projected),'remaining_headroom_gib':round((total_ram_bytes-projected)/GIB,3),'policy':'PROFILES_ABOVE_ACTIVE_OWNER_CEILING_MUST_REMAIN_COLD_OR_PARKED_UNTIL_LEASED'}
