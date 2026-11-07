"""Generate SYNTHETIC sample data with the same schema as the Olist dataset,
used to test the whole pipeline before downloading the real data.

Note: the data is random. Any conclusions drawn from it are meaningless.

Usage:
    python scripts/make_sample_data.py            # writes to data/sample/
"""
from __future__ import annotations

import uuid
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "sample"
RNG = np.random.default_rng(42)

N_CUSTOMERS = 4000
N_PRODUCTS = 600
N_SELLERS = 150
STATES = ["SP", "RJ", "MG", "RS", "PR", "SC", "BA", "DF", "GO", "ES"]
STATE_P = [0.42, 0.13, 0.12, 0.06, 0.05, 0.04, 0.04, 0.05, 0.05, 0.04]
CATEGORIES = {
    "cama_mesa_banho": "bed_bath_table",
    "beleza_saude": "health_beauty",
    "esporte_lazer": "sports_leisure",
    "informatica_acessorios": "computers_accessories",
    "moveis_decoracao": "furniture_decor",
    "utilidades_domesticas": "housewares",
    "relogios_presentes": "watches_gifts",
    "telefonia": "telephony",
    "brinquedos": "toys",
    "automotivo": "auto",
}


def uid() -> str:
    return uuid.UUID(int=int(RNG.integers(0, 2**63)) << 64 | int(RNG.integers(0, 2**63))).hex


