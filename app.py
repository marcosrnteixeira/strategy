import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="Strategy BTC Valuation & Stress Test", layout="wide")

st.title("Strategy: Valuation by BTC and Liquidity Stress Test")

st.markdown(
    """
Esta aplicação estima o preço implícito da MSTR a partir do preço futuro do BTC e de um múltiplo MNAV, 
e testa cenários de stress de liquidez com possível impacto em vendas de BTC e dividendos da STRC.
"""
)

st.sidebar.header("Assumptions")

btc_holdings = st.sidebar.number_input("BTC holdings", value=717131.0, step=1000.0)
diluted_shares = st.sidebar.number_input("Diluted shares", value=344.897e6, step=1e6)
cash = st.sidebar.number_input("Cash / USD reserve", value=2.25e9, step=1e7)
debt = st.sidebar.number_input("Debt", value=8.25e9, step=1e7)
preferred_claims = st.sidebar.number_input("Preferred claims / liability buffer", value=0.0, step=1e7)
annual_pref_dividends = st.sidebar.number_input("Annual preferred dividends", value=0.0, step=1e7)
annual_interest = st.sidebar.number_input("Annual debt interest", value=0.0, step=1e7)

btc_price = st.sidebar.slider("Future BTC price", 10000, 500000, 150000, 5000)
mnav = st.sidebar.slider("MNAV multiple", 0.2, 3.0, 1.2, 0.05)

btc_value = btc_holdings * btc_price
equity_value = btc_value + cash - debt - preferred_claims
nav_per_share = equity_value / diluted_shares
mstr_price = nav_per_share * mnav

st.subheader("Valuation")

col1, col2, col3 = st.columns(3)
col1.metric("BTC value", f"${btc_value:,.0f}")
col2.metric("NAV/share", f"${nav_per_share:,.2f}")
col3.metric("MSTR implied price", f"${mstr_price:,.2f}")

st.subheader("MNAV sensitivity")

btc_range = np.linspace(btc_price * 0.4, btc_price * 1.8, 25)
mnav_range = np.linspace(0.5, 2.5, 25)

grid = pd.DataFrame([
    {
        "btc_price": b,
        "mnav": m,
        "mstr": (((btc_holdings * b) + cash - debt - preferred_claims) / diluted_shares) * m
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

fig.update_layout(
    xaxis_title="MNAV",
    yaxis_title="BTC price",
    height=600
)

st.plotly_chart(fig, use_container_width=True)

st.subheader("Liquidity stress test")

shock = st.slider("BTC drawdown", 0, 90, 50, 5)
shocked_btc = btc_price * (1 - shock / 100)
shocked_value = btc_holdings * shocked_btc

annual_obligations = annual_pref_dividends + annual_interest
available_liquidity = cash
liquidity_gap = annual_obligations - available_liquidity
btc_to_sell = max(0.0, liquidity_gap / shocked_btc) if shocked_btc > 0 else np.nan

c1, c2, c3 = st.columns(3)
c1.metric("Shocked BTC price", f"${shocked_btc:,.0f}")
c2.metric("Annual obligations", f"${annual_obligations:,.0f}")
c3.metric("BTC to sell to cover gap", f"{btc_to_sell:,.2f}")

st.write(
    "Se as obrigações anuais excederem o cash/reserve disponível, a estimativa acima indica quanto BTC teria de ser vendido para cobrir o défice."
)

st.subheader("Scenario table")

scenarios = pd.DataFrame({
    "BTC price": [btc_price * 0.5, btc_price, btc_price * 1.5],
    "MNAV": [0.8, 1.2, 1.8]
})

scenarios["MSTR implied"] = scenarios.apply(
    lambda r: (((btc_holdings * r["BTC price"]) + cash - debt - preferred_claims) / diluted_shares) * r["MNAV"],
    axis=1
)

st.dataframe(scenarios, use_container_width=True)
