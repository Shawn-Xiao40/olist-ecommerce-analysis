-- 04_cohort_retention.sql
-- Business question: do customers come back after their first purchase? When do they churn?
-- Note: customers must be identified by customer_unique_id; customer_id is different on every order.

CREATE OR REPLACE TABLE ana_cohort_retention AS
WITH o AS (
    SELECT customer_unique_id, date_trunc('month', purchased_at)::DATE AS order_month
    FROM fct_orders
    WHERE order_status NOT IN ('canceled', 'unavailable')
),
first_order AS (
    SELECT customer_unique_id, MIN(order_month) AS cohort_month
    FROM o GROUP BY 1
),
activity AS (
    SELECT DISTINCT
        f.cohort_month,
        o.customer_unique_id,
        date_diff('month', f.cohort_month, o.order_month) AS month_number
    FROM o JOIN first_order f USING (customer_unique_id)
)
SELECT
    cohort_month,
    strftime(cohort_month, '%Y-%m') AS cohort_label,   -- text label for the Superset heatmap
    month_number,
    COUNT(*) AS active_customers,
    ROUND(COUNT(*) / FIRST_VALUE(COUNT(*)) OVER (
        PARTITION BY cohort_month ORDER BY month_number), 4) AS retention_rate
FROM activity
WHERE cohort_month >= '2017-01-01' AND cohort_month < '2018-09-01'
GROUP BY 1, 2, 3
ORDER BY 1, 3;

-- Overall repeat purchase: distribution of orders per customer
CREATE OR REPLACE TABLE ana_repeat_purchase AS
WITH per_user AS (
    SELECT customer_unique_id, COUNT(*) AS n_orders
    FROM fct_orders
    WHERE order_status NOT IN ('canceled', 'unavailable')
    GROUP BY 1
)
SELECT
    CASE WHEN n_orders >= 4 THEN '4+' ELSE n_orders::VARCHAR END AS orders_per_customer,
    COUNT(*) AS customers,
    ROUND(COUNT(*) / SUM(COUNT(*)) OVER (), 4) AS share
FROM per_user
GROUP BY 1
ORDER BY 1;
