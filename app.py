import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="Strategy BTC Valuation & Stress Test", layout="wide")

st.title("Strategy: Valuation by BTC and Liquidity Stress Test")
st.caption("All balance sheet figures are in thousands USD, consistent with the financial statements.")

st.markdown(
    """
Esta aplicação estima o preço implícito da MSTR a partir do preço futuro do BTC e de um múltiplo MNAV.
A secção de stress test mostra se a Strategy cobre as obrigações com a USD Reserve, e apenas depois avalia
se é necessário cortar dividendos ou vender BTC.
"""
)

st.sidebar.header("Assumptions")

btc_holdings = st.sidebar.number_input("BTC holdings (BTC)", value=717131.0, step=1000.0)
diluted_shares = st.sidebar.number_input("Diluted shares (shares)", value=344.897e6, step=1e6)
future_btc_price = st.sidebar.number_input(
    "Future BTC price (USD/BTC)",
    value=150000.0,
    step=1000.0,
    min_value=10000.0,
    max_value=500000.0
)
mnav = st.sidebar.slider("MNAV multiple", 0.2, 3.0, 1.2, 0.05)

cash_th = st.sidebar.number_input("Cash / USD reserve (thousands USD)", value=2250000.0, step=1000.0)
debt_th = st.sidebar.number_input("Debt (thousands USD)", value=8250000.0, step=1000.0)
preferred_claims_th = st.sidebar.number_input("Preferred claims / buffer (thousands USD)", value=8470000.0, step=1000.0)
annual_pref_dividends_th = st.sidebar.number_input("Annual preferred dividends (thousands USD)", value=381367.0, step=1000.0)
annual_interest_th = st.sidebar.number_input("Annual debt interest (thousands USD)", value=36200.0, step=1000.0)

cash_usd = cash_th * 1000.0
debt_usd = debt_th * 1000.0
preferred_claims_usd = preferred_claims_th * 1000.0

btc_value_th = (btc_holdings * future_btc_price) / 1000.0
equity_value_usd = (btc_holdings * future_btc_price) + cash_usd - debt_usd - preferred_claims_usd
nav_per_share = equity_value_usd / diluted_shares
mstr_price = nav_per_share * mnav

st.subheader("Valuation")

col1, col2, col3 = st.columns(3)
col1.metric("BTC value (thousands USD)", f"{btc_value_th:,.0f}")
col2.metric("NAV/share (USD)", f"${nav_per_share:,.2f}")
col3.metric("MSTR implied price (USD)", f"${mstr_price:,.2f}")

st.subheader("MNAV sensitivity")

btc_range = np.linspace(future_btc_price * 0.4, future_btc_price * 1.8, 25)
mnav_range = np.linspace(0.5, 2.5, 25)

grid = pd.DataFrame([
    {
        "btc_price": b,
        "mnav": m,
        "mstr": ((((btc_holdings * b) + cash_usd - debt_usd - preferred_claims_usd) / diluted_shares) * m)
    }
    for b in btc_range for m in mnav_range
])

pivot = grid.pivot(index="btc_price", columns="mnav", values="mstr")

fig = go.Figure(
    data=go.Heatmap(
        z=pivot.values,
        x=[round(x, 2) for x in pivot.columns],
        y=[int(y) for y in pivot.index],
        colorscale="Viridis"
    )
)
fig.update_layout(xaxis_title="MNAV", yaxis_title="BTC price (USD/BTC)", height=600)
st.plotly_chart(fig, use_container_width=True)

st.subheader("Liquidity stress test")

shock = st.slider("BTC drawdown", 0, 90, 35, 5)
shocked_btc = future_btc_price * (1 - shock / 100)
annual_obligations_th = annual_pref_dividends_th + annual_interest_th
liquidity_gap_th = annual_obligations_th - cash_th
btc_to_sell = max(0.0, (liquidity_gap_th * 1000.0) / shocked_btc) if shocked_btc > 0 else np.nan

c1, c2, c3 = st.columns(3)
c1.metric("Shocked BTC price (USD/BTC)", f"${shocked_btc:,.0f}")
c2.metric("Annual obligations (thousands USD)", f"{annual_obligations_th:,.0f}")
c3.metric("BTC to sell to cover gap", f"{btc_to_sell:,.2f}")

st.write(
    "If annual obligations exceed available liquidity, the model estimates how much BTC would need to be sold to close the shortfall after using the USD Reserve."
)

st.subheader("3 stress scenarios")

scenarios = pd.DataFrame([
    {"Scenario": "Mild stress", "Shock %": 5, "Use reserve first": True, "Cut dividends": False},
    {"Scenario": "Base stress", "Shock %": 35, "Use reserve first": True, "Cut dividends": True},
    {"Scenario": "Severe stress", "Shock %": 60, "Use reserve first": True, "Cut dividends": True}
])

results = []
for _, r in scenarios.iterrows():
    s_btc = future_btc_price * (1 - r["Shock %"] / 100)
    effective_dividends = 0 if r["Cut dividends"] else annual_pref_dividends_th
    obligations = effective_dividends + annual_interest_th
    residual_gap = max(0.0, obligations - cash_th)
    btc_sell = max(0.0, (residual_gap * 1000.0) / s_btc) if s_btc > 0 else np.nan
    dividend_action = "Cut" if r["Cut dividends"] else "Keep"
    outcome = "Covered" if residual_gap <= 0 else "Need BTC sale"

    results.append({
        "Scenario": r["Scenario"],
        "Shock %": r["Shock %"],
        "BTC price after shock": round(s_btc, 0),
        "Liquidity available (thousands USD)": round(cash_th, 0),
        "Annual obligations (thousands USD)": round(obligations, 0),
        "Dividend action": dividend_action,
        "BTC sold": round(btc_sell, 2),
        "Residual gap (thousands USD)": round(residual_gap, 0),
        "Outcome": outcome
    })

results_df = pd.DataFrame(results)
st.dataframe(results_df, use_container_width=True)

fig2 = go.Figure()
fig2.add_trace(go.Bar(x=results_df["Scenario"], y=results_df["BTC sold"], name="BTC sold"))
fig2.update_layout(height=450, yaxis_title="BTC sold", xaxis_title="Scenario")
st.plotly_chart(fig2, use_container_width=True)
