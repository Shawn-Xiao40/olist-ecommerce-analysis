-- 01_staging.sql
-- Clean and aggregate the raw tables into analysis-ready fact tables.
-- Grain: fct_orders = one row per order; fct_order_items = one row per order item.

-- Order fact table -----------------------------------------------------------
CREATE OR REPLACE TABLE fct_orders AS
WITH items AS (
    SELECT
        order_id,
        COUNT(*)            AS n_items,
        SUM(price)          AS items_value,
        SUM(freight_value)  AS freight_value
    FROM raw_order_items
    GROUP BY order_id
),
pay AS (
    SELECT
        order_id,
        SUM(payment_value)                    AS payment_value,
        arg_max(payment_type, payment_value)  AS main_payment_type,
        MAX(payment_installments)             AS installments
    FROM raw_order_payments
    GROUP BY order_id
),
rev AS (
    -- A few orders have more than one review; take the average
    SELECT order_id, AVG(review_score) AS review_score
    FROM raw_order_reviews
    GROUP BY order_id
)
SELECT
    o.order_id,
    c.customer_unique_id,                      -- the real customer ID (customer_id changes on every order)
    c.customer_state,
    c.customer_city,
    o.order_status,
    CAST(o.order_purchase_timestamp      AS TIMESTAMP) AS purchased_at,
    CAST(o.order_approved_at             AS TIMESTAMP) AS approved_at,
    CAST(o.order_delivered_carrier_date  AS TIMESTAMP) AS shipped_at,
    CAST(o.order_delivered_customer_date AS TIMESTAMP) AS delivered_at,
    CAST(o.order_estimated_delivery_date AS TIMESTAMP) AS estimated_delivery_at,
    COALESCE(i.n_items, 0)        AS n_items,
    COALESCE(i.items_value, 0)    AS items_value,
    COALESCE(i.freight_value, 0)  AS freight_value,
    p.payment_value,
    p.main_payment_type,
    p.installments,
    r.review_score,
    date_diff('day', CAST(o.order_purchase_timestamp AS TIMESTAMP),
                     CAST(o.order_delivered_customer_date AS TIMESTAMP)) AS delivery_days,
    CASE
        WHEN o.order_delivered_customer_date IS NULL THEN NULL
        WHEN CAST(o.order_delivered_customer_date AS TIMESTAMP)
           > CAST(o.order_estimated_delivery_date AS TIMESTAMP) THEN TRUE
        ELSE FALSE
    END AS is_late
FROM raw_orders o
JOIN raw_customers c USING (customer_id)
LEFT JOIN items i USING (order_id)
LEFT JOIN pay   p USING (order_id)
LEFT JOIN rev   r USING (order_id);

-- Order item fact table ------------------------------------------------------
CREATE OR REPLACE TABLE fct_order_items AS
SELECT
    oi.order_id,
    oi.order_item_id,
    oi.product_id,
    oi.seller_id,
    COALESCE(t.product_category_name_english, p.product_category_name, 'unknown') AS category,
    oi.price,
    oi.freight_value,
    o.purchased_at,
    o.order_status,
    o.review_score,
    o.customer_state,
    s.seller_state
FROM raw_order_items oi
JOIN fct_orders o USING (order_id)
LEFT JOIN raw_products p USING (product_id)
LEFT JOIN raw_category_translation t ON p.product_category_name = t.product_category_name
LEFT JOIN raw_sellers s USING (seller_id);
