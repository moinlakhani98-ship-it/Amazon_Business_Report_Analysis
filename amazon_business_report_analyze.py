import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(page_title="Amazon Business Report", layout="wide")
st.title("📊 Amazon Business Report Dashboard")

file = st.file_uploader("Business Report (CSV) upload karo", type="csv")

def clean(df):
    cols = ["(Child) ASIN", "Title", "Sessions - Total", "Units Ordered",
            "Unit Session Percentage", "Featured Offer (Buy Box) Percentage",
            "Ordered Product Sales"]
    d = df[[c for c in cols if c in df.columns]].copy()
    for c in d.columns:
        if c not in ["(Child) ASIN", "Title"]:
            d[c] = pd.to_numeric(
                d[c].astype(str).str.replace(r"[$,%]", "", regex=True).str.replace(",", ""),
                errors="coerce",
            )
    d["Sales per Session"] = d["Ordered Product Sales"] / d["Sessions - Total"]
    d["Avg Order Value"] = d["Ordered Product Sales"] / d["Units Ordered"]
    return d.replace([np.inf, -np.inf], np.nan)

if file:
    data = clean(pd.read_csv(file))

    min_s = st.sidebar.slider("Minimum Sessions", 0, int(data["Sessions - Total"].max()), 0)
    data = data[data["Sessions - Total"] >= min_s].copy()

    med_s = data["Sessions - Total"].median()
    avg_cr = data["Unit Session Percentage"].mean()

    def segment(r):
        ht = r["Sessions - Total"] > med_s
        hc = r["Unit Session Percentage"] >= avg_cr
        if ht and hc: return "Star"
        if ht: return "Fix"
        if hc: return "Promote"
        return "Review"

    data["Segment"] = data.apply(segment, axis=1)

    # KPI cards
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Sales", f"${data['Ordered Product Sales'].sum():,.0f}")
    k2.metric("Total Units", f"{data['Units Ordered'].sum():,.0f}")
    k3.metric("Total Sessions", f"{data['Sessions - Total'].sum():,.0f}")
    k4.metric("Avg Conversion", f"{avg_cr:.1f}%")

    # Segment summary
    st.subheader("Segment Summary")
    summary = data.groupby("Segment").agg(
        ASINs=("(Child) ASIN", "count"),
        Sales=("Ordered Product Sales", "sum"),
        Avg_CR=("Unit Session Percentage", "mean"),
        Avg_BuyBox=("Featured Offer (Buy Box) Percentage", "mean"),
    ).round(2)
    summary["Sales Share %"] = (summary["Sales"] / summary["Sales"].sum() * 100).round(1)
    st.dataframe(summary, use_container_width=True)

    # Charts
    c1, c2 = st.columns(2)
    fig1 = px.scatter(data.dropna(subset=["Ordered Product Sales"]),
                      x="Sessions - Total", y="Unit Session Percentage",
                      color="Segment", hover_name="(Child) ASIN",
                      size="Ordered Product Sales", log_x=True,
                      title="Product Segments")
    fig1.add_hline(y=avg_cr, line_dash="dash")
    fig1.add_vline(x=med_s, line_dash="dash")
    c1.plotly_chart(fig1, use_container_width=True)

    # Pareto
    p = data.sort_values("Ordered Product Sales", ascending=False).reset_index(drop=True)
    p["Cum Sales %"] = p["Ordered Product Sales"].cumsum() / p["Ordered Product Sales"].sum() * 100
    n80 = int((p["Cum Sales %"] <= 80).sum() + 1)
    fig2 = px.line(p, y="Cum Sales %", title=f"Pareto: {n80} ASINs = 80% sales")
    fig2.add_hline(y=80, line_dash="dash", line_color="red")
    c2.plotly_chart(fig2, use_container_width=True)

    # Fix priority
    st.subheader("⚠️ Fix Priority (potential extra sales)")
    fix = data[data["Segment"] == "Fix"].copy()
    fix["Potential Extra Sales"] = (
        fix["Sessions - Total"] * (avg_cr - fix["Unit Session Percentage"]) / 100
        * fix["Avg Order Value"]
    ).round(2)
    st.dataframe(
        fix.sort_values("Potential Extra Sales", ascending=False)[
            ["(Child) ASIN", "Sessions - Total", "Unit Session Percentage",
             "Featured Offer (Buy Box) Percentage", "Potential Extra Sales"]
        ].head(15),
        use_container_width=True,
    )

    st.download_button("Segmented report download", data.to_csv(index=False),
                       "segmented_report.csv", "text/csv")
else:
    st.info("Shuru karne ke liye CSV upload karo.")
