"""Create the Superset database connection, datasets, charts and dashboards through the REST API,
then export the dashboards.

Prerequisite: the container in superset/ is running and initialised (see README),
and superset/.env contains the admin account.
Usage:
    python scripts/build_superset_dashboards.py
Safe to re-run: existing dashboards with the same slugs (and their charts) are deleted and rebuilt.
"""
from __future__ import annotations

import json
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
BASE = "http://localhost:8088"
DB_NAME = "ecommerce (DuckDB)"
DB_URI = "duckdb:////data/ecommerce.duckdb?access_mode=read_only"
EXPORT_PATH = ROOT / "superset" / "dashboards" / "dashboards_export.zip"

# dashboard title -> slug
DASHBOARDS = {
    "Business Overview": "olist-overview",
    "Customer Analytics": "olist-customers",
    "Delivery & Customer Experience": "olist-delivery",
}


def read_env() -> dict:
    env = {}
    for line in (ROOT / "superset" / ".env").read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


class Superset:
    def __init__(self, user: str, password: str):
        self.s = requests.Session()
        r = self.s.post(f"{BASE}/api/v1/security/login",
                        json={"username": user, "password": password, "provider": "db", "refresh": True})
        r.raise_for_status()
        self.s.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
        csrf = self.s.get(f"{BASE}/api/v1/security/csrf_token/").json()["result"]
        self.s.headers.update({"X-CSRFToken": csrf, "Referer": BASE})

    def req(self, method: str, path: str, **kw):
        r = self.s.request(method, f"{BASE}/api/v1/{path}", **kw)
        if not r.ok:
            raise RuntimeError(f"{method} {path} -> {r.status_code}: {r.text[:500]}")
        return r

    def find(self, resource: str, col: str, value: str) -> list[int]:
        q = json.dumps({"filters": [{"col": col, "opr": "eq", "value": value}], "page_size": 100})
        return [x["id"] for x in self.req("GET", f"{resource}/", params={"q": q}).json()["result"]]


def metric(sql: str, label: str) -> dict:
    return {"expressionType": "SQL", "sqlExpression": sql, "label": label}


def where(sql: str) -> list[dict]:
    return [{"expressionType": "SQL", "clause": "WHERE", "sqlExpression": sql}]


