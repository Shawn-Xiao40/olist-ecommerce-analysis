"""Take full-page screenshots of the Superset dashboards and save them to reports/figures/dashboard_*.png.

Extra dependency (not in requirements.txt, only needed for screenshots):
    pip install playwright && python -m playwright install chromium
Usage:
    python scripts/screenshot_dashboards.py
"""
from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
BASE = "http://localhost:8088"
OUT = ROOT / "reports" / "figures"
DASHBOARDS = {
    "olist-overview": "dashboard_overview.png",
    "olist-customers": "dashboard_customers.png",
    "olist-delivery": "dashboard_delivery.png",
}


def read_env() -> dict:
    env = {}
    for line in (ROOT / "superset" / ".env").read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def main() -> None:
    env = read_env()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1600, "height": 1000}, device_scale_factor=2,
                                locale="en-US")
        page.goto(f"{BASE}/login/")
        page.fill("input[name=username]", env["SUPERSET_ADMIN_USER"])
        page.fill("input[name=password]", env["SUPERSET_ADMIN_PASSWORD"])
        page.click("input[type=submit]")
        page.wait_for_url("**/superset/welcome/**")

        for slug, filename in DASHBOARDS.items():
            page.goto(f"{BASE}/superset/dashboard/{slug}/?standalone=1")
            page.wait_for_selector(".dashboard-component-chart-holder", timeout=60_000)
            # Wait until every chart has loaded (no spinner, no "Waiting on" placeholder)
            page.wait_for_function(
                "() => !document.querySelector('.loading') && !document.body.innerText.includes('Waiting on')",
                timeout=120_000,
            )
            page.wait_for_timeout(2500)  # let the ECharts animations finish
            page.screenshot(path=str(OUT / filename), full_page=True)
            print(f"Saved {OUT / filename}")
        browser.close()


if __name__ == "__main__":
    main()
