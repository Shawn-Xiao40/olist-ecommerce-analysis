-- 03_order_funnel.sql
-- Business question: where do orders drop off between purchase and delivery?
-- Note: Olist has no browsing / add-to-cart events, so this is a *fulfillment* funnel
--       (placed -> approved -> shipped -> delivered), not a conversion funnel.
--       With clickstream data the next step would be a view -> cart -> purchase funnel.

CREATE OR REPLACE TABLE ana_order_funnel AS
WITH stages AS (
    SELECT 1 AS step, '1 Placed'    AS stage, COUNT(*)            AS orders FROM fct_orders
    UNION ALL
    SELECT 2, '2 Approved',   COUNT(approved_at)  FROM fct_orders
    UNION ALL
    SELECT 3, '3 Shipped',    COUNT(shipped_at)   FROM fct_orders
    UNION ALL
    SELECT 4, '4 Delivered',  COUNT(delivered_at) FROM fct_orders
)
SELECT
    step,
    stage,
    orders,
    ROUND(orders / FIRST_VALUE(orders) OVER (ORDER BY step), 4)  AS pct_of_placed,
    ROUND(orders / LAG(orders) OVER (ORDER BY step), 4)          AS pct_of_prev_step
FROM stages
ORDER BY step;

-- Order status distribution
CREATE OR REPLACE TABLE ana_order_status AS
SELECT order_status, COUNT(*) AS orders,
       ROUND(COUNT(*) / SUM(COUNT(*)) OVER (), 4) AS share
FROM fct_orders
GROUP BY 1
ORDER BY orders DESC;