# ---------------------------------------------------------------------------
# Chart specs: (dashboard, name, dataset, viz_type, params, width [1-12], height)
# ---------------------------------------------------------------------------
def chart_specs() -> list[tuple]:
    pct = {"y_axis_format": ".1%"}
    ov, cu, de = DASHBOARDS
    return [
        # ---------------- Business Overview ----------------
        (ov, "Total Orders", "fct_orders", "big_number_total",
         {"metric": metric("COUNT(*)", "Orders"), "y_axis_format": ",d"}, 3, 25),
        (ov, "Customers", "fct_orders", "big_number_total",
         {"metric": metric("COUNT(DISTINCT customer_unique_id)", "Customers"), "y_axis_format": ",d"}, 3, 25),
        (ov, "GMV (BRL)", "fct_orders", "big_number_total",
         {"metric": metric("SUM(items_value)", "GMV"), "y_axis_format": "SMART_NUMBER"}, 3, 25),
        (ov, "Average Review Score", "fct_orders", "big_number_total",
         {"metric": metric("AVG(review_score)", "Avg review"), "y_axis_format": ".2f"}, 3, 25),
        (ov, "Monthly GMV and Orders", "ana_monthly_sales", "mixed_timeseries",
         {"x_axis": "month", "time_grain_sqla": "P1M",
          "metrics": [metric("SUM(gmv)", "GMV")], "metrics_b": [metric("SUM(orders)", "Orders")],
          "groupby": [], "groupby_b": [], "adhoc_filters": [], "adhoc_filters_b": [],
          "seriesType": "line", "seriesTypeB": "bar", "yAxisIndexB": 1, "show_legend": True,
          "y_axis_format": "SMART_NUMBER", "y_axis_format_secondary": "SMART_NUMBER",
          "row_limit": 1000, "row_limit_b": 1000}, 8, 55),
        (ov, "Monthly Average Order Value", "ana_monthly_sales", "echarts_timeseries_line",
         {"x_axis": "month", "time_grain_sqla": "P1M", "metrics": [metric("SUM(aov)", "AOV")],
          "groupby": [], "markerEnabled": True, "y_axis_format": ".0f", "row_limit": 1000}, 4, 55),
        (ov, "Top 15 Categories by GMV", "ana_category_performance", "echarts_timeseries_bar",
         {"x_axis": "category", "metrics": [metric("SUM(gmv)", "GMV")], "groupby": [],
          "x_axis_sort": "GMV", "x_axis_sort_asc": False, "row_limit": 15,
          "orientation": "horizontal", "y_axis_format": "SMART_NUMBER"}, 6, 60),
        (ov, "Orders by Weekday and Hour", "ana_order_heatmap", "heatmap_v2",
         {"x_axis": "hour_label", "groupby": "weekday_label", "metric": metric("SUM(orders)", "Orders"),
          "linear_color_scheme": "blue_white_yellow", "show_legend": True, "row_limit": 1000,
          "sort_x_axis": "alpha_asc", "sort_y_axis": "alpha_asc", "value_bounds": [None, None]}, 6, 60),

        # ---------------- Customer Analytics ----------------
        (cu, "Repeat Purchase Rate (2+ orders)", "ana_repeat_purchase", "big_number_total",
         {"metric": metric("SUM(CASE WHEN orders_per_customer <> '1' THEN customers END) * 1.0 / SUM(customers)",
                           "Repeat rate"), **pct}, 4, 25),
        (cu, "Month-1 Retention", "ana_cohort_retention", "big_number_total",
         {"metric": metric("AVG(CASE WHEN month_number = 1 THEN retention_rate END)", "Retention"), **pct}, 4, 25),
        (cu, "Revenue Share of High-Value Customers", "ana_rfm_segments", "big_number_total",
         {"metric": metric("SUM(CASE WHEN segment LIKE '3%' OR segment LIKE '5%' THEN revenue_share END)",
                           "Revenue share"), **pct}, 4, 25),
        (cu, "RFM Segments: Customer Share vs Revenue Share", "ana_rfm_segments", "echarts_timeseries_bar",
         {"x_axis": "segment", "metrics": [metric("SUM(customer_share)", "Customer share"),
                                          metric("SUM(revenue_share)", "Revenue share")],
          "groupby": [], "x_axis_sort_asc": False, "row_limit": 100, "show_legend": True,
          "orientation": "horizontal", "y_axis_format": ".0%"}, 7, 60),
        (cu, "Orders per Customer", "ana_repeat_purchase", "pie",
         {"groupby": ["orders_per_customer"], "metric": metric("SUM(customers)", "Customers"),
          "show_labels": True, "label_type": "key_percent", "show_legend": True, "row_limit": 100}, 5, 60),
        (cu, "Cohort Retention (Months 1-12)", "ana_cohort_retention", "heatmap_v2",
         {"x_axis": "month_number", "groupby": "cohort_label", "metric": metric("MAX(retention_rate)", "Retention"),
          "adhoc_filters": where("month_number BETWEEN 1 AND 12"),
          "linear_color_scheme": "superset_seq_1", "y_axis_format": ".2%", "show_values": True,
          "row_limit": 1000, "sort_x_axis": "alpha_asc", "sort_y_axis": "alpha_asc",
          "value_bounds": [None, None]}, 12, 70),

        # ---------------- Delivery & Customer Experience ----------------
        (de, "Late Delivery Rate", "fct_orders", "big_number_total",
         {"metric": metric("AVG(CASE WHEN is_late THEN 1.0 ELSE 0 END)", "Late rate"),
          "adhoc_filters": where("order_status = 'delivered' AND is_late IS NOT NULL"), **pct}, 3, 25),
        (de, "Average Delivery Days", "fct_orders", "big_number_total",
         {"metric": metric("AVG(delivery_days)", "Days"), "y_axis_format": ".1f",
          "adhoc_filters": where("order_status = 'delivered'")}, 3, 25),
        (de, "Bad Review Rate: On-Time Orders", "ana_late_vs_review", "big_number_total",
         {"metric": metric("MAX(CASE WHEN delivery = 'On time' THEN bad_review_rate END)", "Bad review rate"),
          **pct}, 3, 25),
        (de, "Bad Review Rate: Late Orders", "ana_late_vs_review", "big_number_total",
         {"metric": metric("MAX(CASE WHEN delivery = 'Late' THEN bad_review_rate END)", "Bad review rate"),
          **pct}, 3, 25),
        (de, "Delivery Time vs Bad Review Rate", "ana_delivery_days_vs_review", "echarts_timeseries_bar",
         {"x_axis": "delivery_bucket", "metrics": [metric("SUM(bad_review_rate)", "Bad review rate (1-2 stars)")],
          "groupby": [], "x_axis_sort_asc": True, "row_limit": 100, "y_axis_format": ".0%",
          "show_value": True}, 6, 60),
        (de, "Delivery Time vs Average Review", "ana_delivery_days_vs_review", "echarts_timeseries_bar",
         {"x_axis": "delivery_bucket", "metrics": [metric("SUM(avg_review)", "Average review")], "groupby": [],
          "x_axis_sort_asc": True, "row_limit": 100, "y_axis_format": ".2f", "show_value": True}, 6, 60),
        (de, "Late Delivery Rate by State", "ana_state_delivery", "echarts_timeseries_bar",
         {"x_axis": "customer_state", "metrics": [metric("SUM(late_rate)", "Late rate")], "groupby": [],
          "x_axis_sort": "Late rate", "x_axis_sort_asc": False, "row_limit": 100, "y_axis_format": ".0%"}, 7, 60),
        (de, "Delivery Performance by State", "ana_state_delivery", "table",
         {"query_mode": "raw", "all_columns": ["customer_state", "orders", "avg_delivery_days",
                                               "late_rate", "avg_review"],
          "order_by_cols": [json.dumps(["orders", False])], "row_limit": 100,
          "include_search": True, "column_config": {"late_rate": {"d3NumberFormat": ".1%"}}}, 5, 60),
    ]


