-- 06_delivery_vs_review.sql
-- Deep dive: does the delivery experience affect review scores, and by how much?
-- This is the headline question of the project: the answer translates directly into actions
-- (e.g. more realistic delivery promises, fixing logistics in specific states).
-- The statistical test (Mann-Whitney U) is in the notebook.

-- On time vs late
CREATE OR REPLACE TABLE ana_late_vs_review AS
SELECT
    CASE WHEN is_late THEN 'Late' ELSE 'On time' END AS delivery,
    COUNT(*)                                             AS orders,
    ROUND(AVG(review_score), 3)                          AS avg_review,
    ROUND(AVG(CASE WHEN review_score <= 2 THEN 1.0 ELSE 0 END), 4) AS bad_review_rate
FROM fct_orders
WHERE order_status = 'delivered' AND is_late IS NOT NULL AND review_score IS NOT NULL
GROUP BY 1
ORDER BY 1;

-- By delivery time bucket
CREATE OR REPLACE TABLE ana_delivery_days_vs_review AS
SELECT
    CASE
        WHEN delivery_days <= 7  THEN '1) 0-7 days'
        WHEN delivery_days <= 14 THEN '2) 8-14 days'
        WHEN delivery_days <= 21 THEN '3) 15-21 days'
        WHEN delivery_days <= 30 THEN '4) 22-30 days'
        ELSE                          '5) 30+ days'
    END AS delivery_bucket,
    COUNT(*)                                             AS orders,
    ROUND(AVG(review_score), 3)                          AS avg_review,
    ROUND(AVG(CASE WHEN review_score <= 2 THEN 1.0 ELSE 0 END), 4) AS bad_review_rate
FROM fct_orders
WHERE order_status = 'delivered' AND delivery_days IS NOT NULL AND review_score IS NOT NULL
GROUP BY 1
ORDER BY 1;

-- Delivery performance by state
CREATE OR REPLACE TABLE ana_state_delivery AS
SELECT
    customer_state,
    COUNT(*)                                     AS orders,
    ROUND(AVG(delivery_days), 1)                 AS avg_delivery_days,
    ROUND(AVG(CASE WHEN is_late THEN 1.0 ELSE 0 END), 4) AS late_rate,
    ROUND(AVG(review_score), 3)                  AS avg_review
FROM fct_orders
WHERE order_status = 'delivered' AND delivery_days IS NOT NULL
GROUP BY 1
ORDER BY orders DESC;
