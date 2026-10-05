select *
from marketplace.raw.orders AS t1
where t1.order_status = 'delivered'
limit 10
;