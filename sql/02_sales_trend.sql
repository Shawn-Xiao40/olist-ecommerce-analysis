-- 02_sales_trend.sql
-- Business question: how is the platform growing? Is growth driven by more customers or by bigger baskets?
-- Restricted to 2017-01 .. 2018-08: the first and last months of the Olist data are very sparse
-- and would distort the trend.

CREATE OR REPLACE TABLE ana_monthly_sales AS
SELECT
    date_trunc('month', purchased_at)::DATE      AS month,
    COUNT(*)                                     AS orders,
    COUNT(DISTINCT customer_unique_id)           AS customers,
    ROUND(SUM(items_value), 2)                   AS gmv,            -- merchandise value (excl. freight)
    ROUND(SUM(items_value) / COUNT(*), 2)        AS aov,            -- average order value
    ROUND(AVG(n_items), 3)                       AS items_per_order
FROM fct_orders
WHERE order_status NOT IN ('canceled', 'unavailable')
  AND purchased_at >= '2017-01-01' AND purchased_at < '2018-09-01'
GROUP BY 1
ORDER BY 1;

-- Orders by weekday x hour (for scheduling campaigns and support staffing)
CREATE OR REPLACE TABLE ana_order_heatmap AS
SELECT
    dayofweek(purchased_at) AS weekday,      -- 0 = Sunday
    hour(purchased_at)      AS hour,
    -- Text labels for the Superset heatmap (it renders the numeric value 0 as NULL)
    ['7 Sun', '1 Mon', '2 Tue', '3 Wed', '4 Thu', '5 Fri', '6 Sat'][dayofweek(purchased_at) + 1] AS weekday_label,
    lpad(hour(purchased_at)::VARCHAR, 2, '0') AS hour_label,
    COUNT(*)                AS orders
FROM fct_orders
GROUP BY 1, 2, 3, 4
ORDER BY 1, 2;
