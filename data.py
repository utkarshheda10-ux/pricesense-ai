"""Sample SKU catalogue for the PriceSense AI demo.

In production this table would be a live feed from the retailer's
inventory + OMS + competitor-scraping pipeline. Here it's a small,
reproducible synthetic catalogue so the dashboard behaves consistently
across demo runs.
"""

import numpy as np
import pandas as pd

_CATALOGUE = [
    # name, category, base_price, unit
    ("Amul Toned Milk 1L", "Dairy", 66, "pouch"),
    ("Amul Butter 100g", "Dairy", 58, "pack"),
    ("Britannia Bread 400g", "Staples", 45, "pack"),
    ("Tata Salt 1kg", "Staples", 28, "pack"),
    ("Fortune Sunflower Oil 1L", "Staples", 160, "bottle"),
    ("Maggi Noodles (pack of 4)", "Snacks", 56, "pack"),
    ("Lay's Chips 52g", "Snacks", 20, "pack"),
    ("Cadbury Dairy Milk 55g", "Snacks", 45, "bar"),
    ("Coca-Cola 750ml", "Beverages", 40, "bottle"),
    ("Red Bull 250ml", "Beverages", 125, "can"),
    ("Real Fruit Juice 1L", "Beverages", 110, "carton"),
    ("Surf Excel Detergent 1kg", "Household", 130, "pack"),
    ("Dove Soap 100g", "Personal Care", 65, "bar"),
    ("Colgate Toothpaste 100g", "Personal Care", 55, "tube"),
    ("McCain French Fries 425g", "Frozen", 199, "pack"),
]


def get_skus(seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for name, category, base_price, unit in _CATALOGUE:
        avg_daily_sales = float(rng.integers(20, 90))
        # Inventory sometimes scarce, sometimes overstocked, sometimes healthy
        cover_choice = rng.choice(["scarce", "healthy", "over"], p=[0.27, 0.46, 0.27])
        if cover_choice == "scarce":
            cover_days = rng.uniform(0.5, 1.8)
        elif cover_choice == "over":
            cover_days = rng.uniform(5.5, 9.5)
        else:
            cover_days = rng.uniform(2.5, 4.5)
        inventory_units = round(avg_daily_sales * cover_days)

        competitor_price = round(base_price * (1 + rng.uniform(-0.10, 0.10)), 2)

        rows.append(
            {
                "SKU": name,
                "Category": category,
                "Unit": unit,
                "Current Price (₹)": base_price,
                "Inventory (units)": int(inventory_units),
                "Avg Daily Sales (units)": round(avg_daily_sales, 1),
                "Competitor Price (₹)": competitor_price,
            }
        )
    return pd.DataFrame(rows)
