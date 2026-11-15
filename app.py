import os
import requests
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Company Checker", page_icon="📊", layout="wide")

API_BASE = "https://financialmodelingprep.com/stable"

st.title("📊 Company Checker")
st.caption("A simple dashboard for exploring company financials and comparing businesses.")

# --- Access gate: optional extra layer. Streamlit's private-app viewer access is still recommended. ---
def check_password():
    expected = st.secrets.get("APP_PASSWORD", os.getenv("APP_PASSWORD", ""))
    if not expected:
        return True
    if st.session_state.get("authenticated", False):
        return True
    st.subheader("Private access")
    entered = st.text_input("App password", type="password")
    if st.button("Unlock"):
        if entered == expected:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("That password did not match.")
    return False

if not check_password():
    st.stop()

api_key = st.secrets.get("FMP_API_KEY", os.getenv("FMP_API_KEY", ""))
if not api_key:
    st.warning("Add your FMP API key in Streamlit Secrets as FMP_API_KEY to load live company data.")
    st.markdown("You can still explore the layout, but live figures need an API key.")
    st.stop()

@st.cache_data(ttl=3600, show_spinner=False)
def fmp_get(endpoint: str, symbol: str, limit: int = 10):
    url = f"{API_BASE}/{endpoint}"
    response = requests.get(
        url,
        params={"symbol": symbol, "limit": limit, "period": "annual", "apikey": api_key},
        timeout=25,
    )
    response.raise_for_status()
    data = response.json()
    if isinstance(data, dict) and data.get("Error Message"):
        raise ValueError(data["Error Message"])
    if not isinstance(data, list):
        raise ValueError(str(data)[:300])
    return data

def load_company(symbol):
    symbol = symbol.strip().upper()
    if not symbol:
        raise ValueError("Enter a ticker symbol.")
    profile = fmp_get("profile", symbol, 1)
    income = fmp_get("income-statement", symbol, 10)
    ratios = fmp_get("ratios", symbol, 10)
    if not profile:
        raise ValueError(f"No company profile was found for {symbol}. Check the ticker.")
    p = profile[0]
    inc = pd.DataFrame(income)
    rat = pd.DataFrame(ratios)
    if not inc.empty:
        inc["date"] = pd.to_datetime(inc["date"], errors="coerce")
        inc["year"] = inc["date"].dt.year
    if not rat.empty:
        rat["date"] = pd.to_datetime(rat["date"], errors="coerce")
        rat["year"] = rat["date"].dt.year
    if not inc.empty and not rat.empty:
        df = pd.merge(
            inc[["year", "date", "revenue", "operatingIncome", "reportedCurrency"]],
            rat[["year", "priceToEarningsRatio"]],
            on="year", how="left"
        )
    elif not inc.empty:
        df = inc[["year", "date", "revenue", "operatingIncome", "reportedCurrency"]].copy()
        df["priceToEarningsRatio"] = None
    else:
        df = pd.DataFrame(columns=["year", "date", "revenue", "operatingIncome", "reportedCurrency", "priceToEarningsRatio"])
    df = df.sort_values("year", ascending=False).drop_duplicates("year") if not df.empty else df
    return {"symbol": symbol, "name": p.get("companyName") or symbol,
            "currency": p.get("currency") or (df["reportedCurrency"].dropna().iloc[0] if not df.empty and df["reportedCurrency"].notna().any() else ""),
            "exchange": p.get("exchangeShortName") or p.get("exchange") or "",
            "sector": p.get("sector") or "",
            "industry": p.get("industry") or "",
            "data": df}

def pretty_money(value, currency):
    if pd.isna(value):
        return "—"
    try:
        return f"{currency} {value / 1_000_000_000:,.2f}bn"
    except Exception:
        return "—"

def show_company(company):
    st.subheader(f"{company['name']} ({company['symbol']})")
    st.caption(" · ".join(x for x in [company["sector"], company["industry"], company["exchange"]] if x))
    df = company["data"].copy()
    if df.empty:
        st.info("No annual financial statement rows were returned.")
        return
    latest = df.iloc[0]
    a, b, c = st.columns(3)
    a.metric("Latest annual revenue", pretty_money(latest.get("revenue"), company["currency"]))
    b.metric("Latest operating profit", pretty_money(latest.get("operatingIncome"), company["currency"]))
    pe = latest.get("priceToEarningsRatio")
    c.metric("Latest annual P/E", f"{pe:.1f}×" if pd.notna(pe) else "Not available")
    st.caption("Figures are annual and shown in the reporting currency. P/E is the provider's reported annual ratio; it may be blank where unavailable.")
    view = df[["year", "revenue", "operatingIncome", "priceToEarningsRatio"]].copy()
    view["Revenue"] = view["revenue"].map(lambda x: pretty_money(x, company["currency"]))
    view["Operating profit"] = view["operatingIncome"].map(lambda x: pretty_money(x, company["currency"]))
    view["P/E"] = view["priceToEarningsRatio"].map(lambda x: f"{x:.1f}×" if pd.notna(x) else "—")
    st.markdown("**Historical figures**")
    st.dataframe(view[["year", "Revenue", "Operating profit", "P/E"]].rename(columns={"year":"Year"}), hide_index=True, use_container_width=True)
    chart_df = df.sort_values("year")
    left, right = st.columns(2)
    with left:
        fig = px.line(chart_df, x="year", y="revenue", markers=True, title=f"{company['symbol']} revenue")
        fig.update_yaxes(title=f"Revenue ({company['currency']})", tickformat="~s")
        st.plotly_chart(fig, use_container_width=True)
    with right:
        fig = px.line(chart_df, x="year", y="operatingIncome", markers=True, title=f"{company['symbol']} operating profit")
        fig.update_yaxes(title=f"Operating profit ({company['currency']})", tickformat="~s")
        st.plotly_chart(fig, use_container_width=True)
    pe_df = chart_df.dropna(subset=["priceToEarningsRatio"])
    if not pe_df.empty:
        fig = px.line(pe_df, x="year", y="priceToEarningsRatio", markers=True, title=f"{company['symbol']} P/E history")
        fig.update_yaxes(title="P/E ratio (×)")
        st.plotly_chart(fig, use_container_width=True)

