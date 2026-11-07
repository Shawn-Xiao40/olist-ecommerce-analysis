-- 07_category_performance.sql
-- Business question: which categories drive revenue, and which sell well but get poor reviews?

CREATE OR REPLACE TABLE ana_category_performance AS
SELECT
    category,
    COUNT(DISTINCT order_id)                         AS orders,
    ROUND(SUM(price), 2)                             AS gmv,
    ROUND(SUM(price) / SUM(SUM(price)) OVER (), 4)   AS gmv_share,
    ROUND(AVG(price), 2)                             AS avg_price,
    ROUND(AVG(freight_value / NULLIF(price, 0)), 4)  AS freight_ratio,   -- freight as a share of item price
    ROUND(AVG(review_score), 3)                      AS avg_review
FROM fct_order_items
WHERE order_status NOT IN ('canceled', 'unavailable')
GROUP BY 1
ORDER BY gmv DESC;
