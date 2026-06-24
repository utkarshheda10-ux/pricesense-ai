"""
PriceSense AI — pricing engine
--------------------------------
A transparent, explainable rule-based + price-elasticity engine that simulates
how a production dynamic-pricing model (gradient boosting / contextual bandit,
trained on real POS + competitor-scrape + weather data) would behave.

Kept rule-based and fully inspectable on purpose: for a prototype with no
historical transaction data, an explainable elasticity model is both more
honest and more demo-friendly than pretending a few hundred rows trained a
"real" ML model. A production rollout would retrain this on real data.
"""

from dataclasses import dataclass

DAY_DEMAND = {
    "Weekday": 0.00,
    "Weekend": 0.04,
    "Festival / Big Billion Day": 0.10,
}

WEATHER_DEMAND = {
    "Normal": 0.00,
    "Rain": 0.05,       # quick-commerce orders spike when it rains
    "Heatwave": 0.06,   # spikes for beverages/dairy/frozen
}


def _clamp(value, low, high):
    return max(low, min(high, value))


@dataclass
class PriceRecommendation:
    base_price: float
    recommended_price: float
    price_change_pct: float
    expected_demand_change_pct: float
    expected_revenue_change_pct: float
    stock_cover_days: float
    confidence: float
    explanation: str
    signals: dict


def recommend_price(
    base_price: float,
    inventory_units: float,
    avg_daily_sales: float,
    competitor_price: float,
    day_type: str = "Weekday",
    weather: str = "Normal",
    elasticity: float = -1.3,
) -> PriceRecommendation:
    """Return an explainable price recommendation for one SKU."""

    avg_daily_sales = max(avg_daily_sales, 0.1)
    stock_cover_days = inventory_units / avg_daily_sales

    # --- Signal 1: inventory pressure -------------------------------------
    if stock_cover_days < 1.5:
        stock_signal = 0.08
        stock_note = "very low stock cover (<1.5 days) → scarcity premium"
    elif stock_cover_days < 3:
        stock_signal = 0.03
        stock_note = "tight stock cover (<3 days) → slight premium"
    elif stock_cover_days > 7:
        stock_signal = -0.07
        stock_note = "heavy overstock (>7 days cover) → markdown to clear"
    elif stock_cover_days > 5:
        stock_signal = -0.04
        stock_note = "building overstock (>5 days cover) → mild markdown"
    else:
        stock_signal = 0.0
        stock_note = "healthy stock cover → no inventory pressure"

    # --- Signal 2: competitive gap -----------------------------------------
    gap = (competitor_price - base_price) / base_price
    competitor_signal = _clamp(gap * 0.35, -0.06, 0.06)
    if competitor_signal > 0.01:
        comp_note = f"competitor priced {gap*100:.0f}% higher → headroom to raise"
    elif competitor_signal < -0.01:
        comp_note = f"competitor priced {abs(gap)*100:.0f}% lower → pressure to cut"
    else:
        comp_note = "competitor price roughly in line → neutral"

    # --- Signal 3: demand context (day type + weather) ---------------------
    demand_signal = DAY_DEMAND.get(day_type, 0.0) + WEATHER_DEMAND.get(weather, 0.0)
    if demand_signal >= 0.08:
        demand_note = f"{day_type} + {weather} → strong demand tailwind"
    elif demand_signal > 0:
        demand_note = f"{day_type} + {weather} → mild demand tailwind"
    else:
        demand_note = "no seasonal demand tailwind"

    # --- Combine ------------------------------------------------------------
    total_adj = _clamp(stock_signal + competitor_signal + demand_signal, -0.15, 0.15)
    recommended_price = base_price * (1 + total_adj)

    demand_change_pct = elasticity * total_adj  # elasticity is negative
    revenue_change_pct = (1 + total_adj) * (1 + demand_change_pct) - 1

    # --- Confidence: do the signals agree in direction? ----------------------
    signs = [s for s in [stock_signal, competitor_signal, demand_signal] if abs(s) > 1e-6]
    if not signs:
        confidence = 0.55
    else:
        agree = sum(1 for s in signs if (s > 0) == (total_adj >= 0))
        confidence = 0.55 + 0.13 * agree
    confidence = _clamp(confidence, 0.5, 0.95)

    explanation = (
        f"{stock_note}; {comp_note}; {demand_note}. "
        f"Net recommendation: {total_adj*100:+.1f}% price change."
    )

    return PriceRecommendation(
        base_price=base_price,
        recommended_price=round(recommended_price, 2),
        price_change_pct=round(total_adj * 100, 2),
        expected_demand_change_pct=round(demand_change_pct * 100, 2),
        expected_revenue_change_pct=round(revenue_change_pct * 100, 2),
        stock_cover_days=round(stock_cover_days, 1),
        confidence=round(confidence, 2),
        explanation=explanation,
        signals={
            "stock_signal": round(stock_signal * 100, 1),
            "competitor_signal": round(competitor_signal * 100, 1),
            "demand_signal": round(demand_signal * 100, 1),
        },
    )


def demand_curve(base_price, avg_daily_sales, elasticity=-1.3, span=0.25, n=41):
    """Return (prices, demand_units, revenue) across a price range for charting."""
    import numpy as np

    pct = np.linspace(-span, span, n)
    prices = base_price * (1 + pct)
    demand = avg_daily_sales * (1 + elasticity * pct)
    demand = np.clip(demand, avg_daily_sales * 0.1, None)
    revenue = prices * demand
    return prices, demand, revenue