def fmt(ts) -> str:
    return "" if pd.isna(ts) else pd.Timestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    # customer_unique_id is the real customer; each order gets its own customer_id
    unique_ids = [uid() for _ in range(N_CUSTOMERS)]
    user_state = dict(zip(unique_ids, RNG.choice(STATES, N_CUSTOMERS, p=STATE_P)))

    cat_pt = list(CATEGORIES)
    products = pd.DataFrame({
        "product_id": [uid() for _ in range(N_PRODUCTS)],
        "product_category_name": RNG.choice(cat_pt, N_PRODUCTS),
        "product_name_lenght": RNG.integers(20, 70, N_PRODUCTS),
        "product_description_lenght": RNG.integers(100, 2000, N_PRODUCTS),
        "product_photos_qty": RNG.integers(1, 6, N_PRODUCTS),
        "product_weight_g": RNG.integers(100, 10000, N_PRODUCTS),
        "product_length_cm": RNG.integers(10, 60, N_PRODUCTS),
        "product_height_cm": RNG.integers(2, 40, N_PRODUCTS),
        "product_width_cm": RNG.integers(10, 50, N_PRODUCTS),
    })
    base_price = dict(zip(products.product_id, RNG.lognormal(4.3, 0.8, N_PRODUCTS).round(2)))

    sellers = pd.DataFrame({
        "seller_id": [uid() for _ in range(N_SELLERS)],
        "seller_zip_code_prefix": RNG.integers(1000, 99999, N_SELLERS),
        "seller_city": "sao paulo",
        "seller_state": RNG.choice(STATES, N_SELLERS, p=STATE_P),
    })

    # Orders per customer: most buy only once (as in the real Olist data)
    n_orders = RNG.choice([1, 2, 3, 4], N_CUSTOMERS, p=[0.93, 0.05, 0.015, 0.005])
    start, end = pd.Timestamp("2017-01-01"), pd.Timestamp("2018-08-31")
    span = (end - start).total_seconds()

    customers, orders, items, payments, reviews = [], [], [], [], []
    for u, k in zip(unique_ids, n_orders):
        # Order volume grows over time: sqrt makes later dates denser
        times = start + pd.to_timedelta(np.sqrt(RNG.random(k)) * span, unit="s")
        for t in sorted(times):
            cid, oid = uid(), uid()
            customers.append((cid, u, RNG.integers(1000, 99999), "cidade", user_state[u]))

            status = RNG.choice(["delivered", "shipped", "canceled", "unavailable", "invoiced"],
                                p=[0.95, 0.02, 0.015, 0.01, 0.005])
            approved = t + pd.Timedelta(hours=float(RNG.exponential(10)))
            shipped = approved + pd.Timedelta(days=float(RNG.exponential(3)))
            delivery_days = float(RNG.gamma(3, 4))
            delivered = t + pd.Timedelta(days=delivery_days)
            estimated = t + pd.Timedelta(days=float(RNG.integers(15, 35)))
            if status in ("canceled", "unavailable"):
                approved = approved if RNG.random() < 0.5 else pd.NaT
                shipped = delivered = pd.NaT
            elif status in ("shipped",):
                delivered = pd.NaT
            elif status == "invoiced":
                shipped = delivered = pd.NaT
            orders.append((oid, cid, status, fmt(t), fmt(approved), fmt(shipped),
                           fmt(delivered), fmt(estimated)))

            n_items = RNG.choice([1, 2, 3], p=[0.88, 0.09, 0.03])
            total = 0.0
            for i in range(1, n_items + 1):
                pid = products.product_id.iloc[RNG.integers(N_PRODUCTS)]
                price = round(base_price[pid] * RNG.uniform(0.9, 1.1), 2)
                freight = round(RNG.uniform(8, 40), 2)
                total += price + freight
                items.append((oid, i, pid, sellers.seller_id.iloc[RNG.integers(N_SELLERS)],
                              fmt(t + pd.Timedelta(days=5)), price, freight))

            ptype = RNG.choice(["credit_card", "boleto", "voucher", "debit_card"], p=[0.74, 0.19, 0.05, 0.02])
            payments.append((oid, 1, ptype, int(RNG.integers(1, 11)) if ptype == "credit_card" else 1,
                             round(total, 2)))

            # Late orders get clearly lower scores (so the sample data has a signal to find)
            late = pd.notna(delivered) and delivered > estimated
            if status != "delivered":
                p = [0.55, 0.1, 0.1, 0.1, 0.15]
            elif late:
                p = [0.40, 0.12, 0.15, 0.15, 0.18]
            else:
                p = [0.06, 0.03, 0.08, 0.20, 0.63]
            score = RNG.choice([1, 2, 3, 4, 5], p=p)
            reviews.append((uid(), oid, score, "", "", fmt(t + pd.Timedelta(days=delivery_days + 1)),
                            fmt(t + pd.Timedelta(days=delivery_days + 2))))

    def save(rows, cols, name):
        pd.DataFrame(rows, columns=cols).to_csv(OUT / name, index=False)

    save(customers, ["customer_id", "customer_unique_id", "customer_zip_code_prefix",
                     "customer_city", "customer_state"], "olist_customers_dataset.csv")
    save(orders, ["order_id", "customer_id", "order_status", "order_purchase_timestamp",
                  "order_approved_at", "order_delivered_carrier_date",
                  "order_delivered_customer_date", "order_estimated_delivery_date"],
         "olist_orders_dataset.csv")
    save(items, ["order_id", "order_item_id", "product_id", "seller_id", "shipping_limit_date",
                 "price", "freight_value"], "olist_order_items_dataset.csv")
    save(payments, ["order_id", "payment_sequential", "payment_type", "payment_installments",
                    "payment_value"], "olist_order_payments_dataset.csv")
    save(reviews, ["review_id", "order_id", "review_score", "review_comment_title",
                   "review_comment_message", "review_creation_date", "review_answer_timestamp"],
         "olist_order_reviews_dataset.csv")
    products.to_csv(OUT / "olist_products_dataset.csv", index=False)
    sellers.to_csv(OUT / "olist_sellers_dataset.csv", index=False)
    pd.DataFrame(list(CATEGORIES.items()),
                 columns=["product_category_name", "product_category_name_english"]
                 ).to_csv(OUT / "product_category_name_translation.csv", index=False)

    print(f"Synthetic sample data written to {OUT}  ({len(orders):,} orders)")


if __name__ == "__main__":
    main()
