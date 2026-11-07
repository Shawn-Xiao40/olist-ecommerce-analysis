-- 05_rfm.sql
-- Business question: how unequal is customer value? Which customers should we retain or win back?
-- R = days since last purchase, F = number of orders, M = total spend.
-- Almost every Olist customer has exactly one order, so F cannot be split into quintiles;
-- it is scored with a simple rule instead.

CREATE OR REPLACE TABLE ana_rfm_customers AS
WITH ref AS (
    SELECT MAX(purchased_at) + INTERVAL 1 DAY AS ref_date FROM fct_orders
),
base AS (
    SELECT
        customer_unique_id,
        date_diff('day', MAX(purchased_at), (SELECT ref_date FROM ref)) AS recency_days,
        COUNT(*)                     AS frequency,
        ROUND(SUM(items_value), 2)   AS monetary
    FROM fct_orders
    WHERE order_status NOT IN ('canceled', 'unavailable')
    GROUP BY 1
),
scored AS (
    SELECT *,
        6 - NTILE(5) OVER (ORDER BY recency_days)       AS r_score,  -- more recent = higher score
        CASE WHEN frequency = 1 THEN 1
             WHEN frequency = 2 THEN 3
             ELSE 5 END                                AS f_score,
        NTILE(5) OVER (ORDER BY monetary)               AS m_score
    FROM base
)
SELECT *,
    CASE
        WHEN f_score >= 3 AND r_score >= 4 AND m_score >= 4 THEN '1 Champions'
        WHEN f_score >= 3                                   THEN '2 Loyal'
        WHEN r_score >= 4 AND m_score >= 4                  THEN '3 Big Spenders'
        WHEN r_score >= 4                                   THEN '4 Promising'
        WHEN r_score <= 2 AND m_score >= 4                  THEN '5 At Risk'
        WHEN r_score <= 2                                   THEN '7 Hibernating'
        ELSE                                                     '6 Need Attention'
    END AS segment
FROM scored;

CREATE OR REPLACE TABLE ana_rfm_segments AS
SELECT
    segment,
    COUNT(*)                                           AS customers,
    ROUND(COUNT(*) / SUM(COUNT(*)) OVER (), 4)         AS customer_share,
    ROUND(SUM(monetary), 2)                            AS revenue,
    ROUND(SUM(monetary) / SUM(SUM(monetary)) OVER (), 4) AS revenue_share,
    ROUND(AVG(recency_days), 1)                        AS avg_recency_days,
    ROUND(AVG(monetary), 2)                            AS avg_monetary
FROM ana_rfm_customers
GROUP BY 1
ORDER BY 1;
