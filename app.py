import math

import pandas as pd
import plotly.express as px
import streamlit as st

import strategies as strat

st.set_page_config(page_title="IPO Flipper", layout="wide")

# ── Sidebar: global IPO parameters ──────────────────────────────────────────
with st.sidebar:
    st.title("IPO Parameters")
    ipo_price = st.number_input(
        "IPO Price ($)", min_value=0.01, value=None, step=0.01, format="%.2f",
        placeholder="e.g. 0.88",
    )
    total_shares = st.number_input(
        "Total Shares", min_value=1, value=None, step=100,
        placeholder="e.g. 10000",
    )
    if ipo_price is not None and total_shares is not None:
        total_cost = ipo_price * total_shares
        st.metric("Total Cost", f"${total_cost:,.2f}")

st.title("IPO Flipper Strategy Calculator")

if ipo_price is None or total_shares is None:
    st.info("Enter your **IPO Price** and **Total Shares** in the sidebar to begin.")
    st.stop()

tabs = st.tabs([
    "Asymmetric Ladder",
    "Inverse Pyramid",
    "Split Equally",
    "Trailing Stop",
])


def render_results(batches, summary):
    df = pd.DataFrame(batches)
    df["Sell Price"] = df["Sell Price"].map("${:.2f}".format)
    df["Gross Proceeds"] = df["Gross Proceeds"].map("${:,.2f}".format)
    df["Gain"] = df["Gain"].map("${:,.2f}".format)
    df["Gain %"] = df["Gain %"].map("{:.1f}%".format)
    st.dataframe(df, hide_index=True, use_container_width=True)

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Gain", f"${summary['total_gain']:,.2f}")
    col2.metric("ROI", f"{summary['roi_pct']:.1f}%")
    col3.metric("Total Proceeds", f"${summary['total_proceeds']:,.2f}")

    chart_df = pd.DataFrame(batches)[["Batch", "Gain"]].copy()
    chart_df["Batch"] = chart_df["Batch"].astype(str)
    fig = px.bar(chart_df, x="Batch", y="Gain", text_auto=".0f",
                 labels={"Gain": "Gain ($)", "Batch": "Batch"},
                 color_discrete_sequence=["#2196F3"])
    fig.update_layout(height=280, margin=dict(t=20, b=20))
    st.plotly_chart(fig, use_container_width=True)


# ── Tab: Asymmetric Ladder ───────────────────────────────────────────────────
with tabs[0]:
    st.subheader("Asymmetric Ladder")
    st.caption("Customise the share count AND gain % for each batch independently.")
    n_al = st.slider("Number of batches", 2, 8, 4, key="al_n")

    weight_defaults = [500, 1000, 2000, 500, 500, 500, 500, 500]
    gain_defaults = [20, 30, 40, 55, 65, 75, 85, 95]

    weights_al, gains_al = [], []
    cols = st.columns(n_al)
    for i, col in enumerate(cols):
        w = col.number_input(f"Batch {i+1} Shares", 1, int(total_shares), weight_defaults[i], 100, key=f"al_w{i}")
        g = col.number_input(f"Batch {i+1} Gain %", 1.0, 500.0, float(gain_defaults[i]), 1.0, key=f"al_g{i}")
        weights_al.append(w)
        gains_al.append(g)

    total_entered = sum(weights_al)
    if total_entered != int(total_shares):
        st.warning(f"Share weights sum to {total_entered:,}, but Total Shares = {int(total_shares):,}. "
                   "Weights will be scaled proportionally.")

    batches, summary = strat.asymmetric_ladder(ipo_price, int(total_shares), weights_al, gains_al)
    render_results(batches, summary)

# ── Tab: Inverse Pyramid ─────────────────────────────────────────────────────
with tabs[1]:
    st.subheader("Inverse Pyramid")
    st.caption("More shares at lower gain targets, tapering off at higher targets. Maximises early exits.")
    col1, col2, col3 = st.columns(3)
    n_ip = col1.slider("Number of batches", 2, 8, 4, key="ip_n")
    min_gain_ip = col2.number_input("Min Gain %", 1.0, 490.0, 20.0, 1.0, key="ip_min")
    max_gain_ip = col3.number_input("Max Gain %", min_gain_ip + 1, 500.0, 55.0, 1.0, key="ip_max")

    batches, summary = strat.inverse_pyramid(ipo_price, int(total_shares), n_ip, min_gain_ip, max_gain_ip)
    render_results(batches, summary)