st.sidebar.header("Your companies")
st.sidebar.write("Enter ticker symbols separated by commas.")
symbols_text = st.sidebar.text_input("Tickers", value="AAPL, MSFT")
symbols = list(dict.fromkeys(s.strip().upper() for s in symbols_text.split(",") if s.strip()))
st.sidebar.caption("Example: AAPL, MSFT, GOOGL")
st.sidebar.button("Refresh data", on_click=st.cache_data.clear)
st.sidebar.caption("Data refreshes automatically from cache every hour.")

if not symbols:
    st.info("Add at least one ticker in the sidebar to get started.")
    st.stop()

companies = []
errors = []
with st.spinner("Loading company financials…"):
    for symbol in symbols[:8]:
        try:
            companies.append(load_company(symbol))
        except Exception as exc:
            errors.append(f"{symbol}: {exc}")

for err in errors:
    st.warning(err)

if not companies:
    st.error("No companies could be loaded. Check the ticker symbols, API key and data-plan access.")
    st.stop()

tab1, tab2, tab3 = st.tabs(["Company overview", "Compare companies", "How to read this"])

with tab1:
    chosen = st.selectbox("Choose a company", [c["symbol"] for c in companies])
    company = next(c for c in companies if c["symbol"] == chosen)
    show_company(company)

with tab2:
    st.subheader("Side-by-side comparison")
    st.caption("Compare up to 8 companies. Revenue and operating profit stay in each company's own reporting currency; do not compare their raw amounts across different currencies.")
    rows = []
    for c in companies:
        d = c["data"]
        if d.empty:
            continue
        latest = d.iloc[0]
        rows.append({
            "Company": f"{c['name']} ({c['symbol']})",
            "Latest year": int(latest["year"]) if pd.notna(latest["year"]) else "—",
            "Currency": c["currency"] or "—",
            "Revenue": pretty_money(latest.get("revenue"), c["currency"]),
            "Operating profit": pretty_money(latest.get("operatingIncome"), c["currency"]),
            "P/E": f"{latest['priceToEarningsRatio']:.1f}×" if pd.notna(latest.get("priceToEarningsRatio")) else "—",
            "Sector": c["sector"] or "—",
        })
    if rows:
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    metric = st.radio("Graph metric", ["Revenue", "Operating profit", "P/E ratio"], horizontal=True)
    key_map = {"Revenue": "revenue", "Operating profit": "operatingIncome", "P/E ratio": "priceToEarningsRatio"}
    plot_rows = []
    for c in companies:
        d = c["data"]
        if d.empty:
            continue
        for _, r in d.iterrows():
            value = r.get(key_map[metric])
            if pd.notna(value):
                plot_rows.append({"Company": c["symbol"], "Year": int(r["year"]), "Value": value})
    if plot_rows:
        plot = pd.DataFrame(plot_rows)
        fig = px.line(plot, x="Year", y="Value", color="Company", markers=True, title=f"Historical {metric} comparison")
        if metric != "P/E ratio":
            fig.update_yaxes(tickformat="~s", title="Amount (each company’s reporting currency)")
        else:
            fig.update_yaxes(title="P/E ratio (×)")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data is available for this comparison.")

with tab3:
    st.subheader("A few useful reminders")
    st.markdown("""
- **Revenue** is the money a company brings in from its normal business before expenses.
- **Operating profit** is profit from the main business before interest and tax; it helps show how the core operation is performing.
- **P/E ratio** compares a share price with earnings per share. A higher P/E is not automatically bad, and a lower P/E is not automatically good.
- **Compare like with like.** Companies in the same industry are usually more useful comparisons than unrelated businesses.
- **Currencies matter.** This first version does not convert GBP, USD or other currencies into one common currency.
- **Different year ends matter.** A company's financial year may not match the calendar year.
- **This is a research tool, not a buy/sell recommendation.** Check company reports and the data provider's definitions before drawing conclusions.
    """)
    st.caption("Source: Financial Modeling Prep API. Figures can be delayed, revised or unavailable depending on the provider's coverage and your subscription.")
