"""
PriceSense AI — AI-Powered Dynamic Pricing & Demand-Sensing Copilot
for Quick-Commerce / FMCG Retail.

Abakus AI Catalyst submission · IIM Kozhikode

Run locally:    streamlit run app.py
Deploy free:    Streamlit Community Cloud (see README.md) or Replit.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from data import get_skus
from engine import recommend_price, demand_curve

# ----------------------------------------------------------------------------
# Page config & light styling
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="PriceSense AI",
    page_icon="💹",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .ps-card {
        background-color: #F2F7F9;
        border-radius: 12px;
        padding: 1.1rem 1.3rem;
        margin-bottom: 0.6rem;
    }
    .ps-card-dark {
        background-color: #21295C;
        color: #F2F7F9;
        border-radius: 12px;
        padding: 1.1rem 1.3rem;
        margin-bottom: 0.6rem;
    }
    .ps-pill {
        display: inline-block;
        padding: 0.15rem 0.7rem;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 600;
        margin-right: 0.3rem;
    }
    .ps-pill-red {background-color:#FDE2E1; color:#A8201A;}
    .ps-pill-amber {background-color:#FDF1D6; color:#9A6700;}
    .ps-pill-green {background-color:#DFF3EC; color:#0E6B4F;}
    .ps-small {color:#5B6B7C; font-size:0.85rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------------
# Session state
# ----------------------------------------------------------------------------
if "decisions" not in st.session_state:
    st.session_state.decisions = {}  # sku -> {"status": "Approved"/"Kept", "impact": float}

# ----------------------------------------------------------------------------
# Sidebar — global "today's context" controls
# ----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 💹 PriceSense AI")
    st.caption("AI Catalyst · Abakus, IIM Kozhikode")
    st.markdown("---")
    st.markdown("**Today's context**")
    st.caption("These signals feed every SKU's price recommendation below.")
    day_type = st.selectbox("Day type", ["Weekday", "Weekend", "Festival / Big Billion Day"])
    weather = st.selectbox("Weather", ["Normal", "Rain", "Heatwave"])
    elasticity = st.slider(
        "Assumed price elasticity of demand", -2.5, -0.5, -1.3, step=0.1,
        help="How much a 1% price change moves demand. More negative = more price-sensitive category.",
    )
    st.markdown("---")
    with st.expander("ℹ️ About this prototype"):
        st.write(
            "Quick-commerce and FMCG retailers re-price thousands of SKUs "
            "manually, once a day — leading to stockouts on fast movers and "
            "markdown losses on slow movers. **PriceSense AI** scores live "
            "inventory, competitor price, weather and calendar signals to "
            "recommend an explainable price every few hours, with a human "
            "category manager always in the loop."
        )
        st.caption(
            "The engine here is a transparent rule-based + price-elasticity "
            "model — built this way so every recommendation is fully "
            "explainable with no historical training data required. A "
            "production version would retrain on real POS + competitor data."
        )

# ----------------------------------------------------------------------------
# Header
# ----------------------------------------------------------------------------
st.title("💹 PriceSense AI")
st.caption("AI-powered dynamic pricing & demand-sensing copilot for quick-commerce & FMCG retail")

tab1, tab2, tab3 = st.tabs(["🎯 SKU Pricing Copilot", "📊 Category Dashboard", "🧮 Impact Simulator"])

sku_df = get_skus()

# ============================================================================
# TAB 1 — SKU Pricing Copilot
# ============================================================================
with tab1:
    left, right = st.columns([1, 1.4], gap="large")

    with left:
        st.subheader("SKU inputs")
        sku_name = st.selectbox("Choose a SKU", sku_df["SKU"].tolist())
        row = sku_df[sku_df["SKU"] == sku_name].iloc[0]

        base_price = float(row["Current Price (₹)"])
        st.metric("Current price", f"₹{base_price:,.2f}")

        inventory_units = st.slider(
            "Inventory on hand (units)", 0, 500, int(row["Inventory (units)"])
        )
        avg_daily_sales = st.slider(
            "Average daily sales (units)", 1, 200, int(row["Avg Daily Sales (units)"])
        )
        competitor_price = st.number_input(
            "Competitor price (₹)", min_value=1.0, value=float(row["Competitor Price (₹)"]), step=0.5
        )

        rec = recommend_price(
            base_price=base_price,
            inventory_units=inventory_units,
            avg_daily_sales=avg_daily_sales,
            competitor_price=competitor_price,
            day_type=day_type,
            weather=weather,
            elasticity=elasticity,
        )

    with right:
        st.subheader("AI recommendation")

        m1, m2, m3 = st.columns(3)
        m1.metric("Recommended price", f"₹{rec.recommended_price:,.2f}", f"{rec.price_change_pct:+.1f}%")
        m2.metric("Expected demand change", f"{rec.expected_demand_change_pct:+.1f}%")
        m3.metric("Expected revenue change", f"{rec.expected_revenue_change_pct:+.1f}%")

        st.progress(rec.confidence, text=f"Model confidence: {rec.confidence*100:.0f}%")

        st.markdown(
            f"<div class='ps-card'><b>Why this price?</b><br>{rec.explanation}</div>",
            unsafe_allow_html=True,
        )

        if rec.signals["stock_signal"] > 4 and rec.expected_revenue_change_pct < 0:
            st.info(
                "⚠️ This price increase is driven mainly by **scarcity, not revenue "
                "maximisation** — it rations limited stock across the day so the SKU "
                "doesn't sell out before restock, rather than chasing short-term revenue.",
                icon="⚠️",
            )
        elif rec.signals["stock_signal"] < -4:
            st.info(
                "📉 This markdown is driven mainly by **overstock risk** — clearing "
                "inventory now protects margin versus a deeper clearance discount later.",
                icon="📉",
            )

        st.markdown("##### Demand curve at different price points")
        prices, demand, revenue = demand_curve(base_price, avg_daily_sales, elasticity=elasticity)

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=prices, y=demand, name="Predicted demand (units/day)",
                                  line=dict(color="#1C7293", width=3)))
        fig.add_trace(go.Scatter(x=prices, y=revenue, name="Predicted revenue (₹/day)",
                                  yaxis="y2", line=dict(color="#21295C", width=3, dash="dot")))
        fig.add_vline(x=base_price, line_dash="dash", line_color="#5B6B7C",
                      annotation_text="Current", annotation_position="top")
        fig.add_vline(x=rec.recommended_price, line_dash="dash", line_color="#0E6B4F",
                      annotation_text="AI recommended", annotation_position="top")
        fig.update_layout(
            height=380, margin=dict(l=10, r=10, t=30, b=10),
            xaxis_title="Price (₹)",
            yaxis=dict(title="Demand (units/day)"),
            yaxis2=dict(title="Revenue (₹/day)", overlaying="y", side="right"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            plot_bgcolor="white",
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"Stock cover at current sales rate: **{rec.stock_cover_days} days**")

# ============================================================================
# TAB 2 — Category Dashboard
# ============================================================================
with tab2:
    st.subheader("Category manager dashboard")
    st.caption("Every SKU, re-priced under today's context. Review and decide — AI recommends, you approve.")

    categories = sorted(sku_df["Category"].unique())
    chosen_cats = st.multiselect("Filter by category", categories, default=categories)

    filtered = sku_df[sku_df["Category"].isin(chosen_cats)].copy()

    records = []
    for _, r in filtered.iterrows():
        rec = recommend_price(
            base_price=float(r["Current Price (₹)"]),
            inventory_units=float(r["Inventory (units)"]),
            avg_daily_sales=float(r["Avg Daily Sales (units)"]),
            competitor_price=float(r["Competitor Price (₹)"]),
            day_type=day_type,
            weather=weather,
            elasticity=elasticity,
        )
        if rec.stock_cover_days < 2:
            urgency = "🔴 Restock risk"
        elif rec.stock_cover_days > 6:
            urgency = "🟠 Overstock"
        else:
            urgency = "🟢 Stable"

        records.append(
            {
                "SKU": r["SKU"],
                "Category": r["Category"],
                "Current Price (₹)": r["Current Price (₹)"],
                "AI Recommended (₹)": rec.recommended_price,
                "Δ%": rec.price_change_pct,
                "Stock Cover (days)": rec.stock_cover_days,
                "Competitor (₹)": r["Competitor Price (₹)"],
                "Confidence": rec.confidence,
                "Status": urgency,
                "_explanation": rec.explanation,
                "_revenue_change_pct": rec.expected_revenue_change_pct,
                "_daily_sales": r["Avg Daily Sales (units)"],
            }
        )

    board = pd.DataFrame(records).sort_values("Δ%", key=lambda s: s.abs(), ascending=False)

    st.dataframe(
        board.drop(columns=["_explanation", "_revenue_change_pct", "_daily_sales"]),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Current Price (₹)": st.column_config.NumberColumn(format="₹%.2f"),
            "AI Recommended (₹)": st.column_config.NumberColumn(format="₹%.2f"),
            "Δ%": st.column_config.NumberColumn(format="%.1f%%"),
            "Competitor (₹)": st.column_config.NumberColumn(format="₹%.2f"),
            "Confidence": st.column_config.ProgressColumn(min_value=0, max_value=1, format="%.0f%%"),
        },
    )

    st.markdown("#### Review & decide")
    review_sku = st.selectbox("Select a SKU to review", board["SKU"].tolist(), key="review_sku")
    rrow = board[board["SKU"] == review_sku].iloc[0]

    c1, c2 = st.columns([2, 1])
    with c1:
        st.markdown(
            f"<div class='ps-card'><b>{rrow['SKU']}</b> — {rrow['Status']}<br>"
            f"{rrow['_explanation']}</div>",
            unsafe_allow_html=True,
        )
    with c2:
        monthly_impact = rrow["_daily_sales"] * rrow["Current Price (₹)"] * (rrow["_revenue_change_pct"] / 100) * 30
        bcol1, bcol2 = st.columns(2)
        if bcol1.button("✅ Approve AI price", use_container_width=True, key="approve_btn"):
            st.session_state.decisions[review_sku] = {"status": "Approved", "impact": monthly_impact}
        if bcol2.button("✋ Keep current price", use_container_width=True, key="keep_btn"):
            st.session_state.decisions[review_sku] = {"status": "Kept current", "impact": 0.0}

    if st.session_state.decisions:
        st.markdown("#### Decisions log")
        log_df = pd.DataFrame(
            [{"SKU": k, "Decision": v["status"], "Est. monthly revenue impact (₹)": round(v["impact"])}
             for k, v in st.session_state.decisions.items()]
        )
        st.dataframe(log_df, use_container_width=True, hide_index=True)

        approved = sum(1 for v in st.session_state.decisions.values() if v["status"] == "Approved")
        total_impact = sum(v["impact"] for v in st.session_state.decisions.values())
        lc1, lc2, lc3 = st.columns(3)
        lc1.metric("SKUs reviewed", len(st.session_state.decisions))
        lc2.metric("AI prices approved", approved)
        lc3.metric("Est. monthly revenue impact", f"₹{total_impact:,.0f}")

        if st.button("Clear decisions log"):
            st.session_state.decisions = {}
            st.rerun()

# ============================================================================
# TAB 3 — Impact Simulator
# ============================================================================
with tab3:
    st.subheader("Business impact simulator")
    st.caption(
        "Roll SKU-level pricing decisions up into a portfolio-level business case. "
        "Ranges are anchored to McKinsey retail-pricing benchmarks (see deck, Slide 2)."
    )

    scenario = st.radio(
        "Scenario", ["Conservative", "Base case", "Optimistic"], horizontal=True, index=1
    )
    scenario_map = {
        "Conservative": dict(revenue=2.0, margin=5.0, time=25.0),
        "Base case": dict(revenue=3.5, margin=7.5, time=40.0),
        "Optimistic": dict(revenue=5.0, margin=10.0, time=55.0),
    }
    sc = scenario_map[scenario]

    c1, c2, c3 = st.columns(3)
    with c1:
        n_skus = st.slider("SKUs you manage", 50, 5000, 800, step=50)
    with c2:
        rev_per_sku = st.number_input("Avg daily revenue per SKU (₹)", min_value=50, value=1200, step=50)
    with c3:
        pct_ai = st.slider("% of SKUs on AI-recommended pricing", 0, 100, 60)

    c4, c5 = st.columns(2)
    with c4:
        category_margin = st.slider("Avg category margin (%)", 5, 40, 18)
    with c5:
        hours_per_week = st.slider("Manager hours/week spent on manual pricing", 1, 40, 12)

    monthly_revenue_today = n_skus * rev_per_sku * 30
    ai_share = pct_ai / 100
    revenue_uplift = monthly_revenue_today * ai_share * (sc["revenue"] / 100)
    margin_gain = monthly_revenue_today * ai_share * category_margin / 100 * (sc["margin"] / 100)
    hours_reclaimed = hours_per_week * (sc["time"] / 100) * 4.345  # weeks/month

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Current monthly revenue", f"₹{monthly_revenue_today:,.0f}")
    k2.metric("Projected revenue uplift", f"₹{revenue_uplift:,.0f}", f"+{sc['revenue']:.1f}% on AI-priced SKUs")
    k3.metric("Projected margin gain", f"₹{margin_gain:,.0f}")
    k4.metric("Manager hours reclaimed / month", f"{hours_reclaimed:,.1f} hrs")

    fig2 = go.Figure(
        data=[
            go.Bar(name="Today", x=["Monthly revenue"], y=[monthly_revenue_today], marker_color="#5B6B7C"),
            go.Bar(name="With PriceSense AI", x=["Monthly revenue"],
                   y=[monthly_revenue_today + revenue_uplift], marker_color="#1C7293"),
        ]
    )
    fig2.update_layout(height=320, margin=dict(l=10, r=10, t=30, b=10), plot_bgcolor="white",
                        yaxis_title="₹ / month")
    st.plotly_chart(fig2, use_container_width=True)

    st.caption(
        "Estimates are illustrative, built from McKinsey retail-pricing and agentic-AI-in-"
        "merchandising research. Treat as a directional business case, to be validated with "
        "a 4-6 week pilot on a limited SKU set before a full rollout."
    )

st.markdown("---")
st.caption("PriceSense AI · Prototype built for the Abakus AI Catalyst challenge, IIM Kozhikode.")