# ── Tab: Split Equally ───────────────────────────────────────────────────────
with tabs[2]:
    st.subheader("Split Equally")
    st.caption("Shares divided equally across all batches. You set a gain % target for each batch.")
    n_eq = st.slider("Number of batches", 2, 8, 2, key="eq_n")
    gain_targets_eq = []
    cols = st.columns(n_eq)
    for i, col in enumerate(cols):
        default = 30 + i * 10
        gain_targets_eq.append(col.number_input(f"Batch {i+1} Gain %", 1.0, 500.0, float(default), 1.0, key=f"eq_g{i}"))

    batches, summary = strat.split_equally(ipo_price, int(total_shares), gain_targets_eq)
    render_results(batches, summary)

# ── Tab: Trailing Stop ───────────────────────────────────────────────────────
with tabs[3]:
    st.subheader("Trailing Stop (Simulation)")
    st.caption(
        "Simulates a trailing stop-loss. Shares all sell at the same stop-trigger price "
        "= peak price × (1 − trail %)."
    )
    col1, col2, col3 = st.columns(3)
    n_ts = col1.slider("Number of batches", 1, 8, 2, key="ts_n")
    peak_gain = col2.number_input("Simulated Peak Gain %", 1.0, 500.0, 60.0, 1.0, key="ts_peak")
    trail_pct = col3.number_input("Trail %", 1.0, 99.0, 15.0, 1.0, key="ts_trail")

    st.write("**Share allocation per batch:**")
    weight_defaults_ts = [2000, 2000, 1000, 1000, 500, 500, 500, 500]
    weights_ts = []
    cols = st.columns(n_ts)
    for i, col in enumerate(cols):
        w = col.number_input(f"Batch {i+1} Shares", 1, int(total_shares),
                             weight_defaults_ts[i] if i < 8 else int(total_shares // n_ts),
                             100, key=f"ts_w{i}")
        weights_ts.append(w)

    peak_price = ipo_price * (1 + peak_gain / 100)
    stop_price = math.ceil(peak_price * (1 - trail_pct / 100) * 100) / 100
    st.info(
        f"Peak price: **${peak_price:.2f}** → Stop trigger: **${stop_price:.2f}** "
        f"({(stop_price/ipo_price - 1)*100:.1f}% above IPO price)"
    )

    batches, summary = strat.trailing_stop(ipo_price, int(total_shares), weights_ts, peak_gain, trail_pct)
    render_results(batches, summary)

# ── Strategy Comparison ──────────────────────────────────────────────────────
st.divider()
st.subheader("Strategy Comparison")
st.caption("All strategies evaluated with their current settings above.")

comparison_rows = []

_, s = strat.asymmetric_ladder(ipo_price, int(total_shares), weights_al, gains_al)
comparison_rows.append({"Strategy": "Asymmetric Ladder", "Batches": n_al,
                         "Total Gain": s["total_gain"], "ROI %": s["roi_pct"],
                         "Total Proceeds": s["total_proceeds"]})

_, s = strat.inverse_pyramid(ipo_price, int(total_shares), n_ip, min_gain_ip, max_gain_ip)
comparison_rows.append({"Strategy": "Inverse Pyramid", "Batches": n_ip,
                         "Total Gain": s["total_gain"], "ROI %": s["roi_pct"],
                         "Total Proceeds": s["total_proceeds"]})

_, s = strat.split_equally(ipo_price, int(total_shares), gain_targets_eq)
comparison_rows.append({"Strategy": "Split Equally", "Batches": n_eq,
                         "Total Gain": s["total_gain"], "ROI %": s["roi_pct"],
                         "Total Proceeds": s["total_proceeds"]})

_, s = strat.trailing_stop(ipo_price, int(total_shares), weights_ts, peak_gain, trail_pct)
comparison_rows.append({"Strategy": "Trailing Stop", "Batches": n_ts,
                         "Total Gain": s["total_gain"], "ROI %": s["roi_pct"],
                         "Total Proceeds": s["total_proceeds"]})

cdf = pd.DataFrame(comparison_rows)
best_idx = cdf["ROI %"].idxmax()

def highlight_best(row):
    if row.name == best_idx:
        return ["background-color: #1a472a; color: white"] * len(row)
    return [""] * len(row)

styled = (
    cdf.style
    .apply(highlight_best, axis=1)
    .format({
        "Total Gain": "${:,.2f}",
        "ROI %": "{:.1f}%",
        "Total Proceeds": "${:,.2f}",
    })
)
st.dataframe(styled, hide_index=True, use_container_width=True)

best_name = cdf.loc[best_idx, "Strategy"]
best_roi = cdf.loc[best_idx, "ROI %"]
st.success(f"Best strategy with current settings: **{best_name}** at **{best_roi:.1f}% ROI**")
