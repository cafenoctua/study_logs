select
	h.PARTKEY as PART_KEY,
	s.PART_NAME AS NAME,
	s.PART_MFGR as MFGR
from
	{{ ref('hub_part') }} as h
inner join
	{{ ref('sat_inv_part_details') }} as s
on
	h.PART_PK = s.PART_PK
where
	s.LOAD_DATE = (select max(load_date) from {{ ref('sat_inv_part_details') }})