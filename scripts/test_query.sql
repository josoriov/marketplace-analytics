select *
from raw.orders as t1
where t1.order_status = 'delivered'
limit 10
;