def build_position(title: str, charts: list[tuple[int, str, int, int]]) -> dict:
    """charts: (chart_id, name, width, height), packed in order into rows 12 units wide."""
    pos = {
        "DASHBOARD_VERSION_KEY": "v2",
        "ROOT_ID": {"type": "ROOT", "id": "ROOT_ID", "children": ["GRID_ID"]},
        "GRID_ID": {"type": "GRID", "id": "GRID_ID", "children": [], "parents": ["ROOT_ID"]},
        "HEADER_ID": {"id": "HEADER_ID", "type": "HEADER", "meta": {"text": title}},
    }
    row, used, n_row = None, 12, 0
    for cid, name, w, h in charts:
        if used + w > 12:
            n_row += 1
            row = f"ROW-{n_row}"
            pos[row] = {"type": "ROW", "id": row, "children": [], "parents": ["ROOT_ID", "GRID_ID"],
                        "meta": {"background": "BACKGROUND_TRANSPARENT"}}
            pos["GRID_ID"]["children"].append(row)
            used = 0
        key = f"CHART-{cid}"
        pos[key] = {"type": "CHART", "id": key, "children": [], "parents": ["ROOT_ID", "GRID_ID", row],
                    "meta": {"width": w, "height": h, "chartId": cid, "sliceName": name}}
        pos[row]["children"].append(key)
        used += w
    return pos


def main() -> None:
    env = read_env()
    api = Superset(env["SUPERSET_ADMIN_USER"], env["SUPERSET_ADMIN_PASSWORD"])

    # 1. Database connection
    ids = api.find("database", "database_name", DB_NAME)
    if ids:
        db_id = ids[0]
    else:
        db_id = api.req("POST", "database/", json={
            "database_name": DB_NAME, "sqlalchemy_uri": DB_URI, "expose_in_sqllab": True,
        }).json()["id"]
    print(f"Database connection id={db_id}")

    # 2. Datasets
    specs = chart_specs()
    datasets = {}
    for table in sorted({s[2] for s in specs}):
        existing = api.find("dataset", "table_name", table)
        if existing:
            datasets[table] = existing[0]
            api.req("PUT", f"dataset/{existing[0]}/refresh")  # table schema may have changed
        else:
            datasets[table] = api.req("POST", "dataset/", json={
                "database": db_id, "schema": "main", "table_name": table}).json()["id"]
    print(f"{len(datasets)} datasets")

    # 3. Delete existing dashboards with our slugs (and their charts), then rebuild
    for slug in DASHBOARDS.values():
        for did in api.find("dashboard", "slug", slug):
            for c in api.req("GET", f"dashboard/{did}/charts").json()["result"]:
                api.req("DELETE", f"chart/{c['id']}")
            api.req("DELETE", f"dashboard/{did}")

    dash_ids = {}
    for title, slug in DASHBOARDS.items():
        dash_ids[title] = api.req("POST", "dashboard/", json={
            "dashboard_title": title, "slug": slug, "published": True}).json()["id"]

    layout: dict[str, list] = {t: [] for t in DASHBOARDS}
    for dash, name, table, viz, params, w, h in specs:
        p = {"viz_type": viz, "datasource": f"{datasets[table]}__table", "adhoc_filters": [], **params}
        cid = api.req("POST", "chart/", json={
            "slice_name": name, "viz_type": viz, "datasource_id": datasets[table],
            "datasource_type": "table", "params": json.dumps(p),
            "dashboards": [dash_ids[dash]],
        }).json()["id"]
        layout[dash].append((cid, name, w, h))
    print(f"{len(specs)} charts")

    for title, did in dash_ids.items():
        api.req("PUT", f"dashboard/{did}", json={
            "position_json": json.dumps(build_position(title, layout[title])),
            "json_metadata": json.dumps({"color_scheme": "supersetColors", "refresh_frequency": 0}),
        })
        print(f"Dashboard '{title}' -> {BASE}/superset/dashboard/{DASHBOARDS[title]}/")

    # 4. Export the dashboards (charts, datasets and the connection config, no passwords)
    q = "!(" + ",".join(str(i) for i in dash_ids.values()) + ")"
    r = api.req("GET", "dashboard/export/", params={"q": q})
    EXPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    EXPORT_PATH.write_bytes(r.content)
    print(f"Exported -> {EXPORT_PATH}")


if __name__ == "__main__":
    main()
